#!/usr/bin/env python
""" Script for preparing and uploading house scan data to S3 """

import json
import os
import argparse
import tempfile
import shutil
import zipfile
import networkx as nx
import boto3
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="./data/v1/scans")
parser.add_argument("--connectivity", default="../../../connectivity")
args = parser.parse_args()

s3 = boto3.client('s3')


def load_gold_paths(scans):
    def distance(pose1, pose2):
        return ((pose1['pose'][3]-pose2['pose'][3])**2 +
                (pose1['pose'][7]-pose2['pose'][7])**2 +
                (pose1['pose'][11]-pose2['pose'][11])**2)**0.5

    paths = {}
    for scan in scans:
        with open(os.path.join(args.connectivity, '%s_connectivity.json' % scan)) as f:
            g = nx.Graph()
            positions = {}
            data = json.load(f)
            for i, item in enumerate(data):
                if item['included']:
                    for j, conn in enumerate(item['unobstructed']):
                        if conn and data[j]['included']:
                            positions[item['image_id']] = np.array([item['pose'][3],
                                                                    item['pose'][7], item['pose'][11]])
                            assert data[j]['unobstructed'][i], 'Graph should be undirected'
                            g.add_edge(
                                item['image_id'], data[j]['image_id'], weight=distance(item, data[j]))
            nx.set_node_attributes(g, values=positions, name='position')
            paths[scan] = dict(nx.all_pairs_dijkstra_path(g))
    return paths


with open(os.path.join(args.connectivity, 'scans_dialog.txt')) as scans_txt_file:

    scans = [scan.strip() for scan in scans_txt_file.readlines()]
    gold_paths = load_gold_paths(scans)

    for scan in scans:
        # Create a temp folder
        tmp_dir = tempfile.mkdtemp()

        # Move and unzip just the skybox images folder
        scan_dir = os.path.join(args.input, scan)
        shutil.copy(os.path.join(
            scan_dir, "matterport_skybox_images.zip"), tmp_dir)
        zip_ref = zipfile.ZipFile(os.path.join(
            tmp_dir, "matterport_skybox_images.zip"), 'r')
        zip_ref.extractall(os.path.join(
            tmp_dir))
        zip_ref.close()

        shutil.move(os.path.join(tmp_dir, scan, "matterport_skybox_images"),
                    os.path.join(tmp_dir, "matterport_skybox_images"))

        shutil.rmtree(os.path.join(tmp_dir, scan))
        os.remove(os.path.join(tmp_dir, "matterport_skybox_images.zip"))

        # Compute optimal policies
        policies_dir = os.path.join(tmp_dir, "policies")
        for goal in gold_paths[scan]:
            if not os.path.exists(policies_dir):
                os.makedirs(policies_dir)
            with open(os.path.join(policies_dir, goal + '.json'), 'w') as policy_file:
                policy_file.write(json.dumps(gold_paths[scan][goal]))

        # Upload to S3 with public read permissions
        for root, dirs, files in os.walk(tmp_dir):
            for filename in files:
                local_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_path, tmp_dir)
                s3_path = os.path.join("data/v1/scans", scan, relative_path)
                s3.upload_file(local_path, "mp-dialog", s3_path,
                               ExtraArgs={'ACL': 'public-read'})

        # Cleanup our temporary folder
        shutil.rmtree(tmp_dir)

        print("done with " + scan)
