## start with the Docker 'base Tensorflow v2.1-gpu for python3' Debian-based image

FROM tensorflow/tensorflow:2.1.0-gpu-py3
ENV LANG=C.UTF-8
COPY neurodebian.gpg /neurodebian.gpg

# Install custom libraries + freesurfer 6.0 + fsl 6.0 (and necessary dependencies)
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
         python3-tk \
         python2.7 \
         file \
         build-essential \
         cmake \
         git \
         vim \
         wget \
         ca-certificates \
         bzip2 \
         libx11-6 \
         libjpeg-dev \
         libpng-dev \
         bc \
         dc \
         tar \
         zip \
         gawk \
         tcsh \
         time \
         libgomp1 \
         libglu1-mesa \
	 libglu1-mesa-dev \
	 perl-modules && \
         apt-get clean && \
         rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
	 wget -qO- https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.1.1/freesurfer-linux-centos8_x86_64-7.1.1.tar.gz | tar zxv --no-same-owner -C /opt \
    	--exclude='freesurfer/trctrain' \
    	--exclude='freesurfer/subjects/fsaverage_sym' \
    	--exclude='freesurfer/subjects/fsaverage3' \
    	--exclude='freesurfer/subjects/fsaverage4' \
    	--exclude='freesurfer/subjects/fsaverage5' \
    	--exclude='freesurfer/subjects/fsaverage6' \
    	--exclude='freesurfer/subjects/cvs_avg35' \
    	--exclude='freesurfer/subjects/cvs_avg35_inMNI152' \
    	--exclude='freesurfer/subjects/bert' \
    	--exclude='freesurfer/subjects/V1_average' \
    	--exclude='freesurfer/average/mult-comp-cor' \
    	--exclude='freesurfer/lib/cuda' \
    	--exclude='freesurfer/lib/qt'

# neurodebian
RUN wget -qO- http://neuro.debian.net/lists/bionic.au.full | tee /etc/apt/sources.list.d/neurodebian.sources.list && \
     apt-key add /neurodebian.gpg && \
     apt-get update

# FSL
RUN wget -q http://fsl.fmrib.ox.ac.uk/fsldownloads/fslinstaller.py && \
    chmod 775 fslinstaller.py && \
    python2.7 /fslinstaller.py -D -d /opt/fsl -V 6.0.4 -q && \
    rm -f /fslinstaller.py
RUN which immv || ( echo "FSLPython not properly configured; re-running" && rm -rf /opt/fsl/fslpython && /opt/fsl/etc/fslconf/fslpython_install.sh -f /opt/fsl || ( cat /tmp/fslpython*/fslpython_miniconda_installer.log && exit 1 ) )
RUN apt-get remove -y libegl1-mesa-dev && \
     apt-get autoremove -y && \
     apt-get clean && \
     rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

## Copying requirement file in docker filesystem
COPY requirements.txt /tmp
WORKDIR "/tmp"

## install pip related dependencies
RUN python3 -m pip install --trusted-host pypi.python.org -r requirements.txt

## Add FreeSurfer Environment variables (.license file needed, alternatively export FS_LICENSE=path/to/license)
ENV OS=Linux \
    FS_OVERRIDE=0 \
    FIX_VERTEX_AREA= \
    SUBJECTS_DIR=/opt/freesurfer/subjects \
    FSF_OUTPUT_FORMAT=nii.gz \
    MNI_DIR=/opt/freesurfer/mni \
    LOCAL_DIR=/opt/freesurfer/local \
    FREESURFER_HOME=/opt/freesurfer \
    FSFAST_HOME=/opt/freesurfer/fsfast \
    MINC_BIN_DIR=/opt/freesurfer/mni/bin \
    MINC_LIB_DIR=/opt/freesurfer/mni/lib \
    MNI_DATAPATH=/opt/freesurfer/mni/data \
    FMRI_ANALYSIS_DIR=/opt/freesurfer/fsfast \
    PERL5LIB=/opt/freesurfer/mni/lib/perl5/5.8.5 \
    MNI_PERL5LIB=/opt/freesurfer/mni/lib/perl5/5.8.5 \
    PYTHONUNBUFFERED=0 \
    PATH=/opt/freesurfer/bin:/opt/freesurfer/fsfast/bin:/opt/freesurfer/tktools:/opt/freesurfer/mni/bin:$PATH

## Add FSL Environment variables
ENV FSLDIR=/opt/fsl \
    FSLOUTPUTTYPE=NIFTI_GZ \
    FSLMULTIFILEQUIT=TRUE \
    FSLTCLSH=/opt/fsl/bin/fsltclsh \
    FSLWISH=/opt/fsl/bin/fslwish \
    LD_LIBRARY_PATH=/opt/fsl/lib:$LD_LIBRARY_PATH \
    PATH=/opt/fsl/bin:$PATH

## Add username upon docker creation
RUN useradd henschell --uid 4323

WORKDIR "/"