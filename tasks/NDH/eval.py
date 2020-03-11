''' Evaluation of agent trajectories '''

import json
import os
import sys
from collections import defaultdict
import networkx as nx
import numpy as np
import pprint
pp = pprint.PrettyPrinter(indent=4)

from env import R2RBatch
from utils import load_datasets, load_nav_graphs
from agent import BaseAgent, StopAgent, RandomAgent, ShortestAgent


class Evaluation(object):
    ''' Results submission format:  [{'instr_id': string, 'trajectory':[(viewpoint_id, heading_rads, elevation_rads),] } ] '''

    def __init__(self, splits, path_type='planner_path'):
        self.error_margin = 3.0
        self.splits = splits
        self.gt = {}
        self.instr_ids = []
        self.scans = []
        for item in load_datasets(splits):
            self.gt[item['inst_idx']] = item
            self.instr_ids.append(item['inst_idx'])
            self.scans.append(item['scan'])

            # Add 'trusted_path' to gt metadata if necessary.
            if path_type == 'trusted_path':
                planner_goal = item['planner_path'][-1]
                if planner_goal in item['player_path'][1:]:
                    self.gt[item['inst_idx']]['trusted_path'] = item['player_path'][:]
                else:
                    self.gt[item['inst_idx']]['trusted_path'] = item['planner_path'][:]

        self.scans = set(self.scans)
        self.instr_ids = set(self.instr_ids)
        self.graphs = load_nav_graphs(self.scans)
        self.distances = {}
        self.path_type = path_type
        for scan,G in self.graphs.iteritems(): # compute all shortest paths
            self.distances[scan] = dict(nx.all_pairs_dijkstra_path_length(G))

    def _get_nearest(self, scan, goal_id, path):
        near_id = path[0][0]
        near_d = self.distances[scan][near_id][goal_id]
        for item in path:
            d = self.distances[scan][item[0]][goal_id]
            if d < near_d:
                near_id = item[0]
                near_d = d
        return near_id

    def _score_item(self, instr_id, path):
        ''' Calculate error based on the final position in trajectory, and also 
            the closest position (oracle stopping rule). '''
        gt = self.gt[int(instr_id)]
        start = gt[self.path_type][0]
        assert start == path[0][0], 'Result trajectories should include the start position'
        goal = gt[self.path_type][-1]
        planner_goal = gt['planner_path'][-1]  # for calculating oracle planner success (e.g., passed over desc goal?)
        final_position = path[-1][0]
        nearest_position = self._get_nearest(gt['scan'], goal, path)
        nearest_planner_position = self._get_nearest(gt['scan'], planner_goal, path)
        dist_to_end_start = None
        dist_to_end_end = None
        for end_pano in gt['end_panos']:
            d = self.distances[gt['scan']][start][end_pano]
            if dist_to_end_start is None or d < dist_to_end_start:
                dist_to_end_start = d
            d = self.distances[gt['scan']][final_position][end_pano]
            if dist_to_end_end is None or d < dist_to_end_end:
                dist_to_end_end = d
        self.scores['nav_errors'].append(self.distances[gt['scan']][final_position][goal])
        self.scores['oracle_errors'].append(self.distances[gt['scan']][nearest_position][goal])
        self.scores['oracle_plan_errors'].append(self.distances[gt['scan']][nearest_planner_position][planner_goal])
        self.scores['dist_to_end_reductions'].append(dist_to_end_start - dist_to_end_end)
        distance = 0  # Work out the length of the path in meters
        prev = path[0]
        for curr in path[1:]:
            if prev[0] != curr[0]:
                try:
                    self.graphs[gt['scan']][prev[0]][curr[0]]
                except KeyError as err:
                    print 'Error: The provided trajectory moves from %s to %s but the navigation graph contains no '\
                        'edge between these viewpoints. Please ensure the provided navigation trajectories '\
                        'are valid, so that trajectory length can be accurately calculated.' % (prev[0], curr[0])
                    raise
            distance += self.distances[gt['scan']][prev[0]][curr[0]]
            prev = curr
        self.scores['trajectory_lengths'].append(distance)
        self.scores['shortest_path_lengths'].append(self.distances[gt['scan']][start][goal])

    def score(self, output_file):
        ''' Evaluate each agent trajectory based on how close it got to the goal location '''
        self.scores = defaultdict(list)
        instr_ids = set(self.instr_ids)
        with open(output_file) as f:
            for item in json.load(f):
                # Check against expected ids
                if item['inst_idx'] in instr_ids:
                    instr_ids.remove(item['inst_idx'])
                    self._score_item(item['inst_idx'], item['trajectory'])
        assert len(instr_ids) == 0, 'Trajectories not provided for %d instruction ids: %s' % (len(instr_ids), instr_ids)
        assert len(self.scores['nav_errors']) == len(self.instr_ids)

        num_successes = len([i for i in self.scores['nav_errors'] if i < self.error_margin])
        oracle_successes = len([i for i in self.scores['oracle_errors'] if i < self.error_margin])
        oracle_plan_successes = len([i for i in self.scores['oracle_plan_errors'] if i < self.error_margin])

        spls = []
        for err, length, sp in zip(self.scores['nav_errors'], self.scores['trajectory_lengths'], self.scores['shortest_path_lengths']):
            if err < self.error_margin:
                if sp > 0:
                    spls.append(sp / max(length, sp))
                else:  # In IF, some Q/A pairs happen when we're already in the goal region, so taking no action is correct.
                    spls.append(1 if length == 0 else 0)
            else:
                spls.append(0)
        
        score_summary ={
            'length': np.average(self.scores['trajectory_lengths']),
            'nav_error': np.average(self.scores['nav_errors']),
            'oracle success_rate': float(oracle_successes)/float(len(self.scores['oracle_errors'])),
            'success_rate': float(num_successes)/float(len(self.scores['nav_errors'])),
            'spl': np.average(spls),
            'oracle path_success_rate': float(oracle_plan_successes)/float(len(self.scores['oracle_plan_errors'])),
            'dist_to_end_reduction': sum(self.scores['dist_to_end_reductions']) / float(len(self.scores['dist_to_end_reductions']))
        }

        assert score_summary['spl'] <= score_summary['success_rate']
        return score_summary, self.scores


RESULT_DIR = 'tasks/NDH/results/'


def eval_simple_agents():
    # path_type = 'planner_path'
    # path_type = 'player_path'
    path_type = 'trusted_path'

    ''' Run simple baselines on each split. '''
    for split in ['train', 'val_seen', 'val_unseen']:
        env = R2RBatch(None, batch_size=1, splits=[split], path_type=path_type)
        ev = Evaluation([split], path_type=path_type)

        for agent_type in ['Stop', 'Shortest', 'Random']:
            outfile = '%s%s_%s_agent.json' % (RESULT_DIR, split, agent_type.lower())
            agent = BaseAgent.get_agent(agent_type)(env, outfile)
            agent.test()
            agent.write_results()
            score_summary, _ = ev.score(outfile)
            print '\n%s' % agent_type
            pp.pprint(score_summary)


def eval_seq2seq():
    ''' Eval sequence to sequence models on val splits (iteration selected from training error) '''
    outfiles = [
        RESULT_DIR + 'seq2seq_teacher_imagenet_%s_iter_5000.json',
        RESULT_DIR + 'seq2seq_sample_imagenet_%s_iter_20000.json'
    ]
    for outfile in outfiles:
        for split in ['val_seen', 'val_unseen']:
            ev = Evaluation([split])
            score_summary, _ = ev.score(outfile % split)
            print '\n%s' % outfile
            pp.pprint(score_summary)


if __name__ == '__main__':

    eval_simple_agents()
    #eval_seq2seq()
