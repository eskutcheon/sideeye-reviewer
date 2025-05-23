import os
import random
from typing import List, Optional, Union, Callable, Any
import matplotlib.pyplot as plt


""" Type for a transformation function that takes an image array (or PIL image) and returns a transformed image """
TransformFn = Callable[[Any], Any]


class DataManager:
    """
        Manages:
        1) File listing + checkpoint logic (optionally via ImageSorter).
        2) Loading images from disk, applying transformations if defined.
        3) (Optional) Sorting/labeling via an internal ImageSorter & BinManager if needed.
        4) Provides a placeholder for future expansions: on-the-fly creation of new images or plots.
        If you do not need labeling, you simply never call the 'assign_label' or 'undo_label' methods.
    """
    def __init__(
        self,
        image_folders: Union[List[str], str],
        out_dir: Optional[str] = None,
        labels: Optional[List[str]] = None,
        file_list: Optional[List[str]] = None,
        summary_type: Optional[str] = None,
        json_name: str = "sorting_output.json",
        enable_sorting: bool = True,
        shuffle = False
    ):
        """
            :param image_folders: One or more directories where images are stored.
                                If a single string, it's converted into a one-element list.
            :param out_dir:       Where sorted results are stored (if sorting is enabled).
            :param labels:        List of possible labels (if sorting is enabled).
            :param file_list:     If given, restricts the images to these filenames, ignoring folder listing.
            :param json_name:     Output JSON name for BinManager (if sorting is enabled).
            :param enable_sorting: If False, we skip creating ImageSorter and BinManager references entirely.
        """
        self.image_folders = [image_folders] if isinstance(image_folders, str) else image_folders
        self._verify_num_folders()  # ensure the number of image folders is valid for the current setup
        # TODO: abstract this further and allow for more generalized setup not depending on the number of image_folders
            # for instance, using a data generation model, it should be base image + number to generate
        self.images_per_batch = len(self.image_folders)
        self.file_list = file_list
        self.summary_type = summary_type
        self.enable_sorting = enable_sorting
        self.labels = labels or []
        self.out_dir = out_dir
        self.json_name = json_name
        self.shuffle = shuffle
        # If sorting is enabled, create the ImageSorter (and BinManager inside it), otherwise it remains None.
        self.sorter = None
        if self.enable_sorting and out_dir and labels is not None:
            from .bin_manager import BinManager
            self.sorter = BinManager(
                labels=self.labels,
                out_dir=self.out_dir,
                outfile_name=self.json_name
            )
        # keep a pipeline of transformations to apply to each loaded image, e.g. edge detection overlays, histograms, etc.
        # TODO: may end up creating an equivalent of torchvision.transforms.Compose for numpy arrays for this
        self.transform_pipeline: List[TransformFn] = []
        #!!! DEBUGGING - for testing the summary box rendering - remove later
        self.temp_iter = 0


    def _verify_num_folders(self):
        """ Check if the number of image folders is valid for the current setup. """
        if len(self.image_folders) == 0:
            raise ValueError("No image folders provided.")
        if len(self.image_folders) > 2:
            raise ValueError("Only up to 2 image folders are supported for paired images (e.g., image + mask).")

    def load_images(self, filename: str) -> List[Any]:
        """ For multiple folders (e.g., image vs. mask), load an image from each folder in self.image_folders.
            If sorting is enabled, we might also delegate to sorter.get_image_paths(...) to be consistent.
        """
        paths = self.get_image_paths(filename)
        images = []
        for p in paths:
            img = plt.imread(p)
            for fn in self.transform_pipeline:
                img = fn(img)
            images.append(img)
        return images

    # TODO: for the following 3 methods, I should probably rewrite to throw an error if sorting is not enabled but it's called anyway
    ############################################################################################################
    def assign_labels(self, filename: str, labels: Union[str, List[str]]):
        """ for single or multi-label assignment - only meaningful if sorting is enabled, otherwise no-op """
        if self.sorter:
            self.sorter.set_current_image(filename)
            self.sorter.update_bin(labels)

    def undo_label(self):
        """ Undo last labeling action. """
        if self.sorter:
            self.sorter.update_bin(labels=None, remove=True)

    def write_results(self):
        """ Writes final sorting results (bin manager JSON). """
        if self.sorter:
            self.sorter.write_to_outfiles()
    #############################################################################################################

    def add_transform(self, transform_fn: TransformFn):
        """ Add a function to be applied to each loaded image. e.g., lambda img: apply_overlay(img, overlay, alpha=0.5) """
        self.transform_pipeline.append(transform_fn)

    def clear_transforms(self):
        """ flush all transformations from the queue """
        self.transform_pipeline.clear()

    # -------------------------------------------------------------------------
    # Future: On‐the‐fly creation of new images/plots
    # -------------------------------------------------------------------------

    def create_additional_image(self, filename: str, **kwargs):
        """
            Placeholder for a future extension: generating edge detection, histograms, etc.
            Possibly store them in a cache.
        """
        # e.g. do something with load_image, compute edges, store to a cache dict
        pass


    ################################################################################################################
    # adding functions from the old ImageSorter class related to file handling while the rest goes in the BinManager
    # will need to check for redundancy and how accessing the sorter will need to be refactored
    ################################################################################################################

    def get_file_list(self, checkpoint: Optional[Union[bool, int]] = False) -> List[str]:
        """ Returns the list of files to be reviewed, possibly skipping the first 'checkpoint' entries """
        # NOTE: whole pipeline still assumes that corresponding files share filenames
        all_files = self.file_list if self.file_list else os.listdir(self.image_folders[0])
        ckpt_idx = self.check_if_resuming(len(all_files), checkpoint)
        if ckpt_idx:
            all_files = all_files[checkpoint:]
        if self.shuffle:
            random.shuffle(all_files)
        return all_files

    def get_image_paths(self, img_name: str) -> List[str]:
        """ Return the full path(s) for the given filename in each directory """
        # TODO: add safeguards for missing folders or files
        return [os.path.join(d, img_name) for d in self.image_folders]

    def check_if_resuming(self, num_files: int, checkpoint: Union[bool, int] = True) -> Optional[int]:
        """ If checkpoint is True, we read how many have already been sorted from the JSON file and skip that many.
            If checkpoint is an int >= 2, we skip exactly that many. If checkpoint is False, start from zero.
        """
        if not checkpoint:
            return None
        # if checkpoint is an int and it's greater than 1 (i.e. no progress), return it
        if isinstance(checkpoint, int) and 1 < checkpoint < num_files:
            return checkpoint
        # otherwise see how many have been sorted so far
        # TODO: rename once I figure out what I want to do with the new task-specific sorter model class
            # may want to do checkpointing for more than just the sorting task
        if self.sorter:
            files_checked = self.sorter.get_num_sorted()
            if files_checked == 0:
                return None
            return files_checked
        return None

    def generate_summary_text(self) -> str:
        """ generate text about the data based on self.summary_type to be displayed by the viewer in a summary box """
        # TODO: compare summary_type against supported summary types and generate text accordingly
        self.temp_iter += 1
        # testing that this is updating and not drawing on top of existing text
        # TODO: later this should be based on querying the current image (FIXME: apparently that's in the sorter at the moment)
        return f"TESTING: summary box for type '{self.summary_type}' - curr value: {self.temp_iter}"