#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 16:06:35 2020

Script to apply the adversarially trained generator network (U-net) to create synthetic 
MR-images.
Images will be saved as PNGs. Images in RAW_OUTPATH are saved without post-hoc intensity
scaling. I recommend using the images in OUTPATH instead, after histogram matching and
intensity scaling for best results.
IMPORTANT: Saving and loading the keras model with CPU at the moment only works
with the tf.nightly build! GPU version should also work with the stable 2.1.0 version

@author: bdavid
"""

from __future__ import absolute_import, division, print_function, unicode_literals
# disable messages from tensorflow on startup (i.e INFO and WARNINGS are filtered with 2)
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf

import os
import numpy as np
import glob
from PIL import Image, ImageChops
# from skimage.exposure import match_histograms
from skimage.transform import match_histograms
import nibabel as nib
from tqdm import tqdm
import argparse


def setup_options():
    # -------- USER INPUT ----------
    parser = argparse.ArgumentParser(description='Synthetic Image Generation with GAN')

    parser.add_argument(
        "--model",
        dest="MODEL",
        help="Model to use for generatino (default: T1_2_FLAIR)",
        default="../models/T1_2_FLAIR_cor/generator",
        type=str,
    )

    parser.add_argument(
        "--dir",
        dest="DIRECTION",
        help="Mapping direction (default; real-fake)",
        default="real-fake",
        type=str,
    )

    parser.add_argument(
        "--im",
        dest="INPUT_MODALITY",
        help="Modality of input image",
        default="T1", choices=["T1", "FLAIR"],
        type=str,
    )

    parser.add_argument(
        "--om",
        dest="TARGET_MODALITY",
        help="Modality of synthetic image",
        default="FLAIR", choices=["T1", "FLAIR"],
        type=str,
    )

    parser.add_argument(
        "--png_p",
        dest="DATAPATH",
        help="Output png-data. Default: /output/data/bonn/FCD/iso_FLAIR/png",
        default="/output/data/bonn/FCD/iso_FLAIR/png",
        type=str,
    )

    parser.add_argument(
        "--nii_p",
        dest="NIIPATH",
        help="Output nii-data. Default: /output/data/bonn/FCD/iso_FLAIR/nii",
        default="/output/data/bonn/FCD/iso_FLAIR/nii",
        type=str,
    )

    parser.add_argument(
        "--input",
        dest="INPUT",
        help="Input data. Default: /input/data/bonn/FCD/iso_FLAIR/png",
        default="/input/data/bonn/FCD/iso_FLAIR/png",
        type=str,
    )

    parser.add_argument(
        "--sid",
        dest="SUBJID",
        help="Subject name. If none is given, all files will be processed (default)",
        default="",
        type=str,
    )

    parser.add_argument(
        "--nii",
        dest="CREATE_NIFTI", action="store_true", default=False,
        help="Turn on to create niftis for input, synthetic and diff images.",
    )

    parser.add_argument(
        "--ds",
        dest="DATASET",
        help="Directory prefix (Test, Train, None (=default))",
        default="", choices=["test", "train", ""],
        type=str,
    )

    parser.add_argument(
        "--bs",
        dest="BUFFER_SIZE",
        help="Size of Buffer to use",
        default=400,
        type=int,
    )

    parser.add_argument(
        "--batch_size",
        dest="BATCH_SIZE",
        help="Batch size for model inference (default=1)",
        default=1,
        type=int,
    )

    parser.add_argument(
        "--img_w",
        dest="IMG_WIDTH",
        help="Width of image (Default=256)",
        default=256, type=int,
    )

    parser.add_argument(
        "--img_h",
        dest="IMG_HEIGHT",
        help="Height of image (Default=256)",
        default=256, type=int,
    )

    parser.add_argument(
        "--num_c",
        dest="INPUT_CHANNELS",
        help="Number of input channels to use. Only odd no. of slices is supported (Default=7)",
        default=7, type=int,
    )
    # -------------------------------
    return parser.parse_args()


def setup_dirs():
    args = setup_options()
    dir_dict = {}
    dir_dict["INFILES"] = args.SUBJID + '*.png'
    dir_dict["TARGETPATH"] = os.path.join(args.INPUT, args.TARGET_MODALITY, args.DATASET, '')
    dir_dict["INPUTPATH"] = os.path.join(args.INPUT, args.INPUT_MODALITY, args.DATASET, '')
    dir_dict["TARGET_PADDING_PATH"] = os.path.join(args.DATAPATH, args.TARGET_MODALITY + '_paddings', args.DATASET, '')
    dir_dict["INPUT_PADDING_PATH"] = os.path.join(args.DATAPATH, args.INPUT_MODALITY + '_paddings', args.DATASET, '')

    dir_dict["RAW_OUTPATH"] = os.path.join(args.DATAPATH, 'raw_synth_' + args.TARGET_MODALITY, args.DATASET, '')
    if args.DIRECTION == 'real-fake':
        dir_dict["DIFF_OUTPATH"] = os.path.join(args.DATAPATH, 'diff_' + 'real_' + args.TARGET_MODALITY +
                                '-' + 'synth_' + args.TARGET_MODALITY, args.DATASET, '')
        dir_dict["DIFF_NII"] = os.path.join(args.NIIPATH, 'diff_' + 'real_' + args.TARGET_MODALITY +
                            '-' + 'synth_' + args.TARGET_MODALITY, args.DATASET, '')
    else:
        dir_dict["DIFF_OUTPATH"] = os.path.join(args.DATAPATH, 'diff_' + 'synth_' + args.TARGET_MODALITY +
                                '-' + 'real_' + args.TARGET_MODALITY, args.DATASET, '')
        dir_dict["DIFF_NII"] = os.path.join(args.NIIPATH, 'diff_' + 'synth_' + args.TARGET_MODALITY +
                            '-' + 'real_' + args.TARGET_MODALITY, args.DATASET, '')
    dir_dict["OUTPATH"] = os.path.join(args.DATAPATH, 'synth_' + args.TARGET_MODALITY, args.DATASET, '')

    dir_dict["TARGET_NII"] = os.path.join(args.INPUT[:-3] + "nii", args.TARGET_MODALITY, args.DATASET, '')
    dir_dict["INPUT_NII"] = os.path.join(args.INPUT[:-3] + "nii", args.INPUT_MODALITY, args.DATASET, '')
    dir_dict["SYNTH_NII"] = os.path.join(args.NIIPATH, 'synth_' + args.TARGET_MODALITY, args.DATASET, '')
    dir_dict["GAN_TARGET_NII"] = os.path.join(args.NIIPATH, 'gan_target_' + args.TARGET_MODALITY, args.DATASET, '')
    dir_dict["GAN_INPUT_NII"] = os.path.join(args.NIIPATH, 'gan_input_' + args.INPUT_MODALITY, args.DATASET, '')
    return args, dir_dict


def file_exists(image_file, slicenum, slice_of_interest):
    return tf.io.gfile.exists(
        tf.strings.regex_replace(image_file, slicenum, str(slice_of_interest.numpy()).zfill(3) + '.').numpy())


def load_padding(padding_path, subjid, first):
    if first:
        return tf.io.read_file(padding_path + subjid + '_first_mean_padding.png')
    else:
        return tf.io.read_file(padding_path + subjid + '_last_mean_padding.png')


def load_curr_slice(image_file, slicenum, curr_slice):
    return tf.io.read_file(tf.strings.regex_replace(image_file, slicenum, str(curr_slice.numpy()).zfill(3) + '.'))


def load(image_file, dir_dict, args):
    real_image_file = tf.strings.regex_replace(image_file, dir_dict["INPUTPATH"], dir_dict["TARGETPATH"])
    # create 3D image stack for multi-channel input with mean padding
    # input_imagelist,real_imagelist = tf.zeros((IMG_WIDTH, IMG_HEIGHT, INPUT_CHANNELS), tf.float32), tf.zeros((IMG_WIDTH, IMG_HEIGHT, INPUT_CHANNELS), tf.float32)
    input_imagelist = tf.zeros((args.IMG_WIDTH, args.IMG_HEIGHT, args.INPUT_CHANNELS), tf.float32)
    slicenum = "([0-9]{3})\."
    subjid = tf.strings.split(tf.strings.split(image_file, sep='/')[-1], sep='_')[0]
    mid_slice = int(tf.strings.substr(image_file, -7, 3))
    halfstack = lo_idx = hi_idx = args.INPUT_CHANNELS // 2
    min_slice = mid_slice - lo_idx
    max_slice = mid_slice + hi_idx
    num_curr_slice = 0

    while not tf.py_function(file_exists, [image_file, slicenum, min_slice], Tout=tf.bool):
        lo_idx -= 1
        min_slice += 1

    while not tf.py_function(file_exists, [image_file, slicenum, max_slice], Tout=tf.bool):
        hi_idx -= 1
        max_slice -= 1

    if halfstack - lo_idx != 0:

        # input_image = tf.io.read_file(INPUT_PADDING_PATH+subjid+'_first_mean_padding.png')
        input_image = tf.py_function(load_padding, [dir_dict["INPUT_PADDING_PATH"], subjid, True], Tout=tf.string)
        input_image = tf.image.decode_png(input_image, channels=1)
        input_image = tf.image.convert_image_dtype(input_image, tf.float32)

        #     real_image = tf.py_function(load_padding, [TARGET_PADDING_PATH,subjid,True],Tout=tf.string)
        #     real_image = tf.image.decode_png(real_image,channels=1)
        #     real_image = tf.image.convert_image_dtype(real_image, tf.float32)

        for i in range(halfstack - lo_idx):
            input_imagelist = tf.concat([input_imagelist[..., :num_curr_slice],
                                         input_image,
                                         tf.zeros((args.IMG_WIDTH, args.IMG_HEIGHT, args.INPUT_CHANNELS - num_curr_slice - 1),
                                                  tf.float32)], axis=2)
            #       real_imagelist=tf.concat([real_imagelist[...,:num_curr_slice],
            #                                 real_image, tf.zeros((IMG_WIDTH, IMG_HEIGHT, INPUT_CHANNELS-num_curr_slice-1),
            #                                                      tf.float32)], axis=2)
            num_curr_slice += 1

            input_imagelist.set_shape([args.IMG_WIDTH, args.IMG_HEIGHT, args.INPUT_CHANNELS])
    #       real_imagelist.set_shape([IMG_WIDTH, IMG_HEIGHT, INPUT_CHANNELS])

    for curr_slice in range(min_slice, max_slice + 1):
        # input_image = tf.io.read_file(tf.strings.regex_replace(image_file,slicenum,str(curr_slice).zfill(3)+'.'))
        input_image = tf.py_function(load_curr_slice,
                                     [image_file, slicenum, curr_slice],
                                     Tout=tf.string)
        input_image = tf.image.decode_png(input_image, channels=1)
        input_image = tf.image.convert_image_dtype(input_image, tf.float32)

        # real_image = tf.io.read_file(tf.strings.regex_replace(real_image_file,slicenum,str(curr_slice).zfill(3)+'.'))
        #     real_image = tf.py_function(load_curr_slice,
        #                                 [real_image_file,slicenum,curr_slice],
        #                                 Tout=tf.string)
        #     real_image = tf.image.decode_png(real_image,channels=1)
        #     real_image = tf.image.convert_image_dtype(real_image, tf.float32)

        input_imagelist = tf.concat([input_imagelist[..., :num_curr_slice],
                                     input_image, tf.zeros((args.IMG_WIDTH, args.IMG_HEIGHT, args.INPUT_CHANNELS - num_curr_slice - 1),
                                                           tf.float32)], axis=2)
        #     real_imagelist=tf.concat([real_imagelist[...,:num_curr_slice],
        #                               real_image, tf.zeros((IMG_WIDTH, IMG_HEIGHT, INPUT_CHANNELS-num_curr_slice-1),
        #                                                    tf.float32)], axis=2)
        num_curr_slice += 1

        input_imagelist.set_shape([args.IMG_WIDTH, args.IMG_HEIGHT, args.INPUT_CHANNELS])
    #     real_imagelist.set_shape([IMG_WIDTH, IMG_HEIGHT, INPUT_CHANNELS])

    if halfstack - hi_idx != 0:

        input_image = tf.py_function(load_padding, [dir_dict["INPUT_PADDING_PATH"], subjid, False], Tout=tf.string)
        input_image = tf.image.decode_png(input_image, channels=1)
        input_image = tf.image.convert_image_dtype(input_image, tf.float32)

        #     real_image = tf.py_function(load_padding, [TARGET_PADDING_PATH,subjid,False],Tout=tf.string)
        #     real_image = tf.image.decode_png(real_image,channels=1)
        #     real_image = tf.image.convert_image_dtype(real_image, tf.float32)

        for i in range(halfstack - hi_idx):
            input_imagelist = tf.concat([input_imagelist[..., :num_curr_slice],
                                         input_image,
                                         tf.zeros((args.IMG_WIDTH, args.IMG_HEIGHT, args.INPUT_CHANNELS - num_curr_slice - 1),
                                                  tf.float32)], axis=2)
            #       real_imagelist=tf.concat([real_imagelist[...,:num_curr_slice],
            #                                 real_image, tf.zeros((IMG_WIDTH, IMG_HEIGHT, INPUT_CHANNELS-num_curr_slice-1),
            #                                                      tf.float32)], axis=2)
            num_curr_slice += 1
            input_imagelist.set_shape([args.IMG_WIDTH, args.IMG_HEIGHT, args.INPUT_CHANNELS])
    #       real_imagelist.set_shape([IMG_WIDTH, IMG_HEIGHT, INPUT_CHANNELS])

    real_image = tf.io.read_file(real_image_file)
    real_image = tf.image.decode_png(real_image, channels=1)
    real_image = tf.image.convert_image_dtype(real_image, tf.float32)

    #   return input_imagelist, real_imagelist
    return input_imagelist, real_image


def resize(input_image, real_image, height, width):
    input_image = tf.image.resize(input_image, [height, width],
                                  method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
    real_image = tf.image.resize(real_image, [height, width],
                                 method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)

    return input_image, real_image


# normalizing the images to [-1, 1]

def normalize(input_image, real_image):
    input_image = (input_image / 127.5) - 1
    real_image = (real_image / 127.5) - 1

    return input_image, real_image


def load_image_test(image_file, args, dir_dict):
    input_image, real_image = load(image_file, args=args, dir_dict=dir_dict)
    input_image, real_image = resize(input_image, real_image,
                                     args.IMG_HEIGHT, args.IMG_WIDTH)
    input_image, real_image = normalize(input_image, real_image)

    return input_image, real_image


def intensity_rescale(synth_img, real_img):
    real_img = np.array(Image.open(real_img))
    synth_img = np.array(Image.open(synth_img))

    min_real = np.min(real_img)
    max_real = np.max(real_img)

    scale = (max_real - min_real) / (np.max(synth_img) - np.min(synth_img))
    offset = max_real - scale * np.max(synth_img)

    synth_img_scaled = scale * synth_img + offset

    return Image.fromarray(np.uint8(synth_img_scaled))


def histo_matching(synth_img, real_img):
    real_img = np.array(Image.open(real_img))
    synth_img = np.array(Image.open(synth_img))

    synth_img_scaled = match_histograms(synth_img, real_img)

    return Image.fromarray(np.uint8(synth_img_scaled))


def subtract_images(synth_img, real_img, direction):
    #    synth_img=Image.open(synth_img)
    real_img = Image.open(real_img)

    if direction == 'real-fake':
        out_img = ImageChops.subtract(real_img, synth_img)
    elif direction == 'fake-real':
        out_img = ImageChops.subtract(synth_img, real_img)

    return out_img


def to_nifti(subjid, realnii, inputdir, outname):
    real_nifti = nib.load(realnii)

    first_slice = True
    for png in sorted(glob.glob(os.path.join(inputdir, subjid + '_*.png'))):

        curr_slice = np.array(Image.open(png).convert('L'))
        # curr_slice=np.fliplr(np.flipud(curr_slice))

        if first_slice:
            vol_array = curr_slice
            first_slice = False
        else:
            vol_array = np.dstack((vol_array, curr_slice))

    final_nifti = nib.Nifti1Image(np.rot90(np.rot90(vol_array), axes=(2, 1)), real_nifti.affine,
                                  header=real_nifti.header)
    final_nifti.to_filename(outname)
    #print(f"Successfully saved {subjid} from {inputdir} and {realnii} as {outname}")


def main():
    args, var_dict = setup_dirs()
    print(var_dict["INPUTPATH"] + var_dict["INFILES"])
    test_dataset = tf.data.Dataset.list_files(var_dict["INPUTPATH"] + var_dict["INFILES"], shuffle=False)
    test_dataset = test_dataset.map(lambda x: load_image_test(x, args, var_dict))
    test_dataset = test_dataset.batch(args.BATCH_SIZE)

    generator = tf.keras.models.load_model(args.MODEL)

    os.makedirs(os.path.join(var_dict["RAW_OUTPATH"]), exist_ok=True)

    # Run the trained model on a few examples from the test dataset
    for (inp, tar), path, i in zip(test_dataset,
                               tf.data.Dataset.list_files(var_dict["INPUTPATH"] + var_dict["INFILES"], shuffle=False),
                               tqdm(range(len(glob.glob(os.path.join(var_dict["TARGETPATH"], var_dict["INFILES"])))),
                                    desc='Creating raw synthetic images')):
        prediction = generator(inp, training=True)
        #print(var_dict["INPUTPATH"], var_dict["RAW_OUTPATH"])
        outfile = tf.strings.regex_replace(path, var_dict["INPUTPATH"], var_dict["RAW_OUTPATH"])
        # print('\rwriting '+outfile.numpy().decode("utf-8").split('/')[-1], end='')
        tf.keras.preprocessing.image.save_img(outfile.numpy(), prediction[0], file_format='png')

    raw_synth_list = sorted(glob.glob(os.path.join(var_dict["RAW_OUTPATH"], var_dict["INFILES"])))
    real_list = sorted(glob.glob(os.path.join(var_dict["TARGETPATH"], var_dict["INFILES"])))

    os.makedirs(os.path.join(var_dict["OUTPATH"]), exist_ok=True)
    os.makedirs(os.path.join(var_dict["DIFF_OUTPATH"]), exist_ok=True)

    for synth_img, real_img, i in zip(raw_synth_list, real_list, tqdm(range(len(raw_synth_list)),
                                                                  desc='Creating final synthetic and diff images')):
        # MinMax Intensity scaling (not recommended):
        # synth_img_minmax_scaled= intensity_rescale(synth_img, real_img)
        # synth_img_minmax_scaled.save(os.path.join(OUTPATH,'test','minmax',synth_img.split('/')[-1]))

        # print('\rwriting '+synth_img.split('/')[-1], end='')
        synth_img_histo_scaled = histo_matching(synth_img, real_img)
        diff_img = subtract_images(synth_img_histo_scaled, real_img, args.DIRECTION)
        synth_img_histo_scaled.save(os.path.join(var_dict["OUTPATH"], synth_img.split('/')[-1]))
        diff_img.save(os.path.join(var_dict["DIFF_OUTPATH"], synth_img.split('/')[-1]))
    #print("#############################NIFTI", args.CREATE_NIFTI)
    if args.CREATE_NIFTI:

        os.makedirs(os.path.join(var_dict["SYNTH_NII"]), exist_ok=True)
        os.makedirs(os.path.join(var_dict["DIFF_NII"]), exist_ok=True)
        os.makedirs(os.path.join(var_dict["GAN_INPUT_NII"]), exist_ok=True)
        os.makedirs(os.path.join(var_dict["GAN_TARGET_NII"]), exist_ok=True)

        subjids = set([os.path.basename(img).split('/')[-1].split('_')[0]
                   for img in glob.glob(os.path.join(var_dict["INPUTPATH"], var_dict["INFILES"]))])

        for sbj in tqdm(subjids):
            to_nifti(sbj, var_dict["TARGET_NII"] + sbj + '_' + args.TARGET_MODALITY + '.nii.gz',
                     var_dict["OUTPATH"], var_dict["SYNTH_NII"] + sbj + '_synth_' + args.TARGET_MODALITY)

            to_nifti(sbj, var_dict["TARGET_NII"] + sbj + '_' + args.TARGET_MODALITY + '.nii.gz',
                     var_dict["DIFF_OUTPATH"], var_dict["DIFF_NII"] + sbj + '_diff')

            to_nifti(sbj, var_dict["INPUT_NII"] + sbj + '_' + args.INPUT_MODALITY + '.nii.gz',
                     var_dict["INPUTPATH"], var_dict["GAN_INPUT_NII"] + sbj + '_gan-input_' + args.INPUT_MODALITY)

            to_nifti(sbj, var_dict["TARGET_NII"] + sbj + '_' + args.TARGET_MODALITY + '.nii.gz',
                     var_dict["TARGETPATH"], var_dict["GAN_TARGET_NII"] + sbj + '_gan-target_' + args.TARGET_MODALITY)


if __name__ == "__main__":
    main()