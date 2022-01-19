#!/bin/bash


# export FREESURFER License and FSLOUTPUTTYPE (set to nii.gz)
export FS_LICENSE=/output/postprocessing/.license
export OMP_NUM_THREADS=1

# base directories
INPUT_DIR=/input/data/berlin/analyses/FCD/nii
OUTPUT_DIR=/output/data/berlin/analyses/FCD/nii

# original input directories
REAL_T1_DIR=${INPUT_DIR}/T1
ROI_DIR=${INPUT_DIR}/ROI
DEEPMEDIC_INPUT=${OUTPUT_DIR}/deepmedic_input


SUBJECTS=$(ls ${REAL_T1_DIR}| cut -d'_' -f1)


# Run commands
for sbj in $SUBJECTS; do
    echo "Processing $sbj"
    mri_convert -rl ${DEEPMEDIC_INPUT}/${sbj}_T1.nii.gz -rt nearest ${ROI_DIR}/${sbj}_roi.nii.gz ${DEEPMEDIC_INPUT}/${sbj}_roi.nii.gz
done