import os
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
        json_name: str = "sorting_output.json",
        enable_sorting: bool = True
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
        # TODO: abstract this further and allow for more generalized setup not depending on the number of image_folders
        self.images_per_batch = len(self.image_folders)
        self.file_list = file_list
        self.enable_sorting = enable_sorting
        self.labels = labels or []
        self.out_dir = out_dir
        self.json_name = json_name
        # If sorting is enabled, create the ImageSorter (and BinManager inside it), otherwise it remains None.
        self.sorter = None
        if self.enable_sorting and out_dir and labels is not None:
            from .sorter import ImageSorter  # or wherever sorter is
            self.sorter = ImageSorter(
                image_folders=self.image_folders,
                out_dir=self.out_dir,
                labels=self.labels,
                file_list=self.file_list,
                json_name=self.json_name
            )
        # keep a pipeline of transformations to apply to each loaded image, e.g. edge detection overlays, histograms, etc.
        # TODO: may end up creating an equivalent of torchvision.transforms.Compose for numpy arrays for this
        self.transform_pipeline: List[TransformFn] = []


    def get_file_list(self, checkpoint: Union[bool, int] = False) -> List[str]:
        """
            Returns the list of files, potentially skipping some if 'checkpoint' is True or an integer.
            If sorting is enabled, we delegate to self.sorter for consistent logic (including get_num_sorted).
            Otherwise, we build a simple list from self.file_list or the folder listing.
        """
        if self.sorter is not None:
            ckpt_idx = self.sorter.check_if_resuming(checkpoint)
            return self.sorter.get_file_list(ckpt_idx)
        else:
            # No sorting logic. We'll just handle file listing ourselves.
            all_files = self.file_list
            if all_files is None:
                all_files = os.listdir(self.image_folders[0]) if self.image_folders else []
            if isinstance(checkpoint, int) and checkpoint > 0:
                return all_files[checkpoint:]
            return all_files

    def load_images(self, filename: str) -> List[Any]:
        """ For multiple folders (e.g., image vs. mask), load an image from each folder in self.image_folders.
            If sorting is enabled, we might also delegate to sorter.get_image_paths(...) to be consistent.
        """
        if self.sorter:
            paths = self.sorter.get_image_paths(filename)
        else:
            paths = []
            for folder in self.image_folders:
                paths.append(os.path.join(folder, filename))
        images = []
        for p in paths:
            img = plt.imread(p)
            for fn in self.transform_pipeline:
                img = fn(img)
            images.append(img)
        return images

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
            self.sorter.bin_manager.write_to_outfiles()


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
