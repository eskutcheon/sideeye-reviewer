import os, sys, json
# uncomment this later if I add these scripts to subfolders again
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import torch
import torchvision.io as IO
import torchvision.transforms as T
import numpy as np
import matplotlib.pyplot as plt
import skimage
from random import random
# project files
import utils.utils as util
import utils.img_utils as img_util


BIN_MASK_FILENAMES = {
    'FV': {'cam1': "combined_welfords_mean_mask.png"},
    'RV': {'cam1': "combined_welford_methods_mask.png"},
    'MVL': {'cam1': "final_mask_welfords_mean.png", 'cam2': "new_threshold_mask_touchup.png"},
    'MVR': {'cam1': "mask_welfords_mean_N=200.png", 'cam2': "new_threshold_mask_touchup.png"}
}

# TODO: write quick script to fix these
# I messed up in the naming when I sorted these and don't want to go fix it
CAM_ANGLE_ALIASES = {
    'MVL': {'cam1': 'camera_1', 'cam2': 'camera_2'},
    'MVR': {'cam1': 'camera_1', 'cam2': 'camera_2'}
}

MAP_OUTPUT_DIR = os.path.join("..", "soiling_dataset_new", "updated_maps")
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
SOILED_JSON_ROOT_DIR = os.path.join('data', 'camera_setups', 'soiled')
SOILED_JSON_TRAIN_DIR = os.path.join(SOILED_JSON_ROOT_DIR, 'train')

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

# argument dict specifying how SegMapper sets the map func and how to process afterwards
FUNC_DICT = {
    'img': {'method': 'welfords_mean', 'params': {}, 'labels_to_img': False},
    'mask': {'method': 'welfords_mean', 'params': {}, 'labels_to_img': False}
}



def get_black_pixel_mask(mask: torch.tensor, histogram: torch.tensor=None) -> torch.tensor:
    ''' get a bool mask of whether each channel is 0, then check if all channels == True
        Args:
            mask: tensor of RGB pixels in shape of either (N,3,H,W) or (3,H,W) - preferably as int in 0-255 for minimal error
                NOTE: also works with categorical mask where 0 maps [0,0,0] in shape (N,1,H,W)
        Returns:
            flat boolean mask of black pixels in shape (1,H,W)
    '''
    is_batch = util.is_batch_tensor(mask)
    # Check channels first, then batches (if applicable)
    mask = torch.all(torch.eq(mask, 0), dim=is_batch) # becomes either (H,W) or (N,H,W)
    if histogram is not None:
        # FIXME: fix the shape difference
        histogram += torch.sum(torch.logical_not(mask).to(dtype=torch.int), dim=0, keepdim=(not is_batch)).unsqueeze(0)
    if is_batch:
        mask = torch.all(mask, dim=0)
    #print(f'mask shape: {mask.shape}')
    if histogram is not None:
        return mask.unsqueeze(dim=0), histogram
    else:
        return mask.unsqueeze(dim=0)


def get_boundary_rings(bin_mask: np.ndarray, orientation: str, ring_thickness:int = 10):
    if orientation not in ['outer', 'inner']:
        raise ValueError(f"'orientation' argument must be one of 'outer', 'inner'. Received {orientation}")
    # TODO: really should edit this to just set boundary_rings equal to this then make mask_boundaries temp variable in the loop
        # just don't feel like testing it right now
    mask_boundaries = skimage.segmentation.find_boundaries(bin_mask, mode=orientation, background=1)
    #original_ring = np.copy(mask_boundaries)
    outermost_edge_mask = np.copy(~bin_mask)
    boundary_rings = np.copy(mask_boundaries)
    for _ in range(ring_thickness):
        outermost_edge_mask[mask_boundaries] = ~outermost_edge_mask[mask_boundaries]
        mask_boundaries = skimage.segmentation.find_boundaries(outermost_edge_mask, mode=orientation, background=1, connectivity=2)
        boundary_rings = np.logical_or(boundary_rings, mask_boundaries)
    #util.plot_images(mask_boundaries, boundary_rings, outermost_edge_mask, title="mask boundaries")
    return boundary_rings

def get_overlay(img_map, mask):
    # black will show as red and white will show as green for contrast's sake
    colors = [(255,0,0), (0,255,0)]
    onehot_mask = util.labels_to_onehot(mask.to(dtype=torch.long), 2)
    overlay_mask = util.get_mask_overlay(img_map, onehot_mask, colors, 2)
    return overlay_mask

def show_overlay(img_map, overlay, title=''):
    #util.plot_images(overlay, title=title)
    util.plot_images(img_map, overlay, title=title)

def get_num_from_filename(name, str_to_strip):
    return float(name.lstrip(str_to_strip).rstrip(".png"))

def get_largest_sample(filenames, str_to_strip):
    samples = [get_num_from_filename(name, str_to_strip) for name in filenames]
    return filenames[np.argmax(samples)]

def test_boundary_ring_addition(img_map, mask, title=''):
    overlay_initial = get_overlay(img_map, mask)
    bin_mask_np = util.tensor_to_ndarray(mask.squeeze(0))
    thickness = 5
    if 'MVR' in title or 'MVL' in title:
        thickness = 7
    boundary_ring = get_boundary_rings(bin_mask_np, 'outer', ring_thickness=thickness)
    #util.get_all_debug(boundary_ring)
    bin_mask_new = torch.clone(mask)
    bin_mask_new[:, torch.from_numpy(boundary_ring)] = True
    #util.get_all_debug(bin_mask_new)
    #util.plot_images(torch.logical_xor(mask, bin_mask_new), title="old mask vs new mask difference")
    overlay_updated = get_overlay(img_map, bin_mask_new)
    util.plot_images(overlay_initial, title=f"{title} with initial overlay")
    util.plot_images(overlay_updated, title=f"{title} with updated overlay")

def add_boundary_ring(mask, thickness=4):
    bin_mask_np = util.tensor_to_ndarray(mask.squeeze(0))
    boundary_ring = get_boundary_rings(bin_mask_np, 'outer', ring_thickness=thickness)
    bin_mask_new = torch.clone(mask)
    bin_mask_new[:, torch.from_numpy(boundary_ring)] = True
    return bin_mask_new
    #overlay_updated = get_overlay(img_map, bin_mask_new)
    #util.plot_images(overlay_updated, title=f"test with updated overlay")

if __name__ == "__main__":
    # NOTE: this was just a directory ending with ~/train/ before - now it's a dict - adjust as needed
    for cam, angle_dict in BIN_MASK_FILENAMES.items():
        for angle, mask_name in angle_dict.items():
            '''if angle != "cam2":
                continue'''
            map_parent_dir = os.path.join(MAP_OUTPUT_DIR, cam, angle)
            # path for binary masks used to create the new segmentation datasets
            bin_mask_path = os.path.join(map_parent_dir, 'threshold_masks', BIN_MASK_FILENAMES[cam][angle])
            bin_mask = IO.read_image(bin_mask_path, IO.ImageReadMode.RGB)
            # actual black and white binary mask in shape (1,H,W)
            bin_mask = ~get_black_pixel_mask(bin_mask)
            map_names = util.get_matching_filenames(map_parent_dir, f"img_{FUNC_DICT['img']['method']}_N=")
            map_sample_name = get_largest_sample(map_names, f"img_{FUNC_DICT['img']['method']}_N=")
            img_map = IO.read_image(os.path.join(map_parent_dir, map_sample_name), IO.ImageReadMode.RGB)
            '''if cam == "RV" or cam == "MVL" and angle == "cam1":
                bin_mask = add_boundary_ring(bin_mask, thickness=4)
            if cam == "MVR" and angle == "cam1":
                bin_mask = add_boundary_ring(bin_mask, thickness=8)'''
            # generate new labels since I edited stuff manually in the process of viewing these
            base_mask_name = os.path.splitext(BIN_MASK_FILENAMES[cam][angle])[0]
            #IO.write_png(img_util.labels_to_image(bin_mask, [(0,0,0), (255,255,255)], 2), bin_mask_path, 0)
            IO.write_png(bin_mask.to(dtype=torch.uint8), os.path.join(map_parent_dir, 'threshold_masks', f"{base_mask_name}_labels.png"), 0)
            overlay_initial = get_overlay(img_map, bin_mask)
            show_overlay(img_map, overlay_initial, title=map_sample_name)
            #test_boundary_ring_addition(img_map, bin_mask, title=f"{map_sample_name} for {cam}-{angle}")
            '''file_list = []
            # only cam1 is present in the FV and RV images, while MVL and MVR has 2 cam angles per directory
            if cam in ['FV', 'RV']:
                file_list = os.listdir(SOILED_PATH_DICT['train']['label'])
            else:
                angle_key = CAM_ANGLE_ALIASES[cam][angle]
                with open(os.path.join(SOILED_JSON_TRAIN_DIR, cam, f"{cam}_sorted.json"), 'r') as fptr:
                    file_list = dict(json.load(fptr))[angle_key]'''
            '''for filename in sorted(file_list, key=lambda x: random())[:TEST_SIZE]:
                old_labels = IO.read_image(os.path.join(SOILED_PATH_DICT['train']['label'], filename), IO.ImageReadMode.UNCHANGED)
                util.get_all_debug(old_labels, 'old_labels')
                new_labels = get_new_label_tensor(old_labels, bin_mask)
                IO.write_png(new_labels, os.path.join(output_dirs['label'], filename), 0)
                new_mask = get_new_mask_tensor(new_labels)
                IO.write_png(new_mask, os.path.join(output_dirs['mask'], filename), 0)'''