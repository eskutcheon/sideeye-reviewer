import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# project files
import utils.utils as util
import utils.review_utils as review_utils


CAM_ANGLE = 'MVR'
CAMERA_EXAMPLES = {
    'MVR': {'camera_1': '0268_MVR.png', 'camera_2': '2330_MVR.png'},
    'MVL': {'camera_1': '0012_MVL.png', 'camera_2': '0040_MVL.png'}
}

if __name__ == "__main__":
    train_folder = os.path.join('data', 'soiling_dataset', 'train', 'rgbImages')
    test_folder = os.path.join('data', 'soiling_dataset', 'test', 'rgbImages')
    #label_folder = os.path.join('data', 'soiling_dataset', 'train', 'rgbLabels')
    output_dir = os.path.join('data', 'camera_setups', 'test')
    sorter_labels = ['camera_1', 'camera_2', 'uncertain']
    # folders passed to the ImageSorter constructor must be in a list, even if singleton
    # NOTE: change all instances (except in hint_button_labels) of train_folder to test_folder if doing this for the test directory too
    camera_dict = util.populate_camera_dict(test_folder)
    output_dir = os.path.join(output_dir, CAM_ANGLE)
    image_files = camera_dict[CAM_ANGLE]
    '''txt_file_paths = {label: os.path.join(output_dir, f"{label}_labels.txt") for label in sorter_labels}
    image_files = camera_dict[CAM_ANGLE]
    json_output = os.path.join(output_dir, f"{CAM_ANGLE}_sorted.json")
    review_utils.aggregate_txt2json(txt_file_paths, json_output)'''
    hint_button_labels = {key: os.path.join(test_folder, name) for key, name in CAMERA_EXAMPLES[CAM_ANGLE].items()}
    review_utils.run_reviewer(test_folder, output_dir, sorter_labels, hint_button_labels, image_files)
    review_utils.post_review_cleanup(test_folder, output_dir, sorter_labels)
