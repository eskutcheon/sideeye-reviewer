
from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import List, Dict, Any





class TaskModel(ABC):
    """ A plug-in that handles and utilizes user outcomes (sorting, scoring, …) """
    @abstractmethod
    def update(self, item_id: str, user_choice: Any) -> None: ...

    def undo(self, item_id: str) -> None:  ...  # default no‑ops

    def flush(self) -> None: ...                # default no‑op


class BinSortingTask(TaskModel):
    """ wraps the existing BinManager (models/bin_manager.py) deque-based binning logic """

    def __init__(self, labels: List[str], out_dir: str, outfile: str = "sorting_output.json"):
        from .bin_manager import BinManager  # local import avoids circular ref
        self._bm = BinManager(labels=labels, out_dir=out_dir, outfile_name=outfile)

    # next 3 methods follow TaskModel API
    def update(self, item_id: str, user_choice: Any):
        self._bm.set_current_image(item_id)
        self._bm.update_bin(user_choice)

    def undo(self, item_id: str):
        self._bm.set_current_image(item_id)
        self._bm.update_bin(labels=None, remove=True)

    def flush(self):
        self._bm.write_to_outfiles()

    # extra helper for checkpointing
    def get_num_sorted(self) -> int:
        return self._bm.get_num_sorted()

    def get_category_labels(self) -> List[str]:
        """ returns the list of labels for the binning task """
        return self._bm.labels


class TaskOrchestrator:
    """ optional convenience wrapper to broadcast calls to many TaskModels - to be used by the controller
        to better separate concerns from the data manager
    """
    def __init__(self, *task_models: TaskModel):
        self._models = list(task_models)

    def update(self, item_id: str, user_choice: Any):
        for m in self._models:
            m.update(item_id, user_choice)

    def undo(self, item_id: str):
        for m in self._models:
            m.undo(item_id)

    def flush_all(self):
        for m in self._models:
            m.flush()

    def get_category_labels(self) -> List[str]:
        """ returns the union of all category labels from all task models """
        labels = set()
        #! only exists for BinSortingTask for now, but can be extended to other task models
        for m in self._models:
            if hasattr(m, "get_category_labels") and callable(m.get_category_labels):
                labels.update(m.get_category_labels())
        return list(labels)