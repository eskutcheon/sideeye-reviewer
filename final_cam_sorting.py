import os, sys, json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# project files
import utils.utils as util
import utils.review_utils as review_utils
import core.image_reviewer as IR
from core.show_sort_results import SortResultsViewer


# TODO: replace all hard-coding with staging functions that accept these kinds of CLI arguments later
#^##############################################################################################################################
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

LEGEND_LABELS = {'clean': 'black', 'transparent': 'green', 'semi-transparent': 'blue', 'opaque': 'red'}
SORTER_LABELS = ['camera_1', 'camera_2', 'uncertain']
SUPPORTED_CAM_TYPES = {'FV': ['cam1','cam2'], 'RV': ['cam1','cam2'], 'MVL': ['cam1'], 'MVR': ['cam1']}
#^##############################################################################################################################


def get_sorted_from_json(json_path):
    with open(json_path, 'r') as fptr:
        return dict(json.load(fptr))

def repeat_uncertain_labels(img_dirs, output_dir):
    # just using this to iterate over only "MVR" and "MVR" from the given folder - still assuming only 1 camera variant in FV and RV
    for cam in CAMERA_EXAMPLES.keys():
        json_dir = os.path.join(output_dir, cam)
        # ex json path: /data/camera_setups/soiled/train/MVR/MVR_sorted.json
        with open(os.path.join(json_dir, f"{cam}_sorted.json"), 'r') as fptr:
            camera_dict = dict(json.load(fptr))
        # handle case of no uncertain labels because the sorter doesn't yet:
        if len(camera_dict['uncertain']) == 0:
            print(f"No uncertain labels found - skipping file {os.path.join(json_dir, f'{cam}_sorted.json')}...")
            continue
        #hint_button_labels = {key: os.path.join(image_dir, name) for key, name in CAMERA_EXAMPLES[cam].items()}
        Sorter = IR.ImageSorter(img_dirs, json_dir, SORTER_LABELS, camera_dict['uncertain'], f"{cam}_sorted_uncertain.json")
        Reviewer = IR.ImageReviewer(Sorter, LEGEND_LABELS)
        Reviewer.begin_review()

def review_sorted_cams(output_path, img_dirs):
    # reading intended files to review from the json
    with open(output_path, 'r') as fptr:
        sorted_dict = dict(json.load(fptr))
    # get sorted list of file names in both directories
    image_files = sorted(sorted_dict['disagree'])
    sort_viewer = SortResultsViewer(image_files, img_dirs, "Disputed Labels")

if __name__ == "__main__":
    output_dir = SOILED_JSON_ROOT_DIR
    for mode, dir_dict in SOILED_PATH_DICT.items():
        # just want to deal with the test set to debug it for now:
        repeat_uncertain_labels([dir_dict['img'], dir_dict['mask']], os.path.join(output_dir, mode))
        # seems like the lines below were just for everything but the outlier cam_variants I saw
        '''for camera, angle_list in SUPPORTED_CAM_TYPES.items():
            json_dir = os.path.join(output_dir, folder, camera)
            if len(os.listdir(json_dir)) == 0:
                continue
            review_sorted_cams(os.path.join(json_dir, f"camera_sorted.json") [image_dir, label_dir])
        '''