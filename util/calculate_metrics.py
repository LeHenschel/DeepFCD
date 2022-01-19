# IMPORTS
import numpy as np
import nibabel as nib
import os
import glob
from subprocess import Popen, PIPE
import shlex



def call(command, **kwargs):
    """Run command with arguments. Wait for command to complete. Sends
    output to logging module. The arguments are the same as for the Popen
    constructor."""

    kwargs['stdout'] = PIPE
    kwargs['stderr'] = PIPE
    command_split = shlex.split(command)

    p = Popen(command_split, **kwargs)
    stdout, stderr = p.communicate()

    if stdout:
        for line in stdout.decode('utf-8').split("\n"):
            print(line)

    return p.returncode


def fsl_cluster(finput, findex, thresh=0.9, fosize=None, fothresh=None, **kwargs):
    """
    Run FSL Cluster command (https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Cluster)
    :param str finput: Input filename, image to be thresholded
    :param float thresh: Chosen threshold; default = 0.9
    :param str findex: Output file with each cluster assigned an integer from 1 to N
    :param str fosize: Output file with each cluster voxel assigned an integer equivalent to its cluster size
    :param str fothresh: Output file with clusters assigned the original values (only > threshold remain)
    :return:
    """
    # First try to run standard spherical project
    osize = "--osize={}".format(fosize) if fosize is not None else ""
    othresh = "--othresh={}".format(fothresh) if fothresh is not None else ""
    fsl = "cluster --in={} --thresh={} --oindex={} {} {}".format(finput, thresh, findex, osize, othresh)
    print("Running command: {}".format(fsl))
    code_1 = call(fsl, **kwargs)
    return code_1


def read_image(img):
    data = nib.load(img)
    return data.header, data.affine, np.asanyarray(data.dataobj)



def perf_measures(TP, TN, FP, FN):
    # Sensitivity, hit rate, recall, or true positive rate
    TPR = TP / (TP + FN)
    # Specificity or true negative rate
    TNR = TN / (TN + FP)
    # Precision or positive predictive value
    PPV = TP / (TP + FP)
    # Negative predictive value
    NPV = TN / (TN + FN)
    # Fall out or false positive rate
    FPR = FP / (FP + TN)
    # False negative rate
    FNR = FN / (TP + FN)
    # False discovery rate
    FDR = FP / (TP + FP)

    # Overall accuracy
    ACC = (TP + TN) / (TP + FP + FN + TN)

    return [TPR, TNR, PPV, NPV, FPR,  FNR, FDR,  ACC]


def get_true_positives(gt, pred):
    """
    Function to calculate number of true positives as indicated by overlap of
    x voxels
    :param np.array gt: input ground truth
    :param np.array pred: predicted values
    :return dict x: dictionary with performance measures
    """
    # Correction for FP belonging to same cluster --> if one of the voxels in it is TP, all
    # of them are counted as TP
    tp_bool = np.logical_and(pred > 0, gt == 1)
    overlap = np.sum(tp_bool)
    fp_bool = np.logical_and(pred > 0, gt == 0)
    extra = np.sum(fp_bool)
    true_clust = np.unique(pred[tp_bool])

    fp_bool[np.isin(pred, true_clust)] = False
    tp_bool[np.isin(pred, true_clust)] = True

    # True Positive (TP): we predict a label of 1 (positive), and the true label is 1.
    TP = np.sum(tp_bool)

    # False Positive (FP): we predict a label of 1 (positive), but the true label is 0.
    FP = np.sum(fp_bool)

    # True Negative (TN): we predict a label of 0 (negative), and the true label is 0.
    TN = np.sum(np.logical_and(pred == 0, gt == 0))

    # False Negative (FN): we predict a label of 0 (negative), but the true label is 1.
    FN = np.sum(np.logical_and(pred == 0, gt == 1))

    size_pred = np.sum(pred > 0)
    size_gt = np.sum(gt > 0)
    clustFP = np.unique(pred[fp_bool]).shape[0]

    list_m = [TP, FP, TN, FN, overlap, extra, clustFP, size_pred, size_gt]
    list_m.extend(perf_measures(TP, TN, FP, FN))
    return list_m


def write_to_file(metrics, subject, netw, ofile):
    s = "{}\t{}" + "\t{}" * len(metrics) +"\n"
    with open(ofile, "a") as f:
        f.write(s.format(subject, netw, *metrics))


def instantiate_csv(ofile):
    val_header = "Subject\tNetwork\tTP\tFP\tTN\tFN\tOrig_TP\tOrig_FP\tClust_FP\tSizePred\tSizeGT\tTPR\tTNR\tPPV\tNPV\tFPR\tFNR\tFDR\tACC\n"
    with open(ofile, "w") as f:
        f.write(val_header)


def get_population_stats(basedir, basedir2, gtdir, out, networks, pattern="*_ProbMapClass1.nii.gz"):
    split_l = len(basedir.split("2ch")[0])
    split_l2 = len(basedir2.split("2ch")[0])
    instantiate_csv(out)

    # get all subjects in base and instantiate csv-file
    for folds in ["-fold_0", "-fold_1", "-fold_2", "-fold_3"]:
        subjects = glob.glob(os.path.join(basedir + folds, "predictions", pattern))
        print(os.path.join(basedir + folds, "predictions", pattern))

        print("Processing {} subjects from directory {}".format(len(subjects), basedir))

        for sbj in subjects:
            sid = sbj.split("/")[-1].split("_")[0]
            # Load gt images
            try:
                gt_h, gt_a, gt_d = read_image(os.path.join(gtdir, sid + "_roi.nii.gz"))
                print("Processing subject {}".format(sid))
            except FileNotFoundError:
                print("Missing ROI ground truth for Subject {}. Continue with rest".format(sid))
                continue

            for nets in networks:
                # create fsl-cluster map:
                clust = os.path.join(basedir2[:split_l2] + nets + basedir2[split_l2 + len(nets):], sid + "cluster.nii.gz")
                inputf = os.path.join(basedir[:split_l] + nets + basedir[split_l + len(nets):] + folds, "predictions", sid + "_ProbMapClass1.nii.gz")
                fsl_cluster(inputf, clust)
                p_h, p_a, p_d = read_image(clust)

                # Get metrics for subject and save to file
                m_list = get_true_positives(gt_d, p_d)
                write_to_file(m_list, sid, nets, out)


if __name__ == "__main__":
    #base_i = "/input/deepmedic/examples/output/predictions/testSession_2ch_berlin_FCD/predictions"
    base_i = "/input/bonn_output/cross_validation_output/predictions/testSession_cross_val_2ch_FCD"
    base_o = "/output/data/deepmedic/predictions/testSession_2ch_bonn_FCD/predictions"
    gtd = "/input/data/bonn/FCD/iso_FLAIR/nii/deepmedic_input" #"/output/data/berlin/analyses/FCD/nii/deepmedic_input"
    of = "/output/data/bonn/FCD/iso_FLAIR/metric/bonn_FCD_crossVal_test.csv" #"/output/data/berlin/analyses/FCD/metric/berlin_FCD_test.csv"
    networks = ["2ch", "4ch", "7ch", "MAP"]

    if not os.path.exists(os.path.split(of)[0]):
        os.makedirs(os.path.split(of)[0])

    get_population_stats(base_i, base_o, gtd, of, networks)
    """
    base = "/output/data/deepmedic/predictions/testSession_2ch_berlin_FCD/"
    inf = base + "predictions/4522_pred_ProbMapClass1.nii.gz"
    clso = base + "cluster/4522_cluster_py.nii.gz"
    gt_f = "/output/data/berlin/analyses/FCD/nii/tmp/4522_roi.nii.gz"
    in_old = "/input/berlin_output/FCD/2ch/2ch_4522_pred_ProbMapClass1.nii.gz"
    clso_old = base + "cluster/4522_cluster_old.nii.gz"

    fsl_cluster(in_old, clso_old, thresh=0.9)
    fsl_cluster(inf, clso, thresh=0.9)

    gt_h, gt_a, gt_d = read_image(gt_f)
    p_h, p_a, p_d = read_image(clso)
    po_h, po_a, po_d = read_image(clso_old)

    m_new = get_true_positives(gt_d, p_d)
    m_a = perf_measures(m_new)
    m_o = get_true_positives(gt_d, po_d)
    print(m_new, m_o, m_a)
    """
# FCD detection counted as succes if 1 voxel overlap

# 1. List of "found" clusters (1 voxel overlap)
# 2. List of "other" clusters (False Positives)
# 3. Calculate Sensitivity and Specificity (a. over all subjects, b. per subject)
# 4. NEW: Calculate area overlap between a. found cluster and FCD, b. other cluster and FCD
# 5. NEW: Youden Index (balance between Sensitivity and Specificity)
# 6. Plotting functions