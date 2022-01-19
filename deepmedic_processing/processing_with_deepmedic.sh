#!/bin/bash

INPUT=${1} # /input/deepmedic
OUTPUT=${2} # /output/data/deepmedic
CHANNEL=${3} # Channel version: 2ch, 3ch, 4ch, 7ch or MAP
CKPTF=${4}
GPU=${5} #cuda1

echo $GPU

MODEL=${OUTPUT}/configFiles/deepMedic_${CHANNEL}_FCD/model/modelConfig_${CHANNEL}.cfg
CKPT=${INPUT}/examples/output/saved_models/trainSession_${CHANNEL}_FCD/${CKPTF} #

for TYPE in FCD HC; do
  CONFIG=${OUTPUT}/configFiles/deepMedic_${CHANNEL}_FCD/test_berlin_${TYPE}/testConfig.cfg

  # Simple script to run deepmedic on a given input dataset; cfg-files need to be defined in advance!
  ${INPUT}/deepMedicRun -model $MODEL \
                -test $CONFIG \
                -load $CKPT \
                -dev $GPU
done