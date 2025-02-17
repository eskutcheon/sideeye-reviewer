import os, sys, json
#sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# project files
import core.multilabel_image_reviewer as MIR
import utils.utils as util
from typing import List, Dict, Tuple, Union

# wrote like global constants since this is pretty much all the driver file is meant for.
""" From the ARC proposal draft:
    "The particular contentions that we have identified so far include
        inaccurate_edges - Disagreement on the borders of a region
            e.g., a region labeled opaque covers pixels that could be in a neighboring transparent region
        inaccurate_labels - Disagreement on the label of one or more entire regions
            e.g., the road ahead can be seen through a small grease smudge labeled opaque
        inaccurate_regions - Disagreement based on the coarseness of the mask with an unacceptable level of precision
            e.g., a complex soiled region and the remainder of the mask are split evenly with a single line"
        missed_border - probably won't be handled here, but this is for the cases where the annotator missed the very edge,
            resulting in a mislabeled strip on the border
        laziness - really the exact same as inaccurate_regions so it may be removed, but thought it might be helpful to mark the extremely problematic ones
        other - any problems observed that I haven't accounted for
        no_contest - resort the images into the "agreed" category with no contentions - necessary after masking out borders in the new dataset
"""
SORTER_LABELS = ["inaccurate_edges", "inaccurate_labels", "inaccurate_regions", "missed_border", "laziness", "other", "no_contest"]

CLASS_LABELS = {'clean': 'black', 'transparent': 'green', 'semi-transparent': 'blue', 'opaque': 'red'}

SOILED_TRAIN_DIR = os.path.join('data', 'soiling_dataset', 'train')
SOILED_TEST_DIR = os.path.join('data', 'soiling_dataset', 'test')
SOILED_PATH_DICT = {
    'train': {
        'img': os.path.join(SOILED_TRAIN_DIR, 'rgbImages'),
        # NOTE: don't actually need to save any new masks - so I'm passing the gtLabels for faster computation of inpainting
        'label': os.path.join(SOILED_TRAIN_DIR, 'gtLabels'),
        'mask': os.path.join(SOILED_TRAIN_DIR, 'rgbLabels'),
        'overlay': os.path.join(SOILED_TRAIN_DIR, 'rgbOverlays')},
    'test': {
        'img': os.path.join(SOILED_TEST_DIR, 'rgbImages'),
        'label': os.path.join(SOILED_TEST_DIR, 'gtLabels'),
        'mask': os.path.join(SOILED_TEST_DIR, 'rgbLabels'),
        'overlay': os.path.join(SOILED_TEST_DIR, 'rgbOverlays')}}
NEW_DATASET_TRAIN_PATH = os.path.join("..", "soiling_dataset_new", "train")
NEW_DATASET_TEST_PATH = os.path.join("..", "soiling_dataset_new", "test")
NEW_DATASET_PATH_DICT = {
    'train': {
        'img': os.path.join(NEW_DATASET_TRAIN_PATH, "rgbImages"),
        'label': os.path.join(NEW_DATASET_TRAIN_PATH, "gtLabels"),
        'mask': os.path.join(NEW_DATASET_TRAIN_PATH, "rgbLabels"),
        'overlay': os.path.join(NEW_DATASET_TRAIN_PATH, "rgbOverlays")},
    'test': {
        'img': os.path.join(NEW_DATASET_TEST_PATH, "rgbImages"),
        'label': os.path.join(NEW_DATASET_TEST_PATH, "gtLabels"),
        'mask': os.path.join(NEW_DATASET_TEST_PATH, "rgbLabels"),
        'overlay': os.path.join(NEW_DATASET_TEST_PATH, "rgbOverlays")}}




# just made a small function to make it easier to repeat for the test set
def begin_review(image_folders, output_dir, file_list, json_name):
    ''' IR.ImageSorter optional kwargs:
        file_list (List[str]) - to specify the names of files to review, if not just the whole directory
        json_name (str) - to specify the name of the json file to save the results to.'''
    disputed_sorter = MIR.ImageSorter(image_folders, output_dir, SORTER_LABELS, file_list=file_list, json_name=json_name)
    # the second positional argument criteria_labels should be optional - but this adds a color legend (or image hint)
    Reviewer = MIR.ImageReviewer(disputed_sorter, CLASS_LABELS)
    # optional argument checkpoint (bool) - whether to resume from previous session or not - default True
    Reviewer.begin_review()


def prune_similar_masks(source_files: list, cluster_json_path: str):
    """ uses JSON metadata to find the sequences of images whose masks were all found to be roughly the same """
    # TODO: add only necessary files to new_file_list; after sorting, take set difference between this and the original file list,
        # find cluster of those in the diff and use whichever file is present in the cluster and both lists to just copy the contention labels
    new_file_list = [] # all files
    dropped_files = {}
    with open(cluster_json_path, 'r') as fptr:
        cluster_dict = dict(json.load(fptr))
    # iterate over all image sequences specified by the JSON in cluster_json_path
    for label, file_dict in cluster_dict.items():
        # get a list of files that are in both source_files and the list of filenames for each cluster
        common_filenames = list(set(source_files).intersection(set(file_dict["filenames"])))
        # if there are no files in source_files (given as the disagreed filenames in main) in that cluster, skip to the next cluster
        if len(common_filenames) == 0:
            continue
        # if the intra-cluster difference in masks is 0, choose a representative for the cluster and drop the rest
        if min(file_dict["mean_diff"]) == 0:
            # add the first file as representative of the cluster - copy sorting results for it to the rest of those disagreed on within the cluster
                # NOTE: may need to rethink this later, since it would result in inconsistent masks within the cluster after correction if some weren't disagreed on
            new_file_list.append(common_filenames[0])
            # add the rest of the common files to dropped_files to track for later
            if len(common_filenames) > 1:
                dropped_files[label] = common_filenames[1:]
            continue
        # add files within the cluster (whose 'mean_diff' != 0) that are also in the original disagreed file list
        new_file_list.extend(common_filenames)
    return new_file_list, dropped_files


def copy_sorting_through_cluster(dropped_files: dict, cluster_json_path: str, sort_results_path: str):
    """ iterate over all image sequences with dropped files and copy the sorting results of its representative throughout the sequence """
    # read json of image sequence metadata as dict
    with open(cluster_json_path, 'r') as fptr:
        cluster_dict = dict(json.load(fptr))
    # read the sort results of the multilabel review from a json to a dict
    with open(sort_results_path, 'r') as fptr:
        sorted_contentions = dict(json.load(fptr))
    # iterate over all image sequences with dropped files
    for label, files in dropped_files.items():
        # finds the image sequence representative by taking set difference of whole cluster to those dropped from the cluster
        members_not_dropped = list(set(cluster_dict[label]).difference(set(files)))
        # NOTE: not sure why I made this a list beside maybe having multiple representatives later
        for possible_rep in members_not_dropped:
            # for all bins that the representative could have been sorted into
            for bin in sorted_contentions.values():
                if possible_rep in bin:
                    # add all dropped cluster members to the bin if their representative is in the bin
                    bin.extend(files)
    # rewrite the sorting results to the results json
    with open(sort_results_path, 'w') as fptr:
        json.dump(sorted_contentions, fptr, indent=4)


def check_json_integrity(source_file_list, json_path):
    """ create a flat set from all files in the json pointed to by json_path and ensure they're all in source_files_list"""
    with open(json_path, 'r') as fptr:
        full_sorted_dict = dict(json.load(fptr))
    # create flat list from the json sub-dictionaries that may have duplicates
    joined_list = []
    for file_list in full_sorted_dict.values():
        joined_list.extend(file_list)
    # ensure there are no files in source_files_list that aren't also in joined_list
    set_diff = set(source_file_list).difference(set(joined_list))
    assert len(set_diff) == 0, f"The following files are missing from the JSON:\n {set_diff}"


def redo_partial_sort_results(contention_json_path: str, cluster_json_path: str, path_dict: Dict[str, str]):
    """ redo the sort for all images that were placed in both inaccurate_regions and inaccurate_labels
        While not mutually exclusive, the first reviewer misunderstood the meaning of inaccurate_regions and conflated the two.
    """
    # TODO: check for correctness first - that all files that were supposed to be reviewed have been
    # TODO: need to remember to make a copy of the json before trying to run this.
    # save the redo in a new json to leave the original untouched
    new_json_name = f"{os.path.basename(contention_json_path).split('_')[0]}_contention_redo.json"
    new_json_dir = os.path.dirname(contention_json_path)
    with open(contention_json_path, 'r') as fptr:
        contention_dict = dict(json.load(fptr))
        new_contention_dict = contention_dict.copy()
    # only reviewing these since Cam didn't know the difference between them and may have had too much overlap
    files_to_review = sorted(set(contention_dict["inaccurate_regions"]).intersection(set(contention_dict["inaccurate_labels"])))
    # remove all files to be reviewed from the new json that the review saves into, effectively checkpointing all but those under review
    new_contention_dict["inaccurate_regions"] = sorted(set(new_contention_dict["inaccurate_regions"]).difference(files_to_review))
    new_contention_dict["inaccurate_labels"] = sorted(set(new_contention_dict["inaccurate_labels"]).difference(files_to_review))
    # get disagreed-on files while dropping image sets from image sequences where all masks are the same
    pruned_files_to_review, dropped_files = prune_similar_masks(files_to_review, cluster_json_path)
    # perform multilabel review (using checkboxes) of disagreed-on images to further sort by type of disagreement
    begin_review([path_dict['img'], path_dict['overlay']], new_json_dir, sorted(pruned_files_to_review), new_json_name)
    # copy the sorting results throughout the dropped files of a cluster based on the results for its representative
    copy_sorting_through_cluster(dropped_files, cluster_json_path, os.path.join(new_json_dir, new_json_name))


def check_for_missed_files(contention_json_path, file_superset):
    """ Given the way I wrote the reviewer to not allow moving to the next value without choosing a bin,
        this shouldn't be an issue unless my code was at fault. I want to check just in case.
    """
    with open(contention_json_path, 'r') as fptr:
        contention_dict = dict(json.load(fptr))
    sorted_set = set()
    for bin_list in contention_dict.values():
        sorted_set.update(bin_list)
    set_diff = set(file_superset).difference(sorted_set)
    if len(set_diff) != 0:
        print(f"WARNING: found {len(set_diff)} files in the original set of disagreed files that aren't in the final sort results.\n Files found:\n")
        print(set_diff)


if __name__ == "__main__":
    # /{this parent dir}/disputed_labels - maybe change to /data/sorting/disputed_labels later
    dataset_dict = NEW_DATASET_PATH_DICT
    data_root_dir = os.path.join(dataset_dict['train']['img'], '..', '..')
    output_dir = os.path.join(data_root_dir, 'disputed_labels')
    cluster_json_path = os.path.join(data_root_dir, "cluster_membership.json")
    # test if the output directory exists and recursively create it if not
    os.makedirs(output_dir, exist_ok=True)
    json_path_dict = {
        "train": os.path.join('..', 'other_sorting', 'joined_train_contentions.json'),
        "test": os.path.join('..', 'other_sorting', "test_results.json")
    }
    # assuming that Dr. Carruth still wants to use the new dataset - use SOILED_PATH_DICT.items() otherwise
    # iterate over the dict laid out like {'train': {'img', 'mask', ...}, 'test': {'img', 'mask', ...}}
    for dir_type, path_dict in dataset_dict.items():
        curr_json_name = f"{dir_type}_sorted_contention.json"
        curr_json_path = os.path.join(output_dir, curr_json_name)
        # ensure that all files in the json of all files under contention are in in path_dict['img'] to ensure nothing is missed
        check_json_integrity(os.listdir(path_dict['img']), json_path_dict[dir_type])
        with open(json_path_dict[dir_type], 'r') as fptr:
            full_sorted_dict = dict(json.load(fptr))
        # get disagreed-on files while dropping image sets from image sequences where all masks are the same
        pruned_contentions, dropped_files = prune_similar_masks(sorted(full_sorted_dict['disagree']), cluster_json_path)
        # folders passed to the ImageSorter constructor must be in a list, even if singleton
        # perform multilabel review (using checkboxes) of disagreed-on images to further sort by type of disagreement
        begin_review([path_dict['img'], path_dict['overlay']], output_dir, sorted(pruned_contentions), curr_json_name)
        # copy the sorting results throughout the dropped files of a cluster based on the results for its representative
        copy_sorting_through_cluster(dropped_files, cluster_json_path, curr_json_path)
        check_for_missed_files(curr_json_path, full_sorted_dict['disagree'])
        # get user confirmation to continue the review into the test set as well - else end program
        confirmation = util.get_user_confirmation("Continue with next image set? [Y/n] ")
        if not confirmation:
            break