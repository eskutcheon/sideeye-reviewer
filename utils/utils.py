import torch
import torchvision.io as IO
import torch.utils.data as torch_data
import torchvision.transforms as T
import numpy as np
import os
from typing import Union, Tuple, Dict, List
# import settings
# TODO: start refactoring uses of the config to eliminate dependence on outside settings (move to accepting function args)
import utils.config as cfg

# TODO: add this to the img_utils file later to eliminate circular dependencies - need to track down usage first
def enforce_type(target_type):
    def decorator(func):
        def wrapper(img, *args, **kwargs):
            if target_type == "tensor":
                if isinstance(img, np.ndarray):
                    img = ndarray_to_tensor(img)
            elif target_type == "ndarray":
                if torch.is_tensor(img):
                    img = tensor_to_ndarray(img.cpu())
            else:
                raise ValueError("Unsupported target type, must be either 'tensor' or 'ndarray'")
            return func(img, *args, **kwargs)
        return wrapper
    return decorator

def ndarray_to_tensor(arr: np.ndarray, rescale=False) -> torch.Tensor:
    assert isinstance(arr, np.ndarray), f"input must be a numpy.ndarray object; got {type(arr)}"
    if rescale:
        arr = arr.astype(np.float32)/255
    if arr.ndim not in [3,4]:
        return torch.from_numpy(arr)
    is_batch = (arr.ndim == 4)
    new_dims = (0,3,1,2) if is_batch else (2,0,1)
    tensor = torch.from_numpy(np.transpose(arr, new_dims))
    return tensor

def tensor_to_ndarray(tensor: torch.Tensor, rescale=False) -> np.ndarray:
    ''' convert pytorch tensor in shape (N,C,H,W) or (C,H,W) to ndarray of shape (N,H,W,C) or (H,W,C) '''
    assert isinstance(tensor, torch.Tensor), f"input must be a torch.Tensor object; got {type(tensor)}"
    if rescale:
        np_array *= 255
    if tensor.dim() not in [3,4]:
        return tensor.numpy()
    # TODO: check if tensor is already permuted to shape below
    is_batch = is_batch_tensor(tensor)
    new_dims = (0,2,3,1) if is_batch else (1,2,0)
    # NOTE: might be faster to do torch.permute(new_dims).numpy()
    np_array = np.transpose(tensor.numpy(), new_dims)
    return np_array

def is_valid_shape(tensor):
    def check_channels(num_dims, channel_idx):
        if num_dims in [2,3,4]:
            if num_dims != 2:
                if tensor.shape[channel_idx[num_dims]] not in [1,3]:
                    raise ValueError(f"expected channel dimension to be in {{1,3}} in index 0 for 3D tensor or index 1 for batch tensor. Got shape {tensor.shape}")
        else:
            raise ValueError(f"image tensor must be 2D, 3D, or 4D")
        return True
    num_dims = len(tensor.shape)
    if isinstance(tensor, torch.Tensor):
        channel_idx = {4: 1, 3: 0}
        return check_channels(num_dims, channel_idx)
    elif isinstance(tensor, np.ndarray):
        channel_idx = {4: -1, 3: -1}
        return check_channels(num_dims, channel_idx)
    else:
        raise NotImplementedError(f"method only implemented for torch.Tensor, np.ndarray, got {type(tensor)}")

# FIXME: mostly written by ChatGPT and needs testing - edited heavily by me
def plot_images(*images, title=None, cols=2):
    """ Plots a variable number of images.
        Args:
            *images: Variable-length list of images to plot.
            title (str): Title for the entire plot.
            cols (int): Number of columns for the subplot grid.
    """
    import matplotlib.pyplot as plt
    num_images = len(images)
    rows = num_images // cols + num_images % cols
    cols = num_images if num_images < cols else cols
    position = range(1, num_images + 1)
    fig = plt.figure(figsize=(20, 30), facecolor = 'lightgray')
    for k, img in zip(position, images):
        if not is_valid_shape(img):
            raise ValueError(f"Cannot accept img of type {type(img)} with shape {img.shape}")
        ax = fig.add_subplot(rows, cols, k)
        if isinstance(img, torch.Tensor):
            if img.dtype == torch.bool:
                img = 255*img.to(torch.uint8)
            if img.dtype in [torch.float32, torch.float64]:
                img = img.mul(255).to(torch.uint8)
            img = tensor_to_ndarray(img.cpu())
        elif isinstance(img, np.ndarray):
            img = img.astype(int)
        if img.ndim == 2:  # Grayscale
            plt.imshow(img, cmap='gray', aspect='auto')
        else:  # Color
            plt.imshow(img, aspect='auto')
        plt.axis('off')
    if title:
        fig.suptitle(title, fontsize='large')
    #manager = maximize_window()
    plt.show()

def labels_to_onehot(idx_tensor: torch.LongTensor, num_classes: int) -> torch.Tensor:
    ''' mostly intended to be used by prediction functions above - may change later
        Args:
            idx_tensor: tensor of C different categorical labels of shape (1,H,W) or (N,1,H,W)
            num_classes: number of classes C in tensor input
        Returns:
            one-hot encoded boolean tensor in shape (C,H,W) or (N,C,H,W)
    '''
    is_batch = is_batch_tensor(idx_tensor)
    out_shape = list(idx_tensor.shape)
    out_shape[is_batch] = num_classes
    # because F.one_hot() returns an annoying shape
    one_hot = torch.zeros(size=out_shape).to(idx_tensor.device, dtype=torch.bool)
    # this method only accepts long tensors for some reason
    return one_hot.scatter_(is_batch, idx_tensor.to(dtype=torch.int64), 1)


def get_user_confirmation(prompt):
    answers = {'y': True, 'n': False}
    response = input(f"[Y/n] {prompt} ").lower()
    while response not in answers:
        print("Invalid input. Please enter 'y' or 'n' (not case sensitive).")
        response = input(f"[Y/n] {prompt} ").lower()
    return answers[response]

def populate_camera_dict(img_dir):
    # Load image filenames and separate by camera source
    SUPPORTED_CAM_TYPES = ['FV', 'RV', 'MVL', 'MVR']
    images_by_camera = {cam: [] for cam in SUPPORTED_CAM_TYPES}
    for filename in os.listdir(img_dir):
        # TODO: will need to rewrite this line for the new dataset when we append "CAVS" to the end
        camera = filename.split('_')[1].split('.')[0]
        if camera not in SUPPORTED_CAM_TYPES:
            raise ValueError(f"Camera value must be in set {SUPPORTED_CAM_TYPES}")
        # sort filename into list for camera
        images_by_camera[camera].append(filename)
    print("Camera Distribution:")
    for key, val in images_by_camera.items():
        print(f"\t{key}: {len(val)} images")
    return images_by_camera

# mostly writing this just to be more explicit with calls while debugging manually
class Debugger(object):
    @staticmethod
    def get_min_max(arr, is_torch):
        min_func, max_func = (torch.min, torch.max) if is_torch else (np.min, np.max)
        print(f'\tmin and max: {min_func(arr), max_func(arr)}')

    @staticmethod
    def get_array_values(arr, is_torch):
        set_func = torch.unique if is_torch else np.unique
        print(f'\tvalues: {set_func(arr)}')

    @staticmethod
    def get_arr_shape(arr, is_torch):
        print(f'\tshape: {arr.shape}')

    @staticmethod
    def get_arr_type(arr, is_torch):
        print(f'\tdata type: {type(arr)}')

    @staticmethod
    def get_arr_device(arr, is_torch):
        if is_torch:
            print(f'\tdevice: {arr.device}')
        else:
            pass

    @staticmethod
    def get_element_type(arr, is_torch):
        print(f'\telement types: {arr.dtype}') # same for torch and numpy


def get_all_debug(arr, msg='unnamed tensor'):
    print(f'attributes of {msg}:')
    # FIXME: doesn't work on work computer running Python 3.7.8
    for func in filter(lambda x: callable(x), Debugger.__dict__.values()):
        func(arr, isinstance(arr, torch.Tensor))
    print()

# FIXME: remove dependence on the global settings object from the other project - replace w/ config
def get_inverse_frequency():
    # mean of class label proportion of pixels across all images in the dataset
    dist_dict = vars(cfg.ClassDistribution)
    mean_dists = np.array(list(dist_dict.values()), dtype=np.float32)
    # inverse class frequency based on mean proportion of pixels
    class_weights = np.sum(mean_dists)/mean_dists
    # return normalized class weights
    return class_weights/np.sum(class_weights)

def download_dataset():
    from gdown import download
    from zipfile import ZipFile
    drive_link = cfg.DataSet.DATA_SOURCE
    data_dir = cfg.Directories.data
    if not os.path.isdir(data_dir):
        os.mkdir(data_dir)
    output_path = os.path.join(data_dir, 'soiling_dataset.zip')
    print("\nDownloading Valeo Woodscape dataset from Google Drive:")
    try:
        file_path = download(drive_link, output_path, quiet=False, use_cookies=False)
        print(f"Success: Downloaded soiling_dataset.zip. Now unzipping into {data_dir}")
        with ZipFile(file_path, 'r') as zipped_dataset:
            zipped_dataset.extractall(data_dir)
    except:
        raise Exception("Something went wrong in downloading the dataset")


def is_batch_tensor(tensor: Union[torch.Tensor, np.ndarray]):
    ''' test if shape is (N,C,H,W) or (C,H,W) '''
    return int(len(tensor.shape) == 4) # 0 if shape is (C,H,W), 1 if shape is (N,C,H,W)

def is_label_tensor(tensor: torch.Tensor, num_classes: int):
    ''' test if the only values in the tensor are in range(num_classes), i.e., if uniques is a subset of range(num_classes)'''
    uniques = torch.unique(tensor).to(dtype=tensor.dtype)
    return torch.all(torch.any(uniques[:, None] == torch.arange(num_classes, dtype=uniques.dtype), dim=1))

def is_C_channel(tensor: torch.Tensor, C: int):
    ''' test if C categorical labels are in C dimensions '''
    return (tensor.shape[is_batch_tensor(tensor)] == C)

def is_flat_label_tensor(tensor: torch.Tensor, num_classes: int):
    ''' test if values are class labels and if labels are all in one dim'''
    return is_C_channel(tensor, 1) and is_label_tensor(tensor, num_classes)

def is_onehot_encoded_tensor(tensor: torch.Tensor, num_classes: int):
    ''' test if the tensor is encoded in C channels and whether values are in {0,1} '''
    # torch.equal not implemented for bool, so I had to cast it to uint8
    return is_C_channel(tensor, num_classes) and is_label_tensor(tensor.to(torch.uint8), 2)

def test_path(dir_path):
    if not os.path.exists(dir_path):
        raise Exception(f'Directory {dir_path} given is invalid')


def get_matching_filenames(input_dir, substr):
    return list(filter(lambda x: (substr in x) and (not os.path.isdir(os.path.join(input_dir, x))), os.listdir(input_dir)))

def read_and_resize_image(img_path: str, out_size: Union[Tuple[int], List[int]], is_labels: bool = True) -> torch.Tensor:
    ''' 3-channel image will be read from file as (3,*out_size) tensor with values 0-255
        a flat tensor of mask values will be read as (1, *out_size) tensor with values 0 to C-1
    '''
    read_mode = IO.ImageReadMode.UNCHANGED if is_labels else IO.ImageReadMode.RGB
    interp_mode = T.InterpolationMode.NEAREST if is_labels else T.InterpolationMode.BILINEAR
    # TODO: really need to split this into two functions and add checks if out_size < img shape
    # docs are inaccurate, antialias=True is NOT simply ignored if interpolation mode isn't bicubic or bilinear
    img_resize: T.Resize
    if interp_mode in [T.InterpolationMode.BILINEAR, T.InterpolationMode.BICUBIC]:
        img_resize = T.Resize(out_size, interp_mode, antialias=True)
    else:
        img_resize = T.Resize(out_size, interp_mode)
    return img_resize(IO.read_image(img_path, read_mode))


# TODO: add this to the img_utils file later to eliminate circular dependencies - need to track down usage first
class SegData(torch_data.Dataset):
    def __init__(self, img_dir: Union[str, List[str]], mask_dir: Union[str, List[str]], out_size: Tuple[int]):
        super().__init__()
        for path in [img_dir, mask_dir]:
            if isinstance(path, str):
                test_path(path)
        is_str_path = isinstance(img_dir, str) and isinstance(mask_dir, str)
        # NOTE: for future datasets, note that img and mask path names must be identical to assure proper sorting
        self.img_paths = [os.path.join(img_dir, name) for name in sorted(os.listdir(img_dir))] if is_str_path else img_dir
        self.mask_paths = [os.path.join(mask_dir, name) for name in sorted(os.listdir(mask_dir))] if is_str_path else mask_dir
        self.num_images = len(self.img_paths)
        self.OUT_SIZE = out_size

    # following 2 functions have to be overridden for the DataLoader
    def __getitem__(self, idx):
        # TODO: also need to explore the fisheye distortion correction here.
        if torch.is_tensor(idx):
            idx = idx.tolist()
        img_path = self.img_paths[idx]
        mask_path = self.mask_paths[idx]
        sample = {'img' : read_and_resize_image(img_path, self.OUT_SIZE, is_labels=False),
                'mask' : read_and_resize_image(mask_path, self.OUT_SIZE, is_labels=True)}
        return sample

    def __len__(self):
        return self.num_images


def get_dataloader(img_dir, mask_dir, out_size, shuffle=False, sample_prop=None, batch_size=1):
    if (sample_prop is not None) and not (0 < sample_prop <= 1):
        raise ValueError("sample prop must be None or a float in interval (0,1]")
    sampler = None
    dataset = SegData(img_dir, mask_dir, out_size)
    #device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    device = "cpu"
    if sample_prop is not None:
        loader_size = len(dataset)
        sampler = torch_data.sampler.SubsetRandomSampler(torch.randperm(loader_size)[:int(loader_size*sample_prop)])
    # https://datagy.io/pytorch-dataloader/
    return torch_data.DataLoader(dataset,
                                batch_size=batch_size,
                                shuffle=shuffle,
                                sampler=sampler,
                                generator=torch.Generator(device),
                                num_workers=4,
                                #pin_memory=True, # this causes out of memory errors eventually
                                #persistent_workers=True, # pretty sure this is the thing causing issues with tqdm
                                prefetch_factor=2)