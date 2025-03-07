from typing import List, Optional, Union
# local imports
from ..types import ViewerLike, DataManagerType


class BaseReviewController:
    """ base controller class holding common logic:
        - Storing sorter & view
        - Getting the file list
        - Loading images by index
        - Handling window close
        Subclasses should override or extend with domain-specific callbacks (label assignment, or slideshow controls)
    """
    #def __init__(self, sorter: ImageSorterType, view: ViewerLike):
    def __init__(self, data_manager: DataManagerType, view: ViewerLike):
        """
            :param sorter: e.g. an ImageSorter instance
            :param view:   either a reviewer-type view or a results viewer-type view
        """
        # TODO: should be giving this a more general data manager object of some sort
        self.data_manager = data_manager
        self.view = view
        self.file_list: List[str] = []
        self.num_files = 0
        self.current_idx: int = 0
        self._stop_requested = False

    def initialize(self, checkpoint: Union[bool, int] = True):
        """ called in subclasses to set up the file list from the sorter, then call the view setup """
        # get the list of files from the sorter
        self.file_list = self.data_manager.get_file_list(checkpoint)
        self.num_files = len(self.file_list)
        self.current_idx = 0
        labels = self.get_category_labels()

    def get_category_labels(self):
        # TODO: should probably be careful with this kind of indirect access and return a copy
        return self.data_manager.labels

    def _load_image(self, idx: int):
        """ common method to load the file at 'idx' from disk via the sorter and pass it to the view for display """
        if not self.file_list or idx >= len(self.file_list):
            return
        filename = self.file_list[idx]
        # get a list of full paths for the current filename under all available image folders in the manager
        # FIXME: will be moving this logic to the data manager
        imgs = self.data_manager.load_images(filename)
        for i, img in enumerate(imgs):
            self.view.display_image(img, ax_idx=i)
        # if view has a title or progress info:
        print_idx = self.num_files + idx + 1 if idx < 0 else idx + 1
        self.view.update_title(f"{self.view.fig_title}\n{filename}\nProgress: {print_idx}/{len(self.file_list)}")


    def on_window_closed(self):
        """ if the user forcibly closes the window, do a final stop if not already set """
        if not self._stop_requested:
            print("[CONTROLLER] Window closed: stopping review...")
            self._stop_requested = True
            if hasattr(self.view, "request_stop"):
                self.view.request_stop()
            # Subclasses might do extra logic, e.g. writing bin_manager outfiles or stopping animation.
