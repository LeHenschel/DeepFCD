#!/bin/bash

SCRIPTS=/output/deepmedic_processing

echo "2CH NETWORK TESTING"

${SCRIPTS}/processing_with_deepmedic.sh /input/deepmedic /output/deepmedic_processing 2ch \
                deepMedic_2ch_FCD.trainSession_2ch_FCD.final.2020-11-11.01.26.57.483745.model.ckpt \
                cuda0 &

echo "4CH NETWORK TESTING"

${SCRIPTS}/processing_with_deepmedic.sh /input/deepmedic /output/deepmedic_processing 4ch \
                deepMedic_4ch_FCD.trainSession_4ch_FCD.final.2020-06-30.21.15.09.940662.model.ckpt \
                cuda1

echo "7CH NETWORK TESTING"

${SCRIPTS}/processing_with_deepmedic.sh /input/deepmedic /output/deepmedic_processing 7ch \
                deepMedic_7ch_FCD.trainSession_7ch_FCD.final.2020-07-18.01.46.37.114342.model.ckpt \
                cuda0 &

echo "MAP NETWORK TESTING"

${SCRIPTS}/processing_with_deepmedic.sh /input/deepmedic /output/deepmedic_processing MAP \
                deepMedic_MAP_FCD.trainSession_MAP_FCD.final.2021-06-07.00.22.13.846994.model.ckpt \
                cuda1