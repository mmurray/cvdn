#!/usr/bin/env python
import argparse
import json
import networkx as nx
import numpy as np


# Edited from 'tasks/R2R/utils.py'
def load_nav_graphs(scans):

    def distance(pose1, pose2):
        return ((pose1['pose'][3]-pose2['pose'][3])**2 +
                (pose1['pose'][7]-pose2['pose'][7])**2 +
                (pose1['pose'][11]-pose2['pose'][11])**2)**0.5

    graphs = {}
    for scan in scans:
        with open('../../../connectivity/%s_connectivity.json' % scan) as f:
            g = nx.Graph()
            positions = {}
            data = json.load(f)
            for i,item in enumerate(data):
                if item['included']:
                    for j,conn in enumerate(item['unobstructed']):
                        if conn and data[j]['included']:
                            positions[item['image_id']] = np.array([item['pose'][3],
                                                                    item['pose'][7], item['pose'][11]])
                            assert data[j]['unobstructed'][i], 'Graph should be undirected'
                            g.add_edge(item['image_id'], data[j]['image_id'], weight=distance(item, data[j]))
            nx.set_node_attributes(g, values=positions, name='position')
            graphs[scan] = g
    return graphs


# Spin up a server to sit and manage incoming connections.
def main(args):

    MIN_PATH_LEN = 4
    MAX_PATH_LEN = 35

    # Load resources.
    with open(args.obj_regions_fn, 'r') as f:
        house_obj_region = json.load(f)
    with open(args.region_panorama_fn, 'r') as f:
        house_region_panorama = json.load(f)

    # For every house, generate tuples of (object, start_pano, end_region, end_pano) such that
    # each (object, end_region) appears at most once and start_pano maximizes the distance between the start and
    # all end regions closest panos for the object.
    # The agent will spawn at start_pano and the gold trajectory will be shown to the end_pano, but evaluation will
    # mark correct stopping at any pano point in the end_region.
    house_target_tuple = {}
    for house in house_obj_region:
        instances = []

        # Get connectivity graph and distances.
        graph = load_nav_graphs([house])[house]
        hops = dict(nx.all_pairs_dijkstra_path(graph))

        for obj in house_obj_region[house]:
            end_regions = house_obj_region[house][obj]
            # Choose a start_pano that maximizes the distance between itself and the closest end_pano per region.
            best_start_pano = None
            best_start_pano_d = None
            for start_pano in hops.keys():
                ds_to_end_regions = []
                skip_pano = False
                for end_region in end_regions:
                    ds_to_end_region_panos = [len(hops[start_pano][end_pano])
                                              for end_pano in house_region_panorama[house][end_region]
                                              if end_pano in hops[start_pano]]
                    if len(ds_to_end_region_panos) == 0:
                        # print("WARNING: cannot reach end region '%s' in house '%s' from pano %s" %
                        #       (end_region, house, start_pano))
                        skip_pano = True
                        break  # don't consider this start_pano
                    ds_to_end_regions.append(min([len(hops[start_pano][end_pano])
                                                  for end_pano in house_region_panorama[house][end_region]
                                                  if end_pano in hops[start_pano]]))
                if skip_pano:
                    continue
                l2_d_to_end_regions = np.linalg.norm(ds_to_end_regions)
                if best_start_pano_d is None or best_start_pano_d < l2_d_to_end_regions:
                    best_start_pano = start_pano
                    best_start_pano_d = l2_d_to_end_regions  # maximize average l2 between start and potential ends.
            if best_start_pano is None:
                print("WARNING: could not find a good start_pano for object %s in house %s" % (obj, house))
                continue

            # For every end region, add a datum instance for the chosen best start_pano
            for end_region in end_regions:
                end_panos = []
                end_pano_ds = []
                for end_pano in house_region_panorama[house][end_region]:
                    if end_pano in hops[best_start_pano]:
                        end_panos.append(end_pano)
                        end_pano_ds.append(len(hops[best_start_pano][end_pano]))
                if best_start_pano not in end_panos:
                    if MIN_PATH_LEN <= min(end_pano_ds) <= MAX_PATH_LEN:
                        instances.append((obj, best_start_pano, end_region, end_panos, end_pano_ds))
                    else:
                        print("WARNING: skipping path out of bounds for object %s in house %s (len %d)"
                              % (obj, house, min(end_pano_ds)))
                else:
                    print("WARNING: skipping best start pano contained in end region for object %s in house %s"
                          % (obj, house))
        if len(instances) > 0:
            house_target_tuple[house] = instances
        else:
            print("WARNING: could not find any good paths in house %s!" % house)

    print("Writing %d tuples across %d houses to file '%s'" %
          (sum([len(house_target_tuple[h]) for h in house_target_tuple]), len(house_target_tuple), args.output_fn))
    with open(args.output_fn, 'w') as f:
        json.dump(house_target_tuple, f)
    print("... done")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--obj_regions_fn', type=str, required=True,
                        help="JSON file mapping houses to objects to regions")
    parser.add_argument('--region_panorama_fn', type=str, required=True,
                        help="JSON file mapping houses to regions to panoramas")
    parser.add_argument('--output_fn', type=str, required=True,
                        help="JSON file output of pairs")
    main(parser.parse_args())
