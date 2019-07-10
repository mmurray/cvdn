#!/bin/bash

# Run both docker containers in the background
docker run -d -v $(pwd)/www/client:/client -v $(pwd)/www/log:/log -v $(pwd)/house_target_tuple.json:/house_target_tuple.json -v $(pwd)/tasks/dialog_navigation/all.json:/all.json vln:chat-server
docker run -d \
    -v $(pwd)/www/client:/var/www/site/client -v $(pwd)/www/log:/var/www/site/log -v $(pwd)/www/feedback:/var/www/site/feedback  -v $(pwd)/www/.well-known:/var/www/site/.well-known \
    -v /etc/letsencrypt/live/mp-dialog.ml/privkey.pem:/etc/ssl/privkey.pem \
    -v /etc/letsencrypt/live/mp-dialog.ml/fullchain.pem:/etc/ssl/fullchain.pem \
    -e "R2R_DATA_PREFIX=https://s3.us-west-2.amazonaws.com/mp-dialog/data/v1/r2r" \
    -e "CONNECTIVITY_DATA_PREFIX=https://s3.us-west-2.amazonaws.com/mp-dialog/data/v1/connectivity" \
    -e "MATTERPORT_DATA_PREFIX=https://s3.us-west-2.amazonaws.com/mp-dialog/data" \
    -p 80:80 -p 443:443 vln:chat-www

