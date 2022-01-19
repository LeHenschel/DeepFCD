#!/bin/bash

# base directories
INPUT_DIR=${1} #/input/data/bonn/FCD/iso_FLAIR/nii
OUTPUT_DIR=${2} #/output/data/bonn/FCD/iso_FLAIR/nii
SCRIPT_DIR=${3} # /output

# original input directories
REAL_T1_DIR=${INPUT_DIR}/T1
REAL_FLAIR_DIR=${INPUT_DIR}/FLAIR
SUBJECTS=$(ls ${REAL_T1_DIR}| cut -d'_' -f1)
#SUBJECTS=106

# GAN processing --> created in here
GAN_INPUT_T1_DIR=${OUTPUT_DIR}/gan_input_T1
GAN_TARGET_FLAIR_DIR=${OUTPUT_DIR}/gan_target_FLAIR
SYNTH_FLAIR_DIR=${OUTPUT_DIR}/synth_FLAIR
DIFF_DIR=${OUTPUT_DIR}/diff_real_FLAIR-synth_FLAIR

# make directories
mkdir -p $GAN_INPUT_T1_DIR $GAN_TARGET_FLAIR_DIR $SYNTH_FLAIR_DIR $DIFF_DIR

# Run commands
for sbj in $SUBJECTS; do
    echo "Processing $sbj"
    # 1. Padding
    python3 $SCRIPT_DIR/preprocessing/create_mean_padding.py ${OUTPUT_DIR:0:-4}/png ${INPUT_DIR:0:-4}/png ${sbj}
    # 2. Create fake flairs (on GPU)
    python3 $SCRIPT_DIR/postprocessing/create_synthetic_images-OLD_SKIMAGE.py --sid $sbj --nii --nii_p $OUTPUT_DIR \
            --png_p ${OUTPUT_DIR:0:-4}/png --input ${INPUT_DIR:0:-4}/png
    # 3. Generate Difference image
    python3 $SCRIPT_DIR/postprocessing/subtract_GAN_images.py -rd ${GAN_INPUT_T1_DIR} -fd ${SYNTH_FLAIR_DIR} -s $sbj -od ${DIFF_DIR}
done

