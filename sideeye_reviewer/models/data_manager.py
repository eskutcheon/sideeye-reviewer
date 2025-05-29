import os
from pathlib import Path
import numpy as np
from typing import Dict, List, Optional, Union, Callable, Any, Iterable
# import matplotlib.pyplot as plt


""" Type for a transformation function that takes an image array (or PIL image) and returns a transformed image """
# TransformFn = Callable[[Any], Any] #& UDPATE: added a new Protocol `Transform` in `etl_models.py` for this




# class DataManager:
#     """
#         Manages:
#         1) File listing + checkpoint logic (optionally via ImageSorter).
#         2) Loading images from disk, applying transformations if defined.
#         3) (Optional) Sorting/labeling via an internal ImageSorter & BinManager if needed.
#         4) Provides a placeholder for future expansions: on-the-fly creation of new images or plots.
#         If you do not need labeling, you simply never call the 'assign_label' or 'undo_label' methods.
#     """
#     def __init__(
#         self,
#         image_folders: Union[List[str], str],
#         out_dir: Optional[str] = None,
#         labels: Optional[List[str]] = None,
#         file_list: Optional[List[str]] = None,
#         summary_type: Optional[str] = None,
#         json_name: str = "sorting_output.json",
#         enable_sorting: bool = True,
#         shuffle = False
#     ):
#         """
#             :param image_folders: One or more directories where images are stored.
#                                 If a single string, it's converted into a one-element list.
#             :param out_dir:       Where sorted results are stored (if sorting is enabled).
#             :param labels:        List of possible labels (if sorting is enabled).
#             :param file_list:     If given, restricts the images to these filenames, ignoring folder listing.
#             :param json_name:     Output JSON name for BinManager (if sorting is enabled).
#             :param enable_sorting: If False, we skip creating ImageSorter and BinManager references entirely.
#         """
#         self.image_folders = [image_folders] if isinstance(image_folders, str) else image_folders
#         self._verify_num_folders()  # ensure the number of image folders is valid for the current setup
#         # TODO: abstract this further and allow for more generalized setup not depending on the number of image_folders
#             # for instance, using a data generation model, it should be base image + number to generate
#         self.images_per_batch = len(self.image_folders)
#         self.file_list = file_list
#         self.summary_type = summary_type
#         self.enable_sorting = enable_sorting
#         self.labels = labels or []
#         self.out_dir = out_dir
#         self.json_name = json_name
#         self.shuffle = shuffle
#         # If sorting is enabled, create the ImageSorter (and BinManager inside it), otherwise it remains None.
#         self.sorter = None
#         if self.enable_sorting and out_dir and labels is not None:
#             from .bin_manager import BinManager
#             self.sorter = BinManager(
#                 labels=self.labels,
#                 out_dir=self.out_dir,
#                 outfile_name=self.json_name
#             )
#         # keep a pipeline of transformations to apply to each loaded image, e.g. edge detection overlays, histograms, etc.
#         # TODO: may end up creating an equivalent of torchvision.transforms.Compose for numpy arrays for this
#         # self.transform_pipeline: List[TransformFn] = []
#         #!!! DEBUGGING - for testing the summary box rendering - remove later
#         self.temp_iter = 0


#     #& should now be handled by the DataSource object in the PreLoaderModel
#     def _verify_num_folders(self):
#         """ Check if the number of image folders is valid for the current setup. """
#         if len(self.image_folders) == 0:
#             raise ValueError("No image folders provided.")
#         if len(self.image_folders) > 2:
#             raise ValueError("Only up to 2 image folders are supported for paired images (e.g., image + mask).")

#     #& should be replaced by the new PreLoaderModel.load
#     def load_images(self, filename: str) -> List[Any]:
#         """ For multiple folders (e.g., image vs. mask), load an image from each folder in self.image_folders.
#             If sorting is enabled, we might also delegate to sorter.get_image_paths(...) to be consistent.
#         """
#         paths = self.get_image_paths(filename)
#         images = []
#         for p in paths:
#             img = plt.imread(p)
#             # for fn in self.transform_pipeline:
#             #     img = fn(img)
#             images.append(img)
#         return images

#     # TODO: for the following 3 methods, I should probably rewrite to throw an error if sorting is not enabled but it's called anyway
#     ############################################################################################################
#     #& REPLACED
#     def assign_labels(self, filename: str, labels: Union[str, List[str]]):
#         """ for single or multi-label assignment - only meaningful if sorting is enabled, otherwise no-op """
#         if self.sorter:
#             self.sorter.set_current_image(filename)
#             self.sorter.update_bin(labels)

#     #& REPLACED
#     def undo_label(self):
#         """ Undo last labeling action. """
#         if self.sorter:
#             self.sorter.update_bin(labels=None, remove=True)

#     #& REPLACED
#     def write_results(self):
#         """ Writes final sorting results (bin manager JSON). """
#         if self.sorter:
#             self.sorter.write_to_outfiles()
#     #############################################################################################################


#     ################################################################################################################
#     # adding functions from the old ImageSorter class related to file handling while the rest goes in the BinManager
#     # will need to check for redundancy and how accessing the sorter will need to be refactored
#     ################################################################################################################

#     #& should be replaced by the concrete subclass of DataSource
#     def get_file_list(self, checkpoint: Optional[Union[bool, int]] = False) -> List[str]:
#         """ Returns the list of files to be reviewed, possibly skipping the first 'checkpoint' entries """
#         # NOTE: whole pipeline still assumes that corresponding files share filenames
#         all_files = self.file_list if self.file_list else os.listdir(self.image_folders[0])
#         ckpt_idx = self.check_if_resuming(len(all_files), checkpoint)
#         if ckpt_idx:
#             all_files = all_files[ckpt_idx:]
#         if self.shuffle:
#             random.shuffle(all_files)
#         return all_files

#     #& should be replaced by the concrete subclass of DataSource
#     def get_image_paths(self, img_name: str) -> List[str]:
#         """ Return the full path(s) for the given filename in each directory """
#         # TODO: add safeguards for missing folders or files
#         return [os.path.join(d, img_name) for d in self.image_folders]

#     #& logic should be integrated into the DataSource conditioned on the SessionManager having a checkpoint to resume from
#     def check_if_resuming(self, num_files: int, checkpoint: Union[bool, int] = True) -> Optional[int]:
#         """ If checkpoint is True, we read how many have already been sorted from the JSON file and skip that many.
#             If checkpoint is an int >= 2, we skip exactly that many. If checkpoint is False, start from zero.
#         """
#         if not checkpoint:
#             return None
#         # if checkpoint is an int and it's greater than 1 (i.e. no progress), return it
#         if isinstance(checkpoint, int) and 1 < checkpoint < num_files:
#             return checkpoint
#         # otherwise see how many have been sorted so far
#         # TODO: rename once I figure out what I want to do with the new task-specific sorter model class
#             # may want to do checkpointing for more than just the sorting task
#         if self.sorter:
#             files_checked = self.sorter.get_num_sorted()
#             if files_checked != 0:
#                 return files_checked
#         return None

#     #& not sure where this should go, but I think it should be handled by a long but simple chain of calls from the controller to some utility functions
#     def generate_summary_text(self) -> str:
#         """ generate text about the data based on self.summary_type to be displayed by the viewer in a summary box """
#         # TODO: compare summary_type against supported summary types and generate text accordingly
#         self.temp_iter += 1
#         return f"TESTING: summary box for type '{self.summary_type}' - curr value: {self.temp_iter}"




from .etl_models import PreLoaderModel, PostLoaderModel, LoadResult, UpdateResult, RenderAsset
from .task_models import TaskModel
from .session_manager import SessionManager

# -- summary‑text transform --------------------------------------------------

def summary_transform(*, item_id: str, raw: bytes, ctx: dict, **_) -> None:
    """ Adds basic info for the summary box into ctx; returns *nothing* """
    ctx["summary_text"] = f"File: {item_id} | Size: {len(raw)//1024} KB"
    # TODO: extend for more than one file or call it for each file in a list

# -- raw‑bytes‑>RGB ndarray transform ---------------------------------------

def read_bytes_as_rgb(*, item_id: str, raw: bytes, ctx: dict, idx: int) -> np.ndarray:
    import io, PIL.Image as PIL
    return np.array(PIL.open(io.BytesIO(raw)).convert("RGB"))

def img_decode_rgb(*, item_id: str, raw: bytes, ctx: dict, **_) -> RenderAsset:
    img = read_bytes_as_rgb(item_id=item_id, raw=raw, ctx=ctx, idx=0)
    return RenderAsset("image", img, target_axes=0)

def img_decode_rgb_list(*, item_id: str, raw: Union[bytes, List[bytes]], ctx: dict, **_) -> List[RenderAsset]:
    if isinstance(raw, bytes):
        # if raw is a single bytes object, decode it as a single image
        return [img_decode_rgb(item_id=item_id, raw=raw, ctx=ctx)]
    else:
        # if raw is a list of bytes objects, decode each as an image
        assets = []
        for i, buf in enumerate(raw):
            img = read_bytes_as_rgb(item_id=item_id, raw=buf, ctx=ctx, idx=i)
            assets.append(RenderAsset(kind="image", payload=img, target_axes=i))
        return assets


# TODO: add factory methods to set up the pre-loader, post-loader, and task models


class DataManager:
    """ high-level interface for managing data loading, task orchestration, and session management by the controller """
    def __init__(
        self,
        *,
        pre_loader: PreLoaderModel,
        post_loader: Optional[PostLoaderModel] = None,
        task_models: Optional[List["TaskModel"]] = None,
        session_mgr: Optional["SessionManager"] = None,
        max_cache: Optional[int] = 128,
):
        from .task_models import TaskOrchestrator  # lazy imports to avoid circular refs
        from .session_manager import SessionManager
        self.pre_loader = pre_loader
        self.post_loader = post_loader or []
        if task_models and not isinstance(task_models, Iterable):
            task_models = [task_models]  # ensure task_models is iterable
        self.tasks = TaskOrchestrator(*task_models) if task_models else None
        self.session = session_mgr or SessionManager()
        # enumerate once; DataSource guarantees deterministic order
        self._ids = list(self.pre_loader.source.enumerate())
        self._idx = -1
        self._cache: Dict[str, LoadResult] = {}
        self._max_cache = max_cache

    #~ IDEA: consider implementing a double-ended __iter__ method to allow iterating both forwards and backwards for the undo functionality

    def _insert_cache(self, lr: LoadResult):
        """ Naive LRU - purge first inserted if over limit """
        #!!! FIXME: this needs to be reconciled with using the cache in the `DataSource` subclasses like `FolderSource` or the latter needs to be removed
        if len(self._cache) >= self._max_cache:
            self._cache.pop(next(iter(self._cache)))
        self._cache[lr.item_id] = lr

    def _get_current(self) -> LoadResult:
        item_id = self._ids[self._idx]
        if item_id not in self._cache:
            lr = self.pre_loader.load(item_id)
            #print("[DataManager] Pre-loaded item:", lr)
            self._insert_cache(lr)
        return self._cache[item_id]

    #--------------- public methods for iterating through items and managing the cache ---------------

    def next(self) -> LoadResult:
        """ advance the pointer to the next item and return its pre-loaded result (cached or newly-loaded) """
        # self._idx = min(self._idx + 1, len(self._ids) - 1)
        # item_id = self._ids[self._idx]
        # if item_id not in self._cache:
        #     lr = self.pre_loader.load(item_id)
        #     self._cache_result(lr)
        # return self._cache[item_id]
        if self._idx >= len(self._ids) - 1:
            return None
        self._idx += 1
        return self._get_current()

    def prev(self) -> LoadResult | None:
        """ decrement pointer backwards if possible (needed for UNDO operation) """
        if self._idx <= 0:
            return None
        self._idx -= 1
        #return self._cache[self._ids[self._idx]]
        return self._get_current()

    #---------------  public method for applying transformations to the current item ---------------
    def apply_updaters(self, user_event: Dict[str, Any]) -> Union[UpdateResult, None]:
        """ apply post-load transformations to the current item to re-render based on user input
            - essentially the augmentation pipeline for the current item
            :param user_event: a dictionary with user input data, e.g. {'toggle_edge_detection': True}
        """
        if not self.post_loader: # if no post-loader is defined, return None
            return None
        #current = self._cache[self._ids[self._idx]]
        current = self._get_current()
        upd: UpdateResult = self.post_loader.apply(current, user_event)
        # merge new metadata back into cache so future calls see latest state
        current.metadata.update(upd.metadata)
        return upd

    #---------------  public methods for task model interaction and session management ---------------

    def assign_label(self, choice: Any):
        #& previously had the following 2 lines conditioned on self.sorter being not None
        # self.sorter.set_current_image(filename)
        # self.sorter.update_bin(labels)
        item_id = self._ids[self._idx]
        if self.tasks:
            #! ensure self.tasks.update still supports iterable `choice` for multi-label support
            self.tasks.update(item_id, choice)
        self.session.record(action="label", item_id=item_id, choice=choice)

    def undo_label(self):
        #& previously had the following line conditioned on self.sorter being not None
        # self.sorter.update_bin(labels=None, remove=True)
        item_id = self._ids[self._idx]
        if self.tasks:
            self.tasks.undo(item_id)
        self.prev() #& newer addition after rewiring data manager and controllers back together
        self.session.record(action="undo", item_id=item_id)

    def flush(self):
        #& previously had the following line conditioned on self.sorter being not None
        # self.sorter.write_to_outfiles()
        # TODO: should probably explicitly flush the cache as well, but it might not be necessary
        if self.tasks:
            self.tasks.flush_all()
        self.session.record(action="exit", item_id=None)
        self.session.flush()


    #! TEMPORARY ADDITION: adding this function to retrieve all filenames from the DataSource through the PreLoaderModel
        # eventually this should be moved to more high level controller models for managing axes, image names, and ids if nothing else
    def get_file_list(self) -> List[str]:
        """ Returns the list of files to be reviewed, as enumerated by the pre-loader's data source. """
        #return [os.path.basename(p) for p in self.pre_loader.source.get_image_paths()]
        return self._ids.copy() #& UPDATED: return a copy of the list of item IDs, which are unique identifiers for the items in the data source


    # Convenience accessor methods for controllers

    @property
    def current_item_id(self) -> str:
        # return the current file ID (for now the filename)
        return self._ids[self._idx]

    @property
    def current_idx(self) -> int:
        """ Returns the current index in the list of item IDs. """
        return self._idx

    @property
    def total(self) -> int:
        return len(self._ids)

    #! MIGHT REMOVE - not really useful without __iter__ support
    @property
    def has_next(self) -> bool:
        return self._idx < len(self._ids) - 1

    #! MIGHT REMOVE - not really useful without __iter__ support
    @property
    def has_prev(self) -> bool:
        return self._idx > 0


# re‑export commonly‑used names so controllers can simply do ```from models.data_manager import DataManager2, RenderAsset```

__all__ = [
    "RenderAsset",
    "LoadResult",
    "UpdateResult",
    "PreLoaderModel",
    "PostLoaderModel",
    "DataManager2",
]