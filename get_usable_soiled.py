
''' just a script to search through the files organized within the JSONs and choose which ones are
        the least soiled to use for the mask creation
    since going by counting the black pixels is going to result in several sequences with the same soiling,
        need to eliminate those that have a very high similarity score compared to recent images
    may need to sort these manually, in which case this file becomes another driver file for the ImageReviewer
    Still may want to throw the test images in one big pool along with these to ensure only the best files are used
        need to finish sorting the test files in this case.
    The usable scripts data structure will most likely be used by a new file to create the remaining camera's proper mappings
'''
from typing import List
import os, sys, json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import matplotlib.pyplot as plt
from tqdm import tqdm
import torch
import torchvision.io as IO
# project files
import core.image_reviewer as IR


CAMERAS = ['MVL', 'MVR']

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

CAMERA_EXAMPLES = {
    'MVR': {'camera_1': '0268_MVR.png', 'camera_2': '2330_MVR.png'},
    'MVL': {'camera_1': '0012_MVL.png', 'camera_2': '0040_MVL.png'}
}

SOILED_JSON_ROOT_DIR = os.path.join('data', 'camera_setups', 'soiled')

CLASS_LABELS = {'clean': 'black', 'transparent': 'green', 'semi-transparent': 'blue', 'opaque': 'red'}




def get_least_black_masks(file_names: List[str], file_dir: str, num_samples: int=None) -> List[str]:
    ''' get the most crowded images (fewest black pixels), contributing the best mask outlines of the camera
        Args:
            file_names: list of all file paths, as path/to/file/filename.png
            file_dir: the source directory for the files in file_names
            num_samples: number of file paths to return
        Returns:
            a list of num_samples file paths to return after sorting
    '''
    # TODO: move this to a utils file later after deciding what I plan to do with the repo structure in general
    num_samples = len(file_names) if num_samples is None else num_samples
    # preallocate dictionary with values key:0
    pixel_counts = dict(zip(file_names, [0 for _ in range(len(file_names))]))
    with tqdm(total=len(file_names)) as tracker:
        tracker.set_description("Getting the least black masks in dataset")
        for name in file_names:
            mask = IO.read_image(os.path.join(file_dir, name), IO.ImageReadMode.UNCHANGED)
            num_black_pixels = torch.sum(torch.all(torch.eq(mask, 0), dim=0).to(dtype=torch.int))
            pixel_counts[name] = int(num_black_pixels)
            tracker.update()
        # sort by pixel counts in ascending order - make list of tuples
    pixel_counts_sorted: list = sorted(pixel_counts.items(), key=lambda count: count[1])
    # grab only the {num_samples} filenames with the smallest black pixel count
    return [pixel_counts_sorted[i][0] for i in range(num_samples)]


def check_duplicates(camera_dict):
    for cam in CAMERAS:
        filename_set = set(camera_dict['train'][cam])
        set_intersection = filename_set.intersection(set(camera_dict['test'][cam]))
        print(set_intersection)
        print(f"len(set_intersection): {len(set_intersection)}")

def show_sorted_images(mask_paths: dict):
    # FIXME: need to call the nested dict correctly but don't need this function for now.
    for cam, file_paths in mask_paths.items():
        for path in file_paths:
            mask = plt.imread(path.replace('gtLabels', 'rgbLabels'), format='png')
            plt.imshow(mask, aspect='auto')
            plt.show()

def check_if_review_completed(file_list, json_path):
    if not os.path.exists(json_path):
        return False
    with open(json_path, 'r') as fptr:
        json_dict = json.load(fptr)
    # convert file lists in dict to sets, then successively take their unions
    json_union = set()
    for json_set in [set(sort_list) for sort_list in json_dict.values()]:
        json_union = json_union.union(json_set)
    set_difference = set(file_list).difference(json_union)
    # print(set_difference)
    return len(set_difference) == 0


if __name__ == "__main__":
    cams_aggregate = {mode: {cam: [] for cam in CAMERAS} for mode in ['train', 'test']}
    blackest_masks = {mode: {cam: [] for cam in CAMERAS} for mode in ['train', 'test']}
    for cam in CAMERAS:
        for folder, path_dict in SOILED_PATH_DICT.items():
            with open(os.path.join(SOILED_JSON_ROOT_DIR, folder, str(cam), f"usable_cam2_images.json"), 'r') as fptr:
                json_dict = json.load(fptr)
            json_out_dir = os.path.join(SOILED_JSON_ROOT_DIR, folder, str(cam))
            cams_aggregate[folder][cam] = json_dict['usable']
            #if not check_if_review_completed(cams_aggregate[folder][cam], os.path.join(json_out_dir, 'usable_cam2_images.json')):
            # rewrote the function so that it should be setting num_samples = len(input)
            blackest_masks[folder][cam] = get_least_black_masks(cams_aggregate[folder][cam], path_dict['mask'])[::-1]
            Sorter = IR.ImageSorter(image_folders = [path_dict['img'], path_dict['mask']],
                                    out_dir = json_out_dir,
                                    labels = ['usable', 'unusable', 'maybe'],
                                    file_list = blackest_masks[folder][cam],
                                    json_name = 'usable_cam2_images.json')
            Reviewer = IR.ImageReviewer(Sorter, CLASS_LABELS)
            Reviewer.begin_review(True)


    ''' need to go ahead and feed in all four of these file lists into a reviewer to pick the most usable ones
        - It'll probably be easiest to aggregate them after this.
            - This also means that blackest_masks should become a nested dict that is recombined by key 'cam' later
        Check the counts in each file list - shoot for keeping at least 25-50 per file list.
        Take only 1 or 2 per sequence, which should still be in order by the blackness sorting
        Should have some notes in Obsidian to refer to.

        After sorting, write a function to toss images that have masks too similar to those already observed in the list.
            - Do this only if necessary - I assume it will be just because of the small variation in masks (esp. the usable ones)
            - try covariance measures with every mask observed?
    '''