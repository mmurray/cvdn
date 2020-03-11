#!/bin/sh

wget https://cvdn.dev/dataset/NDH/train_val/train.json -P tasks/NDH/data/
wget https://cvdn.dev/dataset/NDH/train_val/val_seen.json -P tasks/NDH/data/
wget https://cvdn.dev/dataset/NDH/train_val/val_unseen.json -P tasks/NDH/data/
wget https://cvdn.dev/dataset/NDH/test_cleaned/test_cleaned.json -P tasks/NDH/data/test.json
