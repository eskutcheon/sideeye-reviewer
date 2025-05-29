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
        # self.file_list: List[str] = []
        # self.num_files = 0
        # self.current_idx: int = 0
        self._stop_requested = False

    def initialize(self, checkpoint: Union[bool, int] = True):
        """ called in subclasses to set up the file list from the sorter, then call the view setup """
        # get the list of files (possibly sliced by the checkpoint if given)
        self.file_list = self.data_manager.get_file_list(checkpoint)
        self.num_files = len(self.file_list)
        #self.current_idx = 0

    def get_category_labels(self):
        try:
            return self.data_manager.tasks.get_category_labels() #.labels
        except (AttributeError, IndexError):
            print("[CONTROLLER] No task models found or no labels available.")
            #! FIXCHANGE - don't intend to keep it this way, but I need to debug it all first
            return []

    # def _load_image(self, idx: int):
    #     """ common method to load the file at 'idx' from disk via the sorter and pass it to the view for display """
    #     if not self.file_list or idx >= len(self.file_list):
    #         return
    #     filename = self.file_list[idx]
    #     # get a list of full paths for the current filename under all available image folders in the manager
    #     # FIXME: will be moving this logic to the data manager later
    #     # TODO: rewrite this to use iterators like the new data manager intended - mostly through `next` and `prev` to step backward or forward
    #     #imgs = self.data_manager.load_images(filename)
    #     load_results = self.data_manager.next()
    #     #         paths = self.get_image_paths(filename)
    #     #         images = []
    #     #         for p in paths:
    #     #             img = plt.imread(p)
    #     #             # for fn in self.transform_pipeline:
    #     #             #     img = fn(img)
    #     #             images.append(img)
    #     #         return images
    #     for i, img in enumerate(imgs):
    #         self.view.display_image(img, ax_idx=i)
    #     # if view has a title or progress info:
    #     print_idx = self.num_files + idx + 1 if idx < 0 else idx + 1
    #     self.view.update_title(f"{self.view.fig_title}", f"{filename}\nProgress: {print_idx}/{len(self.file_list)}")
    #     # TODO: add logic to retrieve data for the summary box if applicable - using_summary should now be passed to the viewer constructor
    #     # self.view.update_summary(...)
    #     if self.use_summary:
    #         summary_text = self.data_manager.generate_summary_text()
    #         self.view.update_summary(summary_text)


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
        for asset in lr.assets: # iterate over RenderAsset objects
            if asset.kind == "image" and hasattr(self.view, "display_image"):
                self.view.display_image(asset.payload, ax_idx=asset.target_axes)
            elif asset.kind == "plot" and hasattr(self.view, "display_plot"):
                #! FIXME: not yet implemented - may need to be reassessed entirely since I'll still need to either
                    # 1. pass an axes object all the way to the `PostLoaderModel` to be used as a transforms argument OR
                    # 2. adopt a builder pattern that sets up all steps to perform as a callable to be applied
                        # in the controller or data manager after retrieving the axes
                self.view.display_plot(asset.payload, ax_idx=asset.target_axes)
        # titles / summary
        progress = f"{int(self.data_manager.current_idx) + 1}/{self.data_manager.total}"
        if hasattr(self.view, "update_title"):
            self.view.update_title(self.view.fig_title, f"{lr.item_id}\nProgress: {progress}")
        if self.use_summary and "summary_text" in lr.metadata and hasattr(self.view, "update_summary"):
            self.view.update_summary(lr.metadata["summary_text"])