#!/bin/bash

# Wrapper for preprocessing_for_deepmedic.sh

# Written by: Bastian David, M.Sc.
echo ""
echo "#########################################################################"
echo "#################       PRE-DEEPMEDIC PROCESSING       ##################"
echo "#########################################################################"
echo ""


# Input and output directories
INPUT_DIR=/input/data/berlin/analyses/FCD/nii
OUTPUT_DIR=/output/data/berlin/analyses/FCD/nii
SCRIPT_DIR=/output
REAL_T1_DIR=${INPUT_DIR}/T1

# temporary directory
MATRICES_DIR=${OUTPUT_DIR}/matrices
tmp_dir=${OUTPUT_DIR}/tmp


# define subjects here
SUBJECTS=$(ls ${REAL_T1_DIR}| cut -d'_' -f1)
#SUBJECTS=3022

# Run GAN (sequential)
echo ""
echo "STARTING GAN SYNTHETIC T2 GENERATION"
echo ""

#${SCRIPT_DIR}/postprocessing/run_gan.sh ${INPUT_DIR} ${OUTPUT_DIR} ${SCRIPT_DIR} ${INPUT_DIR:0:-4}/png ${OUTPUT_DIR:0:-4}/png

echo ""
echo "All done."

# Run post-processing (Parallel)
max_cores=$(grep -c ^processor /proc/cpuinfo)
#echo "How many cores shall be used? [1-$max_cores]:"
#read cores
cores=50


if [[ "$cores" =~ ^[0-9]+$ ]] && [ "$cores" -ge 1 -a "$cores" -le $max_cores ];
then
    echo ""
    echo "$cores cores will be used."

else
    echo ""
    echo "Invalid input - Terminating script."
    exit 1
fi


echo ""
echo "STARTING PARALLEL PROCESSING"
echo ""
echo "Processing list:"
echo ""


echo $SUBJECTS | xargs -n 1 -P $cores ${SCRIPT_DIR}/postprocessing/preprocessing_for_deepmedic.sh | grep "Processing"

echo ""
echo "All done. Cleaning directory."
rm -rf ${tmp_dir} ${MATRICES_DIR}
