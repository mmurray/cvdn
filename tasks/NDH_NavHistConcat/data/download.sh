#!/bin/sh

wget https://mp-dialog.s3-us-west-2.amazonaws.com/data/v1/ndh/train.json -P tasks/NDH_NavHistConcat/data/
wget https://mp-dialog.s3-us-west-2.amazonaws.com/data/v1/ndh/val_seen.json -P tasks/NDH_NavHistConcat/data/
wget https://mp-dialog.s3-us-west-2.amazonaws.com/data/v1/ndh/val_unseen.json -P tasks/NDH_NavHistConcat/data/
