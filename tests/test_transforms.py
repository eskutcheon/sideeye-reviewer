
import numpy as np
import matplotlib.pyplot as plt
# add sideeye_reviewer to the path since tests/ is on the same level as the main package
import os, sys
sys.path[0] = os.path.join(sys.path[0], "..")  # adjust this path as necessary to point to the main package directory
from sideeye_reviewer.utils.transforms import (
    SUPPORTED_ADAPTIVE_THRESHOLDING_METHODS,
    SUPPORTED_EDGE_DETECTION_METHODS,
    get_default_color_map,
    create_segmentation_mask_overlay,
    create_bbox_overlay_pil,
    create_binary_edge_mask,
    create_morphological_gradient_mask,
    _compute_adaptive_threshold,
    rgb_to_grayscale,
    create_ssim_heatmap,
    create_rgb_distributions
)




def _test_get_default_color_maps():
    # testing get_default_color_map
    for i in range(1, 5):
        color_map = get_default_color_map(3**i - 1)
        print(f"Color map for {3**i - 1} labels:\n\t{color_map}")
        color_map = get_default_color_map(3**i)
        print(f"Color map for {3**i} labels:\n\t{color_map}")
        color_map = get_default_color_map(3**i + 1)
        print(f"Color map for {3**i + 1} labels:\n\t{color_map}")


def _test_create_segmentation_mask_overlay(img, mask):
    color_map = {0: (0,0,0), 1: (0,255,0), 2: (0,0,255), 3: (255,0,0)}
    print("mask values:", np.unique(mask))
    overlay = create_segmentation_mask_overlay(img, mask, alpha=0.15, color_map=color_map)
    plt.imshow(overlay)
    plt.axis('off')
    plt.show()


def _test_create_bbox_overlay(img):
    H, W = img.shape[:2]
    # TODO: generate bounding boxes from segmentation masks to test this function later within the main viewer
        # use with either a quick script or torchvision.utils.masks_to_boxes
        # may want to add NMS while generating them - not sure if I'll want to allow that during the review process later
    bboxes = []
    # generating random indices to test the bbox overlay:
    for _ in range(3):
        x_bounds = np.random.randint(0, W, size=2)
        y_bounds = np.random.randint(0, H, size=2)
        bboxes.append([min(x_bounds), min(y_bounds), max(x_bounds), max(y_bounds)])
    # testing extreme corners and the direct center to gauge whether the local -> global conversion works
    #bboxes = [(0, 0, 100, 100), (1080, 760, 1280, 960), (590, 430, 690, 530)]
    bboxes = np.array(bboxes)
    #print("BBOXES: ", bboxes)
    fake_labels = [f"label{i}" for i in range(len(bboxes))]
    box_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # red, green, blue
    #overlay = create_bbox_overlay_mpl(img, bboxes, box_colors=(255, 0, 0), labels=fake_labels, line_width=2)
    overlay = create_bbox_overlay_pil(img, bboxes, box_colors=box_colors, labels=fake_labels, line_width=5)
    print("overlay type: ", type(overlay))
    print("overlay shape: ", overlay.shape)
    print("overlay dtype: ", overlay.dtype)
    print("overlay values: ", np.unique(overlay))
    plt.imshow(overlay)
    plt.axis('off')
    plt.show()


def _test_thresholding_methods(img):
    if img.ndim == 3 and img.shape[2] == 3:
        img = rgb_to_grayscale(img)  # convert to grayscale if RGB
        print("img_copy shape after conversion: ", img.shape)
    # test the general methods first:
    # fig, ax = filters.try_all_threshold(img, figsize=(10, 8), verbose=True)
    # plt.show()
    for method in SUPPORTED_ADAPTIVE_THRESHOLDING_METHODS:
        print(f"Testing adaptive thresholding method: {method}")
        threshold = _compute_adaptive_threshold(img, method=method)
        print(f"Threshold value for {method}: {threshold}")
        if method != 'local':
            binary_mask = img > threshold
        plt.imshow(binary_mask, cmap='gray')
        plt.title(f"Binary Mask - {method} Threshold")
        plt.axis('off')
        plt.show()


def _test_create_edge_mask(img):
    for method in SUPPORTED_EDGE_DETECTION_METHODS:
        for adaptive_method in SUPPORTED_ADAPTIVE_THRESHOLDING_METHODS:
            print(f"Testing edge detection method: {method} with adaptive thresholding: {adaptive_method}")
            edge_mask = create_binary_edge_mask(img, method=method,
                                                adaptive_threshold=True, adaptive_threshold_method=adaptive_method,
                                                sigma=1.0, low_threshold=0.1, high_threshold=0.3)
            plt.imshow(edge_mask, cmap='gray')
            plt.title(f"Edge Mask - {method} with {adaptive_method} Threshold")
            plt.axis('off')
            plt.show()
        # print(f"Testing edge detection method: {method}")
        # edge_mask = create_binary_edge_mask(img, method=method, sigma=1.0, low_threshold=0.1, high_threshold=0.3)
        # plt.imshow(edge_mask, cmap='gray')
        # plt.title(f"Edge Mask - {method}")
        # plt.axis('off')
        # plt.show()

def _test_create_morphological_gradient_mask(img):
    print("Testing morphological gradient mask")
    gradient_mask = create_morphological_gradient_mask(img, kernel_size=5)
    plt.imshow(gradient_mask, cmap='gray')
    plt.title("Morphological Gradient Mask")
    plt.axis('off')
    plt.show()


def _test_create_ssim_heatmap(img1, img2):
    print("Testing SSIM heatmap")
    ssim_heatmap = create_ssim_heatmap(img1, img2, window_size=11, gaussian_weights=True)
    plt.imshow(ssim_heatmap, cmap='coolwarm')
    plt.title("SSIM Heatmap")
    plt.axis('off')
    plt.show()



def _test_create_rgb_distributions(img):
    print("Testing RGB distributions")
    fig, axes = plt.subplots(figsize=(10, 6), ncols=2, nrows=1)
    #? NOTE (Important): axis of each ax object needs to be manually toggled off rather than turned on after a global toggle off
        # address how it's done in the layout manager later
    #plt.axis('off')  # turn off the main figure axes
    axes[0].axis('off')  # turn off the main figure axes
    axes[0].imshow(img)
    #axes[1].axis('on')  # turn off the main figure axes
    plot_fn = create_rgb_distributions(bins=256, alpha=0.5)
    # assume we only want to change the one axes so I'm not adding anything else to the figure
    axes[1] = plot_fn(img, ax=axes[1])
    plt.show()


if __name__ == "__main__":
    #_test_get_default_color_maps()
    test_img_path = r"E:\Woodscape Soiling\soiling_dataset\train\rgbImages\0499_MVL.png"
    test_img2_path = r"E:\Woodscape Soiling\soiling_dataset\train\rgbImages\0528_MVL.png"
    test_mask_path = r"E:\Woodscape Soiling\soiling_dataset\train\gtLabels\0499_MVL.png"
    img = plt.imread(test_img_path)
    mask = (255 * plt.imread(test_mask_path)).astype(np.uint8)
    #_test_create_segmentation_mask_overlay(img, mask)
    #_test_create_bbox_overlay(img)
    #_test_thresholding_methods(img)
    #_test_create_edge_mask(img)
    #_test_create_morphological_gradient_mask(img)
    # img2 = plt.imread(test_img2_path)
    # _test_create_ssim_heatmap(img, img2)
    _test_create_rgb_distributions(img)