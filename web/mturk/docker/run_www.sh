#!/bin/bash

export MATTERPORT_DATA_PATH=/media/jdtho/shiner/

# Run Apache/PHP with the WWW directory
docker run -it --rm \
    -e "R2R_DATA_PREFIX=R2R_data" \
    -e "CONNECTIVITY_DATA_PREFIX=connectivity" \
    -e "MATTERPORT_DATA_PREFIX=data" \
    -v $(pwd)/www:/var/www/site \
    -v $(pwd)/../../tasks/R2R/data:/var/www/site/R2R_data \
    -v $(pwd)/../../connectivity:/var/www/site/connectivity \
    -v "${MATTERPORT_DATA_PATH}:/var/www/site/data" \
    -p 8080:80 vln:chat-www

echo ${MATTERPORT_DATA_PATH}
