from typing import List, Optional, Union
# local imports
from ..types import ViewerLike, DataManagerType
from ..models.data_manager import LoadResult


# TODO: planning on writing a larger config dataclass to hold all the parameters for the reviewer session, esp. the flags like `use_summary`


class BaseReviewController:
    """ base controller class holding common logic:
        - Storing sorter & view
        - Getting the file list
        - Loading images by index
        - Handling window close
        Subclasses should override or extend with domain-specific callbacks (label assignment, or slideshow controls)
    """
    def __init__(self, data_manager: DataManagerType, view: ViewerLike):
        """
            :param data_manager: DataManager instance
            :param view:   either a reviewer-type view or a results viewer-type view
        """
        self.data_manager = data_manager
        self.view = view
        # retrieve whether to use a summary box from the data manager
        #self.use_summary = self.data_manager.summary_type is not None
        #! TEMPORARY HARDCODE - REMOVE LATER:
        self.use_summary = False # will be replaced with CLI config option in the future
        # TODO: images per batch should soon be determined by session configuration and no longer handled by the data manager
        #! TEMPORARY HARDCODE - REMOVE LATER:
        self.images_per_fig = 2 #self.data_manager.images_per_batch
        self._stop_requested = False

    def initialize(self, checkpoint: Union[bool, int] = True):
        """ called in subclasses to set up the file list from the sorter, then call the view setup """
        # get the list of files (possibly sliced by the checkpoint if given)
        # self.file_list = self.data_manager.get_file_list(checkpoint) #! DEPRECATED - no longer takes a checkpoint - in the process of rewriting this now
        # self.num_files = len(self.file_list)
        raise NotImplementedError("Subclasses should implement the initialize method to set up the view and load the first item.")

    def get_category_labels(self):
        try:
            return self.data_manager.tasks.get_category_labels() #.labels
        except (AttributeError, IndexError):
            print("[CONTROLLER] No task models found or no labels available.")
            #! FIXCHANGE - don't intend to keep it this way, but I need to debug it all first
            return []


    def on_window_closed(self):
        """ if the user forcibly closes the window, do a final stop if not already set """
        if not self._stop_requested:
            print("[CONTROLLER] Window closed: stopping review...")
            self._stop_requested = True
            if hasattr(self.view, "request_stop"):
                self.view.request_stop()
            # Subclasses might do extra logic, e.g. writing bin_manager outfiles or stopping animation.

    def close_requested(self):
        self.data_manager.flush()
        if hasattr(self.view, "request_stop"):
            self.view.request_stop()

    def _render(self, lr: LoadResult):
        """ draw all assets in the load results onto the view """
        print("[DEBUGGING] CHECKING IF `assets` IS EMPTY: ", lr.assets)
        for asset in lr.assets: # iterate over RenderAsset objects
            if asset.kind == "image" and hasattr(self.view, "display_image"):
                print("[DEBUGGING] asset.payload: ", asset.payload)
                self.view.display_image(asset.payload, ax_idx=asset.target_axes)
            elif asset.kind == "plot" and hasattr(self.view, "display_plot"):
                #! FIXME: not yet implemented - may need to be reassessed entirely since I'll still need to either
                    # 1. pass an axes object all the way to the `PostLoaderModel` to be used as a transforms argument OR
                    # 2. adopt a builder pattern that sets up all steps to perform as a callable to be applied
                        # in the controller or data manager after retrieving the axes
                self.view.display_plot(asset.payload, ax_idx=asset.target_axes)
            elif asset.kind == "callable":
                pass
            else:
                print("[DEBUGGING] Checking asset kind: ", asset.kind)
                print("[DEBUGGING] Asset payload: ", asset.payload)
        # titles / summary
        progress = f"{int(self.data_manager.current_idx) + 1}/{self.data_manager.total}"
        if hasattr(self.view, "update_title"):
            self.view.update_title(self.view.fig_title, f"{lr.item_id}\nProgress: {progress}")
        if self.use_summary and "summary_text" in lr.metadata and hasattr(self.view, "update_summary"):
            self.view.update_summary(lr.metadata["summary_text"])