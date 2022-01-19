#!/bin/bash

# Simple script for translating the input and output of the generator network to the native t1-space, intensity transformation (zero mean unit variance) and mask generation. Additionally to the difference image, we produce a outlier weight image using mri_robust_register (see ) Also registering MAP morphometric maps, if specified.
# WIP: Should be redone in nipype at some point. Also registration ultimately not necessary if generator trained in native space.
# space in the first place.
# Written by: Bastian David, M.Sc.

# Do you want to use morphometric maps?
MAP=true

# export FREESURFER License and FSLOUTPUTTYPE (set to nii.gz)
export FS_LICENSE=/output/postprocessing/.license
export OMP_NUM_THREADS=1
export FSLOUTPUTTYPE=NIFTI_GZ

# base directories
INPUT_DIR=/input/data/berlin/analyses/FCD/nii
OUTPUT_DIR=/output/data/berlin/analyses/FCD/nii

# original input directories
REAL_T1_DIR=${INPUT_DIR}/T1
REAL_FLAIR_DIR=${INPUT_DIR}/FLAIR
MAP_DIR=${INPUT_DIR}/berlin_morphometric_maps/FCD # morphometric_maps (also change order Sid_T1) #${INPUT_DIR}/MAP_DeepFCD
ROI_DIR=${INPUT_DIR}/ROI

# GAN processing
GAN_INPUT_T1_DIR=${OUTPUT_DIR}/gan_input_T1
GAN_TARGET_FLAIR_DIR=${OUTPUT_DIR}/gan_target_FLAIR
SYNTH_FLAIR_DIR=${OUTPUT_DIR}/synth_FLAIR
DIFF_DIR=${OUTPUT_DIR}/diff_real_FLAIR-synth_FLAIR

# post-processing of GAN results and MAP --> created in here
MATRICES_DIR=${OUTPUT_DIR}/matrices
DEEPMEDIC_INPUT=${OUTPUT_DIR}/deepmedic_input
tmp_dir=${OUTPUT_DIR}/tmp
log_dir=${OUTPUT_DIR}/log

# make directories
mkdir -p $MATRICES_DIR $tmp_dir $DEEPMEDIC_INPUT $log_dir

# define subjects (not necessary if using parallelized wrapper script)
#SUBJECTS=$(ls ${T1_DIR}| cut -d'_' -f1)
SUBJECTS=$1

# define ROIs not being purged (filtering out mostly subcortical structures in this step)
rois="3 2 24 41 42 77 78 79 80 81 82 100 109"

function RunIt()
{
# parameters
# $1 : cmd  (command to run)
# $2 : LF   (log file)
# $3 : CMDF (command file) optional
# if CMDF is passed, then LF is ignored and cmd is echoed into CMDF and not run
  cmd=$1
  LF=$2
  if [[ $# -eq 3 ]]
  then
    CMDF=$3
    echo "echo \"$cmd\" " |& tee -a $CMDF
    echo "$timecmd $cmd " |& tee -a $CMDF
    echo "if [ \${PIPESTATUS[0]} -ne 0 ] ; then exit 1 ; fi" >> $CMDF
  else
    echo $cmd |& tee -a $LF
    $timecmd $cmd |& tee -a $LF
    if [ ${PIPESTATUS[0]} -ne 0 ] ; then exit 1 ; fi
  fi
}


for sbj in $SUBJECTS
do
  # Set up log file
  LF=$log_dir/$sbj/fcd_gan.log
  mkdir $log_dir/$sbj
  if [ $LF != /dev/null ] ; then  rm -f $LF ; fi
  echo "Log file for FCD GAN Processing" >> $LF
  date  |& tee -a $LF
  echo "Processing $sbj" |& tee -a $LF
  echo "" |& tee -a $LF

  cmd="flirt -in ${REAL_T1_DIR}/${sbj}_T1.nii.gz -ref ${REAL_T1_DIR}/${sbj}_T1.nii.gz -applyisoxfm 0.8 -nosearch -noresampblur -cost normmi -interp spline -out ${tmp_dir}/${sbj}_T1"
  RunIt "$cmd" $LF

  cmd="flirt -in ${REAL_FLAIR_DIR}/${sbj}_FLAIR.nii.gz -ref ${tmp_dir}/${sbj}_T1 -omat ${MATRICES_DIR}/${sbj}_FLAIR_2_T1.mat -out ${tmp_dir}/${sbj}_FLAIR -noresampblur -interp spline"
  RunIt "$cmd" $LF
  cmd="flirt -in ${ROI_DIR}/${sbj}_roi -ref ${tmp_dir}/${sbj}_T1 -applyxfm -init ${MATRICES_DIR}/${sbj}_FLAIR_2_T1.mat -out ${DEEPMEDIC_INPUT}/${sbj}_roi -interp nearestneighbour"
  RunIt "$cmd" $LF

  cmd="flirt -in ${GAN_INPUT_T1_DIR}/${sbj}_* -ref ${tmp_dir}/${sbj}_T1 -omat ${MATRICES_DIR}/${sbj}_gan_input_T1_2_T1.mat -nosearch -noresampblur -cost normmi -interp spline"
  RunIt "$cmd" $LF

  cmd="flirt -in ${DIFF_DIR}/${sbj}_* -ref ${tmp_dir}/${sbj}_T1 -applyxfm -init ${MATRICES_DIR}/${sbj}_gan_input_T1_2_T1.mat -nosearch -noresampblur -cost normmi -interp spline -out ${DEEPMEDIC_INPUT}/${sbj}_diff"
  RunIt "$cmd" $LF

  cmd="bet ${tmp_dir}/${sbj}_T1 ${tmp_dir}/${sbj}_bet_T1 -R"
  RunIt "$cmd" $LF
  cmd="fast -g -o ${tmp_dir}/${sbj} ${tmp_dir}/${sbj}_bet_T1"
  RunIt "$cmd" $LF

  cmd="fslmaths ${tmp_dir}/${sbj}_seg_1 -add ${tmp_dir}/${sbj}_seg_2 ${tmp_dir}/${sbj}_gmwm"
  RunIt "$cmd" $LF

  cmd="fslmaths ${tmp_dir}/${sbj}_gmwm -fillh ${tmp_dir}/${sbj}_gmwm"
  RunIt "$cmd" $LF

  cmd="fslmaths ${tmp_dir}/${sbj}_gmwm -kernel sphere 1 -ero ${tmp_dir}/${sbj}_gmwm_eroded"
  RunIt "$cmd" $LF

  cmd="samseg --t1w ${tmp_dir}/${sbj}_T1.nii.gz --flair ${tmp_dir}/${sbj}_FLAIR.nii.gz --refmode t1w --o ${tmp_dir}/${sbj} --no-save-warp --threads 1 --pallidum-separate"
  RunIt "$cmd" $LF
  cmd="mri_label2vol --seg ${tmp_dir}/${sbj}/seg.mgz --temp ${tmp_dir}/${sbj}_T1.nii.gz --o ${tmp_dir}/${sbj}/seg_reg.nii --regheader ${tmp_dir}/${sbj}/seg.mgz"
  RunIt "$cmd" $LF

  cmd="fslmaths ${tmp_dir}/${sbj}/seg_reg.nii -mul 0 ${tmp_dir}/${sbj}_only_cortical_structures"
  RunIt "$cmd" $LF

  for roi in $rois
  do

    cmd="fslmaths ${tmp_dir}/${sbj}/seg_reg.nii -thr ${roi} -uthr ${roi} -bin ${tmp_dir}/${sbj}_roi_tmp"
    RunIt "$cmd" $LF
    cmd="fslmaths ${tmp_dir}/${sbj}_only_cortical_structures -add ${tmp_dir}/${sbj}_roi_tmp ${tmp_dir}/${sbj}_only_cortical_structures"
    RunIt "$cmd" $LF

  done

  cmd="fslmaths ${tmp_dir}/${sbj}_gmwm_eroded -mul ${tmp_dir}/${sbj}_only_cortical_structures ${tmp_dir}/${sbj}_gmwm_eroded"
  RunIt "$cmd" $LF

  cmd="fslmaths ${tmp_dir}/${sbj}_gmwm_eroded -kernel sphere 1 -ero ${tmp_dir}/${sbj}_gmwm_eroded_ero"
  RunIt "$cmd" $LF

  cmd="fslmaths ${tmp_dir}/${sbj}_gmwm_eroded_ero -kernel sphere 1 -dilF ${DEEPMEDIC_INPUT}/${sbj}_mask"
  RunIt "$cmd" $LF
  # intermediate cleaning
  #rm -rf ${tmp_dir}/${sbj}

  # normalizing difference
  read -r mean std <<< $(fslstats ${DEEPMEDIC_INPUT}/${sbj}_diff -k ${DEEPMEDIC_INPUT}/${sbj}_mask -m -s)
  cmd="fslmaths ${DEEPMEDIC_INPUT}/${sbj}_diff -sub $mean -div $std -mul ${DEEPMEDIC_INPUT}/${sbj}_mask ${DEEPMEDIC_INPUT}/${sbj}_diff"
  RunIt "$cmd" $LF

  # normalizing T1
  read -r mean std <<< $(fslstats ${tmp_dir}/${sbj}_T1 -k ${DEEPMEDIC_INPUT}/${sbj}_mask -m -s)
  cmd="fslmaths ${tmp_dir}/${sbj}_T1 -sub $mean -div $std ${DEEPMEDIC_INPUT}/${sbj}_T1"
  RunIt "$cmd" $LF

  # normalizing FLAIR
  read -r mean std <<< $(fslstats ${tmp_dir}/${sbj}_FLAIR -k ${DEEPMEDIC_INPUT}/${sbj}_mask -m -s)
  cmd="fslmaths ${tmp_dir}/${sbj}_FLAIR -sub $mean -div $std ${DEEPMEDIC_INPUT}/${sbj}_FLAIR"
  RunIt "$cmd" $LF
  
  if $MAP
  then

    # normalizing junction map
    cmd="imcp ${MAP_DIR}/T1_${sbj}_junction_z_score ${tmp_dir}/T1_${sbj}_junction_z_score"
    RunIt "$cmd" $LF

    cmd="fslcpgeom ${REAL_T1_DIR}/${sbj}_T1 ${tmp_dir}/T1_${sbj}_junction_z_score"
    RunIt "$cmd" $LF

    cmd="flirt -in ${tmp_dir}/T1_${sbj}_junction_z_score -ref ${tmp_dir}/T1_${sbj}_junction_z_score -applyisoxfm 0.8 -nosearch -noresampblur -cost normmi -interp spline -out ${tmp_dir}/T1_${sbj}_junction_z_score"
    RunIt "$cmd" $LF

    read -r mean std <<< $(fslstats ${tmp_dir}/T1_${sbj}_junction_z_score -k ${DEEPMEDIC_INPUT}/${sbj}_mask -m -s)
    cmd="fslmaths ${tmp_dir}/T1_${sbj}_junction_z_score -sub $mean -div $std -mul ${DEEPMEDIC_INPUT}/${sbj}_mask ${DEEPMEDIC_INPUT}/${sbj}_junction"
    RunIt "$cmd" $LF

    # normalizing extension map
    cmd="imcp ${MAP_DIR}/T1_${sbj}_extension_z_score ${tmp_dir}/T1_${sbj}_extension_z_score"
    RunIt "$cmd" $LF
    cmd="fslcpgeom ${REAL_T1_DIR}/${sbj}_T1 ${tmp_dir}/T1_${sbj}_extension_z_score"
    RunIt "$cmd" $LF

    cmd="flirt -in ${tmp_dir}/T1_${sbj}_extension_z_score -ref ${tmp_dir}/T1_${sbj}_extension_z_score -applyisoxfm 0.8 -nosearch -noresampblur -cost normmi -interp spline -out ${tmp_dir}/T1_${sbj}_extension_z_score"
    RunIt "$cmd" $LF

    read -r mean std <<< $(fslstats ${tmp_dir}/T1_${sbj}_extension_z_score -k ${DEEPMEDIC_INPUT}/${sbj}_mask -m -s)
    cmd="fslmaths ${tmp_dir}/T1_${sbj}_extension_z_score -sub $mean -div $std -mul ${DEEPMEDIC_INPUT}/${sbj}_mask ${DEEPMEDIC_INPUT}/${sbj}_extension"
    RunIt "$cmd" $LF

    # normalzing thickness map
    cmd="imcp ${MAP_DIR}/T1_${sbj}_thickness_z_score ${tmp_dir}/T1_${sbj}_thickness_z_score"
    RunIt "$cmd" $LF
    cmd="fslcpgeom ${REAL_T1_DIR}/${sbj}_T1 ${tmp_dir}/T1_${sbj}_thickness_z_score"
    RunIt "$cmd" $LF

    cmd="flirt -in ${tmp_dir}/T1_${sbj}_thickness_z_score -ref ${tmp_dir}/T1_${sbj}_thickness_z_score -applyisoxfm 0.8 -nosearch -noresampblur -cost normmi -interp spline -out ${tmp_dir}/T1_${sbj}_thickness_z_score"
    RunIt "$cmd" $LF

    read -r mean std <<< $(fslstats ${tmp_dir}/T1_${sbj}_thickness_z_score -k ${DEEPMEDIC_INPUT}/${sbj}_mask -m -s)
    cmd="fslmaths ${tmp_dir}/T1_${sbj}_thickness_z_score -sub $mean -div $std -mul ${DEEPMEDIC_INPUT}/${sbj}_mask ${DEEPMEDIC_INPUT}/${sbj}_thickness"
    RunIt "$cmd" $LF
    
  fi

  # creating weight map using mri_robust_register
  cmd="mri_robust_register --mov ${GAN_TARGET_FLAIR_DIR}/${sbj}_* --dst ${SYNTH_FLAIR_DIR}/${sbj}_* --lta ${tmp_dir}/${sbj}.lta --weights ${tmp_dir}/${sbj}_weights.nii --satit"
  RunIt "$cmd" $LF
  cmd="flirt -in ${tmp_dir}/${sbj}_weights.nii -ref ${tmp_dir}/${sbj}_T1 -applyxfm -init ${MATRICES_DIR}/${sbj}_gan_input_T1_2_T1.mat -nosearch -noresampblur -cost normmi -interp spline -out ${tmp_dir}/${sbj}_weights_reg"
  RunIt "$cmd" $LF
  read -r mean std <<< $(fslstats ${tmp_dir}/${sbj}_weights_reg -k ${DEEPMEDIC_INPUT}/${sbj}_mask -m -s)
  cmd="fslmaths ${tmp_dir}/${sbj}_weights_reg -sub $mean -div $std -mul ${DEEPMEDIC_INPUT}/${sbj}_mask ${DEEPMEDIC_INPUT}/${sbj}_weights"
  RunIt "$cmd" $LF

  # cleaning up temporary directory
  #rm -rf ${tmp_dir}/${sbj}_* ${tmp_dir}/${sbj}

done
