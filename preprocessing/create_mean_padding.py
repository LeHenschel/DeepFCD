#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  5 12:06:53 2020

@author: bdavid
"""

import os
import re
import glob
import imageio
import numpy as np
#import matplotlib.pyplot as plt
from PIL import Image
import sys


def main(OUTPATH, INPATH, SUBJ):
    INPUT_CHANNELS = 7
    if INPUT_CHANNELS % 2 == 0:
        print('Even no. of slices not supported, setting INPUT_CHANNELS to ',INPUT_CHANNELS+1)
        INPUT_CHANNELS += 1

    modalities = ['FLAIR','T1']

    #folders=['test','train']
    folders=['']
    for modality in modalities:
    
        os.makedirs(os.path.join(OUTPATH,modality+'_paddings'), exist_ok=True)
    
        for folder in folders:
        
            path_to_images=os.path.join(INPATH, modality, folder)

            first_slices=sorted(glob.glob(os.path.join(path_to_images, SUBJ +'*')))[0:INPUT_CHANNELS]
            last_slices=sorted(glob.glob(os.path.join(path_to_images, SUBJ+'*')))[-INPUT_CHANNELS:]
            
            first_mean=np.average(np.array([imageio.imread(im) for im in first_slices]),axis=0)
            last_mean=np.average(np.array([imageio.imread(im) for im in last_slices]),axis=0)

            first_padding=Image.fromarray(first_mean.astype('uint8'))
            last_padding=Image.fromarray(last_mean.astype('uint8'))
            
            first_padding.save(os.path.join(OUTPATH,modality+'_paddings',SUBJ+'_first_mean_padding.png'))
            last_padding.save(os.path.join(OUTPATH,modality+'_paddings',SUBJ+'_last_mean_padding.png'))


if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2], sys.argv[3])
