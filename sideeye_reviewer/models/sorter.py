import os
from typing import Union, List, Tuple, Optional
import random
# local imports
from .bin_manager import BinManager


class ImageSorter:
    """ manages sorting and coordinating the BinManager - now contained within the DataManager class """
    def __init__(
        self,
        image_folders: Union[List[str], Tuple[str], str],
        out_dir: str,
        labels: List[str],
        file_list: Optional[List[str]] = None,
        json_name: str = "sorting_output.json",
        shuffle = False
    ):
        """
            :param image_folders: either a str or list/tuple of up to 2 directory paths
            :param out_dir: where results should be stored
            :param labels: all possible label/bin names
            :param file_list: if given, restricts the images to just these filenames
            :param json_name: filename to store classification results
        """
        # TODO: replace with a helper function later - think I already have some version of "ensure_list_format"
        self.img_dirs = [image_folders] if isinstance(image_folders, str) else list(image_folders)
        # Only supporting up to 2 directories (e.g. image + mask)
        # TODO: planned to be changed within the new DataManager class
        if len(self.img_dirs) > 2:
            raise NotImplementedError("Only supporting up to 2 directories for image pairs.")
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)
        # if a file_list is provided, use it rather than os.listdir
        self.user_file_list = file_list
        self.sorter_labels = labels
        self.shuffle = shuffle
        # Shared bin manager that can handle single or multiple bins
        self.bin_manager = BinManager(labels, out_dir, json_name)
        self.current_image = None

    #^########################################################################
    def get_sorter_labels(self) -> List[str]:
        return self.sorter_labels
    #^########################################################################

    def check_if_resuming(self, checkpoint: Union[bool, int] = True) -> Optional[int]:
        """ If checkpoint is True, we read how many have already been sorted from the JSON file and skip that many.
            If checkpoint is an int >= 2, we skip exactly that many. If checkpoint is False, start from zero.
        """
        if not checkpoint:
            return None
        if isinstance(checkpoint, int) and checkpoint >= 2:
            return checkpoint
        # Otherwise see how many have been sorted so far
        files_checked = self.bin_manager.get_num_sorted()
        if files_checked == 0:
            return None
        return files_checked

    def get_file_list(self, checkpoint: Optional[int] = None) -> List[str]:
        """ Returns the list of files to be reviewed, possibly skipping the first 'checkpoint' entries """
        all_files = self.user_file_list if self.user_file_list is not None else os.listdir(self.img_dirs[0])
        if checkpoint is not None and checkpoint < len(all_files):
            all_files = all_files[checkpoint:]
        if self.shuffle:
            random.shuffle(all_files)
        return all_files

    def get_image_paths(self, img_name: str) -> List[str]:
        """ Return the full path(s) for the given filename in each directory """
        # TODO: add safeguards for missing folders or files
        return [os.path.join(d, img_name) for d in self.img_dirs]

    def set_current_image(self, img_name: str):
        # might want to add this to the reviewer classes instead
        self.current_image = img_name

    def update_bin(self, labels, remove=False):
        """ For single-label usage, 'labels' will be a string. For multi-label usage, 'labels' will typically be a list of strings.
            We unify them internally in BinManager.
        """
        if remove:
            self.bin_manager.undo_sort()
        else:
            self.bin_manager.add_filename(labels, self.current_image)
