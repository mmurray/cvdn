#!/bin/sh

wget https://cvdn.dev/dataset/NDH/train_val/train.json -P tasks/NDH/data/
wget https://cvdn.dev/dataset/NDH/train_val/val_seen.json -P tasks/NDH/data/
wget https://cvdn.dev/dataset/NDH/train_val/val_unseen.json -P tasks/NDH/data/
