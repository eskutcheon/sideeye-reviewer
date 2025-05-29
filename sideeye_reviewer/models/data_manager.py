import numpy as np
from typing import Dict, List, Optional, Union, Callable, Any, Iterable
from .etl_models import PreLoaderModel, PostLoaderModel, LoadResult, UpdateResult, RenderAsset
from .task_models import TaskModel
from .session_manager import SessionManager

# -- summary‑text transform --------------------------------------------------

# TODO: compare summary_type against supported summary types and generate text accordingly

def summary_transform(*, item_id: str, raw: bytes, ctx: dict, **_) -> None:
    """ Adds basic info for the summary box into ctx; returns *nothing* """
    ctx["summary_text"] = f"File: {item_id} | Size: {len(raw)//1024} KB"
    # TODO: extend for more than one file or call it for each file in a list

# -- raw‑bytes‑>RGB ndarray transform ---------------------------------------

# TODO: move file buffer reading functions to another file and simplify them for different input formats
    # may end up implementing concrete transforms subclasses and this could be one of them

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
        # resume index from the session manager by default or start from the beginning if its log is empty
        self._idx = max(-1, self.session.get_last_index() - 1)
        #? NOTE: didn't slice self._ids since the self._idx is based on the original self._ids list and this shows the right progress in title
        self._cache: Dict[str, LoadResult] = {}
        self._max_cache = max_cache

    #~ IDEA: consider implementing a double-ended __iter__ method to allow iterating both forwards and backwards for the undo functionality

    def _insert_cache(self, lr: LoadResult):
        """ Naive LRU caching - purge first inserted if over self._max_cache limit """
        if len(self._cache) >= self._max_cache:
            self._cache.pop(next(iter(self._cache)))
        self._cache[lr.item_id] = lr

    def get_current(self) -> LoadResult:
        item_id = self._ids[self._idx]
        if item_id not in self._cache:
            lr = self.pre_loader.load(item_id)
            self._insert_cache(lr)
        return self._cache[item_id]

    #--------------- public methods for iterating through items and managing the cache ---------------

    def next(self) -> LoadResult:
        """ advance the pointer to the next item and return its pre-loaded result (cached or newly-loaded) """
        if self._idx >= len(self._ids) - 1:
            return None
        self._idx += 1
        return self.get_current()

    def prev(self) -> LoadResult | None:
        """ decrement pointer backwards if possible (needed for UNDO operation) """
        if self._idx <= 0:
            return None
        self._idx -= 1
        return self.get_current()

    #---------------  public method for applying transformations to the current item ---------------
    def apply_updaters(self, user_event: Dict[str, Any]) -> Union[UpdateResult, None]:
        """ apply post-load transformations to the current item to re-render based on user input
            - essentially the augmentation pipeline for the current item
            :param user_event: a dictionary with user input data, e.g. {'toggle_edge_detection': True}
        """
        if not self.post_loader: # if no post-loader is defined, return None
            return None
        current = self.get_current()
        upd: UpdateResult = self.post_loader.apply(current, user_event)
        # merge new metadata back into cache so future calls see latest state
        current.metadata.update(upd.metadata)
        return upd

    #---------------  public methods for task model interaction and session management ---------------

    def assign_label(self, choice: Any):
        item_id = self._ids[self._idx]
        if self.tasks:
            #? NOTE: `self.tasks.update` supports iterable type `choice` for multi-label support
            self.tasks.update(item_id, choice)
        self.session.record(action="label", item_id=item_id, choice=choice)

    def undo_label(self):
        item_id = self._ids[self._idx]
        if self.tasks:
            self.tasks.undo(item_id)
        self.prev() #& newer addition after rewiring data manager and controllers back together
        self.session.record(action="undo", item_id=item_id)

    def flush(self):
        if self.tasks:
            self.tasks.flush_all()
        self.session.record(action="exit", item_id=None)
        self.session.flush()


    #! TEMPORARY ADDITION: adding this function to retrieve all filenames from the DataSource through the PreLoaderModel
        # eventually this should be moved to more high level controller models for managing axes, image names, and ids if nothing else
    def get_file_list(self) -> List[str]:
        """ Returns the list of files to be reviewed, as enumerated by the pre-loader's data source. """
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


# TODO: add to a new file `__init__.py` in the `models` package to more efficiently import the data manager and its components
# re‑export commonly‑used names so controllers can simply do ```from models.data_manager import DataManager2, RenderAsset```
__all__ = [
    "RenderAsset",
    "LoadResult",
    "UpdateResult",
    "PreLoaderModel",
    "PostLoaderModel",
    "DataManager2",
]