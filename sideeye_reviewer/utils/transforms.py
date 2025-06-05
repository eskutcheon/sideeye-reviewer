
from typing import Dict, List, Union, Tuple, Sequence, Any
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from skimage.transform import rescale as sk_rescale, resize as sk_resize
from skimage.morphology import dilation as sk_dilation, erosion as sk_erosion, disk as sk_disk
from skimage.metrics import structural_similarity as sk_ssim
import skimage.filters as skfi
import skimage.feature as skfe



# may move some of these more universal image processing functions to utils.py

def _ensure_normalized_img(img: np.ndarray) -> np.ndarray:
    """ Ensures the image is in the range [0, 1] and of type float32
        :param img: image to normalize
        :return: normalized image
    """
    if img.dtype != np.float32:
        if img.max() > 1.0:  # handle 0-255 or 0-1 range
            img = img.astype(np.float32) / 255.0
        else:
            img = img.astype(np.float32)
    return img

def _ensure_full_color_img(img: np.ndarray) -> np.ndarray:
    """ ensures the image has 3 channels (RGB), handling grayscale of shape (H, W) or (H, W, 1)
        :param img: image to ensure full color
        :return: image with 3 channels
    """
    if img.ndim == 2:
        img = np.stack([img] * 3, axis=-1)
    elif img.ndim == 3 and img.shape[2] == 1:
        img = np.concatenate([img] * 3, axis=-1)
    return img


def _rgb_mask_to_labels(mask: np.ndarray) -> Tuple[np.ndarray, Dict[int, Tuple[int, int, int]]]:
    """ converts a mask with RGB labels to a flat label mask
        :param mask: mask with RGB labels (shape: H, W, 3)
        :return: (
            one-hot encoded mask (shape: H, W) with class IDs as elements,
            color map dictionary mapping class IDs to RGB colors
        )
    """
    assert mask.ndim == 3 and mask.shape[2] == 3, "Mask must be of shape (H, W, 3)"
    unique_colors = np.unique(mask.reshape(-1, 3), axis=0)
    label_mask = np.zeros((mask.shape[0], mask.shape[1]), dtype=np.float32)
    new_color_map = {}
    try:
        for i, color in enumerate(unique_colors):
            new_color_map[i] = tuple(color)  # store the color as a tuple
            #label_mask[..., i] = np.all(mask == color, axis=-1).astype(np.float32)
            label_mask[np.all(mask == color, axis=-1)] = i  # assign class ID to the label mask
    except Exception as e:
        print("[TRANSFORMS]: Error while converting RGB mask to one-hot encoding:", e)
    return label_mask, new_color_map


def _linear_alpha_blend(img1: np.ndarray, img2: np.ndarray, alpha: float) -> np.ndarray:
    """ Performs linear alpha blending of two images
        :param img1: first image (background)
        :param img2: second image (foreground)
        :param alpha: blending factor (0.0 - 1.0)
        :return: blended image
    """
    assert img1.shape == img2.shape, "Images must have the same shape for blending"
    assert 0 <= alpha <= 1, "Alpha must be in the range [0, 1]"
    return (alpha * img2 + (1 - alpha) * img1).astype(np.float32)  # ensure float32 output


def get_default_color_map(
    num_labels: int,
    use_black = True,
    use_white=False,
    # lightness_bounds=(20, 40),
    # chroma_bounds=(40, 50)
) -> Dict[int, Tuple[int, int, int]]:
    """ returns a default (maximally distinct) color map for mask labels given the number of labels
        :return: A dictionary mapping class IDs to RGB colors.
    """
    #rgb_value_bank = [0, 255, 128, 64, 192] # support up to 3**5 - 1 = 242 colors
    if num_labels < 2:
        raise ValueError("num_labels must be at least 2")
    # elif num_labels > 3**len(rgb_value_bank) - 1:
    #     raise ValueError(f"num_labels must be less than {3**len(rgb_value_bank) - 1}")
    elif num_labels == 2:
        # return black and white for binary masks
        return {0: (0, 0, 0), 1: (1, 1, 1)} # or for black and gray: {0: (0, 0, 0), 1: (0.5, 0.5, 0.5)}
    import glasbey
    palette = glasbey.create_palette(palette_size=num_labels, as_hex=False) #, optimize_palette=False)
    # TODO: might remove integer conversion if I'm sticking solely with numpy since everything defaults to float in range [0, 1]
    palette = [[int(255*k) for k in rgb] for rgb in palette]
    return {i: tuple(palette[i]) for i in range(num_labels)}


def create_segmentation_mask_overlay(
    img: np.ndarray,
    mask: np.ndarray,
    alpha: float = 0.125,
    color_map: Dict[int, Tuple[int, int, int]] = None,
) -> np.ndarray:
    """ Creates a mask overlay for an image with alpha blending
        :param img: image to overlay the mask on
        :param mask: mask (encoded as integer labels) to overlay
        :param alpha: transparency of the overlay
        :param color_map: dictionary mapping class IDs to RGB colors
        :return: the segmentation mask-overlayed image
    """
    assert isinstance(img, np.ndarray), "img must be a numpy array"
    assert isinstance(mask, np.ndarray), "mask must be a numpy array"
    is_rgb_mask = (mask.ndim == 3 and mask.shape[-1] == 3)  # check if mask is RGB
    img_copy = _ensure_normalized_img(img.copy())  # ensure img is float32 and in range [0, 1]
    if img.shape[:2] != mask.shape[:2]:
        # resize the mask to match the image size if needed
        mask = sk_resize(mask, img.shape[:2], order=0, anti_aliasing=False, mode='reflect', preserve_range=True)
    # if mask.ndim == 3 and mask.shape[2] == 3:
    #     # if mask is RGB, convert it to one-hot encoded mask and get the color map
    #     mask, color_map = _rgb_mask_to_labels(mask)
    if color_map is None and not is_rgb_mask:
        num_classes = int(np.max(mask) + 1)
        print(f"WARNING: No color map provided; Using default color map with number of labels = {num_classes}")
        #! FIXME: need to change this to use the same color map for all masks, so it needs to be passed in
        color_map = get_default_color_map(num_classes)
    if not is_rgb_mask:
        if mask.ndim == 3 and mask.shape[-1] == 1:
            mask = mask.squeeze(axis=-1)  # remove the last dimension if it's 1
        #? NOTE: assumes numpy-style image with shape (height, width, channels)
        overlay = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.float32)
        for label, color in color_map.items():
            overlay = np.where(mask[..., None] == label, color, overlay)
    else: # if 3D with 3 color channels
        overlay = _ensure_normalized_img(mask.copy())  # ensure mask is float32 and in range [0, 1]
    overlay = (255 * _linear_alpha_blend(img_copy, overlay, alpha)).astype(np.uint8)  # blend the overlay with the image
    return overlay




def _rgb_to_grayscale(img: np.ndarray):
    """ Converts an RGB image to grayscale using the luminosity method
        :param img: input RGB image as a numpy array
        :return: grayscale image as a numpy array
    """
    if img.ndim == 2:
        return img  # already grayscale
    if img.shape[2] != 3:
        raise ValueError("Input image must have 3 channels (RGB)")
    # using the luminosity method for conversion
    weights = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    gray_img = np.dot(img[..., :3], weights).astype(np.float32)
    return gray_img


def _choose_dynamic_text_color(
    img_bg_color: Tuple[float, float, float],
    text_bg_color: Tuple[float, float, float],
    text_bg_alpha: float = 0.3,
):
    # convert RGBA to RGB first using alpha compositing with linear interpolation
    text_bg_color = [text_bg_color[i] * text_bg_alpha + img_bg_color[i] * (1 - text_bg_alpha) for i in range(3)]
    # TODO: may consider optimizing the color choice with glasbey but for now it'll be simpler to just use luminance thresholding
    # luminance calculation
    luminance_weights = [0.2126, 0.7152, 0.0722]
    # weighted average of luminance over RGB channels
    luminance = sum([luminance_weights[i] * text_bg_color[i] for i in range(3)])
    # choose black or white text based on luminance
    text_color = (0, 0, 0) if luminance > 0.5 else (255, 255, 255)
    return text_color




# TODO: decompose this into more atomic steps and more helper functions - way too long in general

def _set_bbox_mask_indices(bbox_bounds: Sequence[int], img_shape: Tuple[int], line_width: int) -> Tuple[np.ndarray, np.ndarray]:
    """ set the indices of the bounding box mask for a given bounding box to draw on the image
        :param bbox_bounds: bounding box coordinates (x1, y1, x2, y2)
        :param img_shape: shape of the image (height, width)
        :param line_width: width of the bounding box lines
        :return: indices of the bounding box mask
    """
    x1, y1, x2, y2 = bbox_bounds
    H, W = img_shape
    # calculate half line width (for even line_width, slightly more will be outside)
    half_line = line_width // 2
    extra = line_width - half_line  # handles odd line_width cases
    # create restricted ranges only around the box boundaries
    y_min = max(0, y1 - half_line)
    y_max = min(H, y2 + extra)
    x_min = max(0, x1 - half_line)
    x_max = min(W, x2 + extra)
    # greate meshgrid only within the region of interest (as short int); compute relative positions for mask conditions
    y_grid, x_grid = np.meshgrid(
        np.arange(y_min, y_max, dtype=np.int16),
        np.arange(x_min, x_max, dtype=np.int16), indexing='ij'
    )
    #& UPDATE: changed order so intersection comes immediately after instantiation for better CPU cache performance
    # create masks for each edge with centered line width
    top_mask = np.abs(y_grid - y1) < line_width/2
    # only include points that are actually on the box perimeter
    top_mask &= (x_grid >= x1 - half_line) & (x_grid <= x2 + half_line)
    # repeat for remaining edges
    bottom_mask = np.abs(y_grid - y2) < line_width/2
    bottom_mask &= (x_grid >= x1 - half_line) & (x_grid <= x2 + half_line)
    left_mask = np.abs(x_grid - x1) < line_width/2
    left_mask &= (y_grid >= y1) & (y_grid <= y2)
    right_mask = np.abs(x_grid - x2) < line_width/2
    right_mask &= (y_grid >= y1) & (y_grid <= y2)
    # combine all masks and get get indices where the final mask is True
    box_mask = top_mask | bottom_mask | left_mask | right_mask
    y_indices, x_indices = np.where(box_mask)
    # return indices converted from local (meshgrid) coordinates back to global image coordinates
    return y_indices + y_min, x_indices + x_min


def _clamp_bbox(bbox: Sequence[int], img_shape: Tuple[int]) -> Tuple[int, int, int, int]:
    """ clamps the bounding box coordinates to the image shape
        :param bbox: bounding box coordinates (x1, y1, x2, y2)
        :param img_shape: shape of the image (height, width)
        :return: clamped bounding box coordinates
    """
    x1, y1, x2, y2 = map(int, bbox)
    H, W = img_shape
    x1 = max(0, min(x1, W - 1))
    y1 = max(0, min(y1, H - 1))
    x2 = max(0, min(x2, W - 1))
    y2 = max(0, min(y2, H - 1))
    return x1, y1, x2, y2


def create_bbox_overlay_pil(
    img: np.ndarray,
    bboxes: np.ndarray,
    box_colors: np.ndarray = (1, 0, 0),
    labels: List[str] = None,
    alpha: float = 0.5,
    line_width: int = 4,
    text_size: int = 12,
    text_padding: int = 2,
    text_background: bool = True,
    text_bg_alpha: float = 0.3,
) -> np.ndarray:
    """ create a bounding box overlay for an image without using Matplotlib figures - arguments should be self-explanatory """
    assert isinstance(img, np.ndarray), "img must be a numpy array"
    assert isinstance(bboxes, np.ndarray), "bboxes must be a numpy array"
    if not isinstance(box_colors, (list, np.ndarray)) or (isinstance(box_colors, np.ndarray) and box_colors.ndim == 1):
        box_colors = np.array([box_colors] * len(bboxes))
    if not isinstance(box_colors, np.ndarray):
        box_colors = np.array(box_colors)
    # ensure the colors are all also normalized to [0, 1] range
    box_colors = _ensure_normalized_img(box_colors)
    MIN_HEIGHT = 10
    MIN_WIDTH = 10
    H, W = img.shape[:2]
    if labels is not None:
        assert len(labels) == len(bboxes), "labels must be either None or a list of strings with the same length as bboxes"
        # create PIL image to draw text on
        text_overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_overlay)
        # get the font size based on the image size
        try:
            font = ImageFont.truetype("arial.ttf", text_size)
        except IOError:
            font = ImageFont.load_default(size=text_size)
    # ensure image is float32 for calculations (will convert back at the end)
    img_dtype = img.dtype
    working_img = img.copy()
    working_img = _ensure_normalized_img(working_img)
    working_img = _ensure_full_color_img(working_img)
    # draw each bbox
    for i, (bbox, color) in enumerate(zip(bboxes, box_colors)):
        x1, y1, x2, y2 = _clamp_bbox(bbox, (H, W))
        if x2 - x1 < MIN_WIDTH or y2 - y1 < MIN_HEIGHT:
            print(f"WARNING: Bounding box {bbox} is too small to draw; skipping...")
            continue
        y_indices, x_indices = _set_bbox_mask_indices((x1, y1, x2, y2), (H, W), line_width)
        working_img[y_indices, x_indices] = _linear_alpha_blend(working_img[y_indices, x_indices], np.array(color), alpha)
        if labels is not None and i < len(labels):
            text = labels[i]
            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
            # get text position - above the box
            text_y = max(0, y1 - text_height - text_padding)
            text_x_right = min(x1 + text_width + 2 * text_padding, working_img.shape[1] - 1)
            if text_background:
                # draw background rectangle for text
                rgb_color = tuple(int(c * 255) for c in color[:3])
                bg_color = (*rgb_color, int(text_bg_alpha * 255))
                draw.rectangle([x1, text_y, text_x_right, text_y + text_height + 2 * text_padding], fill=bg_color)
            # determine text color based on background luminance
            img_bg_color = working_img[text_y:y1, x1:text_x_right]
            # calculate the average color of the image background where the text will be drawn
            img_bg_color = img_bg_color.mean(axis=(0, 1))
            text_bg_color = color
            text_color = _choose_dynamic_text_color(img_bg_color, text_bg_color, text_bg_alpha)
            # draw text on previously created text overlay
            draw.text((x1 + text_padding, text_y), text, font=font, fill=text_color) #tuple([int(c * 255) for c in text_color])
    # if there's text, blend the text overlay with the image
    if labels is not None:
        # convert PIL to numpy
        text_array = np.array(text_overlay)
        # only blend where alpha channel > 0
        alpha_mask = text_array[:, :, 3:4] / 255.0
        rgb_mask = text_array[:, :, :3] / 255.0
        # blend text with image
        working_img = rgb_mask * alpha_mask + working_img * (1 - alpha_mask)
    # Convert back to original dtype
    if img_dtype == np.uint8:
        return (working_img * 255).astype(np.uint8)
    else:
        return working_img


# TODO: I should have several functions in the old SegmentationImprovement repo that would be worth using for other transforms
    # most are based on scikit-image, so it would need to remain a dependency
    # short term additions that would be good could be the edge detection and heatmap generation functions
SUPPORTED_EDGE_DETECTION_METHODS = [
    'canny', 'sobel', 'prewitt', 'roberts', 'scharr', 'laplace', 'hysteresis'
]
SUPPORTED_ADAPTIVE_THRESHOLDING_METHODS = [
    #? NOTE: may not be using all of these but I'm listing them to look up again later
    'mean', 'otsu', 'isodata', 'li', 'minimum', 'triangle', 'yen' #'niblack', 'sauvola', 'local' #? <- these return entire thresholded masks, not a scalar threshold
]
MAX_IMG_SIZE_FOR_EDGE_DETECTION = 1280  # maximum size for edge detection before downscaling is applied


#! FIXME: the thresholding and edge masking functions need work - all results look kinda bad


def _compute_adaptive_threshold(
    img: np.ndarray,
    method: str = 'otsu',
    **kwargs
) -> float:
    # check dims since all methods expect grayscale images
    assert img.ndim == 2, "Image must be grayscale for adaptive thresholding"
    # histogram-based adaptive thresholding methods:
    if method in ['otsu', 'minimum', 'triangle', 'yen', 'isodata']:
        nbins = kwargs.get('nbins', 256)
        if method == 'otsu':
            return skfi.threshold_otsu(img, nbins=nbins)
        elif method == 'minimum':
            return skfi.threshold_minimum(img, nbins=nbins, max_num_iter=1000) #? NOTE: default max_num_iter is 10000
        elif method == 'triangle':
            return skfi.threshold_triangle(img, nbins=nbins)
        elif method == 'yen': # ! MIGHT REMOVE - Yen method's results kind of suck
            return skfi.threshold_yen(img, nbins=nbins)
        elif method == 'isodata':
            return skfi.threshold_isodata(img, nbins=nbins, return_all=False)
    elif method == 'mean':
        return skfi.threshold_mean(img)
    elif method == 'li':
        tolerance = kwargs.get('tolerance', None)  # user-supplied tolerance for Li's method
        initial_guess = kwargs.get('initial_guess', None)  # initial guess for Li's method
        return skfi.threshold_li(img, tolerance=tolerance, initial_guess=initial_guess)
    # elif method == 'local':
    #     block_size = kwargs.get('block_size', 3)  # size of the local neighborhood
    #     returnskfi.threshold_local(img, block_size=block_size, method='gaussian', mode='reflect')
    else:
        raise ValueError(f"Unknown adaptive thresholding method: {method}. Supported methods: {SUPPORTED_ADAPTIVE_THRESHOLDING_METHODS}.")


# TODO: replace explicit resizing logic with a decorator that handles resizing for all functions that need it

def create_binary_edge_mask(
    img: np.ndarray,
    method: str = 'canny',
    adaptive_threshold: bool = False,
    adaptive_threshold_method: str = 'yen',
    **kwargs
) -> np.ndarray:
    """ Creates an edge mask for an image using the specified method
        Args:
            img: input image
            method: edge detection method ('canny', 'sobel', 'prewitt', 'roberts', 'scharr', 'laplace')
            **kwargs: additional parameters for the edge detection function
        Returns:
            (np.ndarray) binary edge mask
    """
    img_copy = _ensure_normalized_img(img.copy())
    img_shape_init = img.shape
    if img.ndim == 3 and img.shape[2] == 3:
        img_copy = _rgb_to_grayscale(img_copy)  # convert to grayscale if RGB
    if max(img_shape_init) > MAX_IMG_SIZE_FOR_EDGE_DETECTION:
        # downscale the image if it's too large
        scale_factor = MAX_IMG_SIZE_FOR_EDGE_DETECTION / max(img_copy.shape)
        img_copy = sk_rescale(img_copy, scale_factor, anti_aliasing=True, mode='reflect', preserve_range=True)
    edges = None
    threshold = _compute_adaptive_threshold(img_copy, method=adaptive_threshold_method)/2 if adaptive_threshold else None
    print("Using adaptive threshold:", adaptive_threshold, "|\t with method:", adaptive_threshold_method, "|\t and threshold value:", threshold)
    if method == 'canny':
        # Canny edge detection
        sigma = kwargs.get('sigma', 1.0)
        low_threshold = threshold or kwargs.get('low_threshold', 0.1)
        high_threshold = kwargs.get('high_threshold', 0.3)
        print("low, high thresholds:", low_threshold, high_threshold)
        if high_threshold <= low_threshold:
            high_threshold = (low_threshold + 1)/2
        print("low, high thresholds:", low_threshold, high_threshold)
        edges = skfe.canny(img_copy, sigma=sigma, low_threshold=low_threshold, high_threshold=high_threshold)
    else:
        threshold = threshold or kwargs.get('threshold', 0.1)
        if method == 'sobel':
            edges = skfi.sobel(img_copy)
        elif method == 'prewitt':
            edges = skfi.prewitt(img_copy)
        elif method == 'roberts':
            edges = skfi.roberts(img_copy)
        elif method == 'scharr':
            edges = skfi.scharr(img_copy)
        elif method == 'laplace':
            edges = skfi.laplace(img_copy)
        #! MIGHT REMOVE - this is the only one of the bunch that doesn't return an *edge* mask per se but a blob-like mask
        elif method == 'hysteresis':
            # TODO: requires both a high and low threshold, so I need to figure out a method for that later
            low_threshold = threshold or kwargs.get('low_threshold', 0.1)
            high_threshold = kwargs.get('high_threshold', 0.3)
            if high_threshold <= low_threshold:
                high_threshold = (low_threshold + 1)/2
            edges = skfi.apply_hysteresis_threshold(img_copy, low_threshold, high_threshold)
        else:
            raise ValueError(f"Unknown edge detection method: {method}. Supported methods: {SUPPORTED_EDGE_DETECTION_METHODS}.")
        # apply threshold to get binary mask - all filters return float32 images in range [0, 1]
        if method not in ['canny', 'hysteresis']:
            edges = edges > threshold
    if edges is None:
        raise ValueError(f"Edge detection method '{method}' did not return any edges.")
    if img_copy.shape != img_shape_init:
        # if we downscaled the image, we need to upscale the edges back to the original size
        edges = sk_resize(edges, img_shape_init[:2], order=0, anti_aliasing=False, mode='reflect', preserve_range=True)
        # ensure the edges are still boolean type after resizing since it may convert them to float
        edges = (edges > 0.5).astype(np.bool_)
    return edges.astype(np.float32)  # ensure the output is float32 for consistency


def create_morphological_gradient_mask(
    img: np.ndarray,
    **kwargs
) -> np.ndarray:
    """ creates a morphological gradient mask as the difference between the dilation and erosion of the image
        Args:
            img: input image
            **kwargs: additional parameters for the gradient detection function
        Returns:
            (np.ndarray) 3-channel gradient mask (concatenated dilation - erosion across each channel)
    """
    if img.ndim == 2:
        img = np.expand_dims(img, axis=-1)  # ensure img is 3-channel
    mask = np.zeros_like(img, dtype=np.float32)
    # TODO: cache the structuring element to reuse each time
    element = sk_disk(kwargs.get('kernel_size', 3))  # default disk radius (more generally kernel size)
    # works for either 3-channel or grayscale images
    for c in range(img.shape[2]):
        dilated = sk_dilation(img[..., c], element, mode='reflect')
        eroded = sk_erosion(img[..., c], element, mode='reflect')
        mask[..., c] = dilated - eroded
    return mask


def create_ssim_heatmap(
    img1: np.ndarray,
    img2: np.ndarray,
    window_size: int = 11,
    gaussian_weights: bool = True,
    **kwargs: Any
):
    """ Creates a heatmap based on the Structural Similarity Index (SSIM) between two images """
    assert img1.shape == img2.shape, "Images must have the same shape"
    if img1.ndim == 2:
        # ensure both images are 3-channel either way so we can specify the channel axis
        img1 = np.expand_dims(img1, axis=-1)
        img2 = np.expand_dims(img2, axis=-1)
    # TODO: determine how I might want to return the mssim value for the summary statistics later
    mssim, ssim_img = sk_ssim(
        img1, img2,
        win_size=window_size, #? NOTE: ignored if gaussian_weights is True
        gaussian_weights=gaussian_weights,
        full=True,
        data_range=1.0,  # assuming images are normalized to [0, 1]
        channel_axis=-1,  # specify the channel axis for multi-channel images
        **kwargs
    )
    # TODO: might create an intermediate function to call this ones then compute an actual seaborn heatmap with ssim_img
    ssim_img = ssim_img.clip(0, 1)  # clip to [0, 1] range
    # !! results just look solarized - not sure if this is the best way to visualize SSIM if at all
    return ssim_img.astype(np.float32)  # return the SSIM image as a float32 heatmap

# adding the following transforms function specifically to conceptualize how I'll handle creation of plots without affecting matplotlib's figure context
def create_rgb_distributions(
    bins: int = 256,
    data_range: Tuple[float, float] = (0, 1),
    alpha: float = 0.5,
) -> Dict[str, np.ndarray]:
    """ Creates RGB channel distributions for an image
        :param bins: number of bins for the histogram
        :param data_range: range of values for the histogram
        :param alpha: transparency of the distribution plot
        :return: a callable that can be used to populate the axes with the RGB distribution plot
    """
    # TODO: I was writing this with the intent to pass an image to the inner function, but I could actually do the opposite and pass
        #~ an axes to the top level function and accept an image in the inner function since the same axes objects are reused for each image
    # return local function to populate the axes with the RGB distributions when called
    def populate_axes(img, ax: plt.Axes) -> plt.Axes: # assume a single axes object is passed in
        """ callable to return to the dispatcher which populates the axes with the histogram """
        assert img.ndim == 3 and img.shape[2] == 3, "Image must be RGB with shape (H, W, 3)"
        # ensure the image is normalized to [0, 1]
        img = _ensure_normalized_img(img)
        TOL = 1e-6  # tolerance to add to histogram for numerical stability (to use log scale if needed)
        # compute histograms for each channel
        histogram = np.array([
            np.histogram(img[..., i], bins=bins, range=data_range)[0] for i in range(3)
        ]).astype(np.float32)
        # TODO: move the tick_params and grid settings to a separate function to reuse for similar plotting functions
            # may also let log_scale be a flag for this new function and replace the ax.set_yscale('log') with it
        ax.tick_params(reset=True, axis='both', which='both', color='black', top=False, right=False)
        #ax.margins(x=0.05, y=0.05)  # Add small margins
        ax.grid(visible=True, alpha=alpha/2, axis='both')  # set grid transparency
        ax = sns.kdeplot(
            data = histogram.T + TOL, # transpose to have channels as columns and add small tolerance to avoid log(0)
            ax=ax,
            palette=sns.color_palette(['red', 'green', 'blue']), # used only for RGB channels
            fill=True,
            common_norm=False,  # normalize each channel separately
            common_grid=True,   # use common grid for all channels
            alpha=alpha,
            linewidth=0,
        )
        ax.set_yscale('log')  # set y-axis to log scale
        ax.set_title('RGB Channel Distributions')
        #! FIXME: this approach to generating the legend on existing plots is discouraged by seaborn - might want to extract artists and pass those
        ax.legend(['Blue', 'Green', 'Red'], title='Channels', loc='upper right')
        return ax
    return populate_axes  # return the callable to be used by the dispatcher



# TODO: maybe create another utility function that computes color space statistics to either plot or use for the summary box


# TODO: add factory/dispatcher function to be called by the loader model to generate the appropriate overlay, additional mask, or a graph of some sort
    # NOTE: still need to figure out how to handle regular data plots
    # main thing that I can think to do is pass in the axes as well, since they're allocated well in advance of the images
        # will require major changes in logic between the data manager and controllers, but that was planned anyway
    

# TODO: determine how to generate the plots for charts and stuff generated by matplotlib/seaborn \
    # todo - since starting new matplotlib figures would interfere with the current view
        # will require major changes in logic between the data manager and controllers, but that was planned anyway
    # Directions to Consider:
    # 1. create methods to pass an axes object (from the current view) from the controller to dispatcher methods in this file
        # - more straightforward, may allow more complex plotting options, and is probably more maintainable
        # - relatively easy to pass existing axes since they're allocated well in advance of any images and continuously reused
    # 2. create more universal method(s) that wrap whatever needs to be done and returns a callable so the data manager can call it
            # (through the controller passings its axes objects)
        # - would allow arbitrary chaining all the way up to the controller, which would be more flexible and fairly
        # - easy to implement and work with upstream
        # - this could also be designed in a systolic way to allow different functional logic applied to each axes index
            # i.e. with a systolic array of the same shape as the grid of axes, where each element is a callable
            # could be taken as far as all the image loading being done by composed callables
    # both methods require a greater amount of new dispatcher logic in the new models and data manager
