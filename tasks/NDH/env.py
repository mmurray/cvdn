''' Batched Room-to-Room navigation environment '''

import sys
sys.path.append('build')
import MatterSim
import csv
import numpy as np
import math
import base64
import json
import random
import networkx as nx

from utils import load_datasets, load_nav_graphs

csv.field_size_limit(sys.maxsize)


class EnvBatch():
    ''' A simple wrapper for a batch of MatterSim environments, 
        using discretized viewpoints and pretrained features '''

    def __init__(self, feature_store=None, batch_size=100, blind=False):
        if feature_store:
            print 'Loading image features from %s' % feature_store
            if blind:
                print("... and zeroing them out for 'blind' evaluation")
            tsv_fieldnames = ['scanId', 'viewpointId', 'image_w','image_h', 'vfov', 'features']
            self.features = {}
            with open(feature_store, "r+b") as tsv_in_file:
                reader = csv.DictReader(tsv_in_file, delimiter='\t', fieldnames = tsv_fieldnames)
                for item in reader:
                    self.image_h = int(item['image_h'])
                    self.image_w = int(item['image_w'])
                    self.vfov = int(item['vfov'])
                    long_id = self._make_id(item['scanId'], item['viewpointId'])
                    if not blind:
                        self.features[long_id] = np.frombuffer(base64.decodestring(item['features']),
                                dtype=np.float32).reshape((36, 2048))
                    else:
                        self.features[long_id] = np.zeros((36, 2048), dtype=np.float32)
        else:
            print 'Image features not provided'
            self.features = None
            self.image_w = 640
            self.image_h = 480
            self.vfov = 60
        self.batch_size = batch_size
        self.sim = MatterSim.Simulator()
        self.sim.setRenderingEnabled(False)
        self.sim.setDiscretizedViewingAngles(True)
        self.sim.setBatchSize(self.batch_size)
        self.sim.setCameraResolution(self.image_w, self.image_h)
        self.sim.setCameraVFOV(math.radians(self.vfov))
        self.sim.initialize()

    def _make_id(self, scanId, viewpointId):
        return scanId + '_' + viewpointId   

    def newEpisodes(self, scanIds, viewpointIds, headings):
        self.sim.newEpisode(scanIds, viewpointIds, headings, [0]*self.batch_size)
  
    def getStates(self):
        ''' Get list of states augmented with precomputed image features. rgb field will be empty. '''
        feature_states = []
        for state in self.sim.getState():
            long_id = self._make_id(state.scanId, state.location.viewpointId)
            if self.features:
                feature = self.features[long_id][state.viewIndex,:]
                feature_states.append((feature, state))
            else:
                feature_states.append((None, state))
        return feature_states

    def makeActions(self, actions):
        ''' Take an action using the full state dependent action interface (with batched input). 
            Every action element should be an (index, heading, elevation) tuple. '''
        ix = []
        heading = []
        elevation = []
        for i,h,e in actions:
            ix.append(int(i))
            heading.append(float(h))
            elevation.append(float(e))
        self.sim.makeAction(ix, heading, elevation)

    def makeSimpleActions(self, simple_indices):
        ''' Take an action using a simple interface: 0-forward, 1-turn left, 2-turn right, 3-look up, 4-look down. 
            All viewpoint changes are 30 degrees. Forward, look up and look down may not succeed - check state.
            WARNING - Very likely this simple interface restricts some edges in the graph. Parts of the
            environment may not longer be navigable. '''
        actions = []
        for i, index in enumerate(simple_indices):
            if index == 0:
                actions.append((1, 0, 0))
            elif index == 1:
                actions.append((0,-1, 0))
            elif index == 2:
                actions.append((0, 1, 0))
            elif index == 3:
                actions.append((0, 0, 1))
            elif index == 4:
                actions.append((0, 0,-1))
            else:
                sys.exit("Invalid simple action");
        self.makeActions(actions)


class R2RBatch():
    ''' Implements the Room to Room navigation task, using discretized viewpoints and pretrained features '''

    def __init__(self, feature_store, batch_size=100, seed=10, splits=['train'], tokenizer=None,
                 path_type='planner_path', history='target', blind=False):
        self.env = EnvBatch(feature_store=feature_store, batch_size=batch_size, blind=blind)
        self.data = []
        self.scans = []
        for item in load_datasets(splits):

            # For every dialog history, stitch together a single instruction string.
            self.scans.append(item['scan'])
            new_item = dict(item)
            new_item['inst_idx'] = item['inst_idx']
            if history == 'none':  # no language input at all
                new_item['instructions'] = ''
                if tokenizer:
                    new_item['instr_encoding'] = tokenizer.encode_sentence('')
            elif history == 'target' or len(item['dialog_history']) == 0:  # Have to use target only if no dialog history.
                tar = item['target']
                new_item['instructions'] = '<TAR> ' + tar
                if tokenizer:
                    new_item['instr_encoding'] = tokenizer.encode_sentence([tar], seps=['<TAR>'])
            elif history == 'oracle_ans':
                ora_a = item['dialog_history'][-1]['message']  # i.e., the last oracle utterance.
                tar = item['target']
                new_item['instructions'] = '<ORA> ' + ora_a + ' <TAR> ' + tar
                if tokenizer:
                    new_item['instr_encoding'] = tokenizer.encode_sentence([ora_a, tar], seps=['<ORA>', '<TAR>'])
            elif history == 'nav_q_oracle_ans':
                nav_q = item['dialog_history'][-2]['message']
                ora_a = item['dialog_history'][-1]['message']
                tar = item['target']
                new_item['instructions'] = '<NAV> ' + nav_q + ' <ORA> ' + ora_a + ' <TAR> ' + tar
                if tokenizer:
                    qa_enc = tokenizer.encode_sentence([nav_q, ora_a, tar], seps=['<NAV>', '<ORA>', '<TAR>'])
                    new_item['instr_encoding'] = qa_enc
            elif history == 'all':
                dia_inst = ''
                sentences = []
                seps = []
                for turn in item['dialog_history']:
                    sentences.append(turn['message'])
                    sep = '<NAV>' if turn['role'] == 'navigator' else '<ORA>'
                    seps.append(sep)
                    dia_inst += sep + ' ' + turn['message'] + ' '
                sentences.append(item['target'])
                seps.append('<TAR>')
                dia_inst += '<TAR> ' + item['target']
                new_item['instructions'] = dia_inst
                if tokenizer:
                    dia_enc = tokenizer.encode_sentence(sentences, seps=seps)
                    new_item['instr_encoding'] = dia_enc

            # If evaluating against 'trusted_path', we need to calculate the trusted path and instantiate it.
            if path_type == 'trusted_path':
                # The trusted path is either the planner_path or the player_path depending on whether the player_path
                # contains the planner_path goal (e.g., stricter planner oracle success of player_path
                # indicates we can 'trust' it, otherwise we fall back to the planner path for supervision).
                # Hypothesize that this will combine the strengths of good human exploration with the known good, if
                # short, routes the planner uses.
                planner_goal = item['planner_path'][-1]  # this could be length 1 if "plan" is to not move at all.
                if planner_goal in item['player_path'][1:]:  # player walked through planner goal (did not start on it)
                    new_item['trusted_path'] = item['player_path'][:]  # trust the player.
                else:
                    new_item['trusted_path'] = item['planner_path'][:]  # trust the planner.

            self.data.append(new_item)
        self.scans = set(self.scans)
        self.splits = splits
        self.seed = seed
        random.seed(self.seed)
        random.shuffle(self.data)
        self.ix = 0
        self.batch_size = batch_size
        self._load_nav_graphs()
        self.path_type = path_type
        print 'R2RBatch loaded with %d instructions, using splits: %s' % (len(self.data), ",".join(splits))

    def _load_nav_graphs(self):
        ''' Load connectivity graph for each scan, useful for reasoning about shortest paths '''
        print 'Loading navigation graphs for %d scans' % len(self.scans)
        self.graphs = load_nav_graphs(self.scans)
        self.paths = {}
        for scan,G in self.graphs.iteritems(): # compute all shortest paths
            self.paths[scan] = dict(nx.all_pairs_dijkstra_path(G))
        self.distances = {}
        for scan,G in self.graphs.iteritems(): # compute all shortest paths
            self.distances[scan] = dict(nx.all_pairs_dijkstra_path_length(G))

    def _next_minibatch(self):
        batch = self.data[self.ix:self.ix+self.batch_size]
        if len(batch) < self.batch_size:
            random.shuffle(self.data)
            self.ix = self.batch_size - len(batch)
            batch += self.data[:self.ix]
        else:
            self.ix += self.batch_size
        self.batch = batch

    def reset_epoch(self):
        ''' Reset the data index to beginning of epoch. Primarily for testing. 
            You must still call reset() for a new episode. '''
        self.ix = 0

    def _shortest_path_action(self, state, goalViewpointId):
        ''' Determine next action on the shortest path to goal, for supervised training. '''
        if state.location.viewpointId == goalViewpointId:
            return (0, 0, 0) # do nothing
        path = self.paths[state.scanId][state.location.viewpointId][goalViewpointId]
        nextViewpointId = path[1]
        # Can we see the next viewpoint?
        for i,loc in enumerate(state.navigableLocations):
            if loc.viewpointId == nextViewpointId:
                # Look directly at the viewpoint before moving
                if loc.rel_heading > math.pi/6.0:
                      return (0, 1, 0) # Turn right
                elif loc.rel_heading < -math.pi/6.0: 
                      return (0,-1, 0) # Turn left
                elif loc.rel_elevation > math.pi/6.0 and state.viewIndex//12 < 2:
                      return (0, 0, 1) # Look up
                elif loc.rel_elevation < -math.pi/6.0 and state.viewIndex//12 > 0:
                      return (0, 0,-1) # Look down            
                else:
                      return (i, 0, 0) # Move
        # Can't see it - first neutralize camera elevation
        if state.viewIndex//12 == 0:
            return (0, 0, 1) # Look up
        elif state.viewIndex//12 == 2:
            return (0, 0,-1) # Look down
        # Otherwise decide which way to turn
        pos = [state.location.x, state.location.y, state.location.z]
        target_rel = self.graphs[state.scanId].node[nextViewpointId]['position'] - pos
        target_heading = math.pi/2.0 - math.atan2(target_rel[1], target_rel[0]) # convert to rel to y axis
        if target_heading < 0:
            target_heading += 2.0*math.pi
        if state.heading > target_heading and state.heading - target_heading < math.pi:
            return (0,-1, 0) # Turn left  
        if target_heading > state.heading and target_heading - state.heading > math.pi:
            return (0,-1, 0) # Turn left
        return (0, 1, 0) # Turn right

    def _get_obs(self):
        obs = []
        for i,(feature,state) in enumerate(self.env.getStates()):
            item = self.batch[i]
            if self.path_type in item:
                target = item[self.path_type][-1]
            else:
                target = item['start_pano']['pano']
            obs.append({
                'inst_idx': item['inst_idx'],
                'scan': state.scanId,
                'viewpoint': state.location.viewpointId,
                'viewIndex': state.viewIndex,
                'heading': state.heading,
                'elevation': state.elevation,
                'feature': feature,
                'step': state.step,
                'navigableLocations': state.navigableLocations,
                'instructions': item['instructions'],
                'teacher': self._shortest_path_action(state, target),
            })
            if 'instr_encoding' in item:
                obs[-1]['instr_encoding'] = item['instr_encoding']
        return obs

    def reset(self):
        ''' Load a new minibatch / episodes. '''
        self._next_minibatch()
        scanIds = [item['scan'] for item in self.batch]
        if self.path_type in self.batch[0]:
            viewpointIds = [item[self.path_type][0] for item in self.batch]
        else:
            # In the test dataset there is no path provided, so we just load the start viewpoint
            viewpointIds = [item['start_pano']['pano'] for item in self.batch]
        headings = [item['start_pano']['heading'] for item in self.batch]
        self.env.newEpisodes(scanIds, viewpointIds, headings)
        return self._get_obs()   

    def step(self, actions):
        ''' Take action (same interface as makeActions) '''
        self.env.makeActions(actions)
        return self._get_obs()


