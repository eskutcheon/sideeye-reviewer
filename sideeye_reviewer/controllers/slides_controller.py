# local imports
from ..types import ViewerLike, DataManagerType
from .base_controller import BaseReviewController


class SlideshowController(BaseReviewController):
    """ Controller for slideshow viewer without labeling/annotation capabilities """
    def __init__(self, data_manager: DataManagerType, view: ViewerLike):
        super().__init__(data_manager, view)
        self.playing_animation = False

    def initialize(self, checkpoint = True):
        # super().initialize(checkpoint) #& UPDATE: new data manager setup doesn't use the superclass method anymore
        #! FIXME (HARDCODING): the number of images to display needs to handled differently from now on
        self.view.setup_gui(self, num_axes = self.images_per_fig) #self.data_manager.images_per_batch)
        first = self.data_manager.next()
        if first:
            self._render(first)
        self.view.main_loop()

    def on_prev_clicked(self, event=None):
        """ returns to previous image """
        # TODO: determine whether to preserve the circular navigation with the new data manager setup
            # i.e. where `self.current_idx = (self.current_idx - 1) % len(self.file_list)` can go from image 1 to the final image
        lr = self.data_manager.prev()
        if lr:
            self._render(lr)

    def on_next_clicked(self, event=None):
        """ skips to next image """
        # TODO: determine whether to preserve the circular navigation with the new data manager setup
            # i.e. where `self.current_idx = (self.current_idx + 1) % len(self.file_list)` can go from the final image to image 1
        lr = self.data_manager.next()
        if lr:
            self._render(lr)

    def on_start_clicked(self, event=None):
        """ start auto-play for slideshow """
        self.playing_animation = True
        if hasattr(self.view, "start_animation"):
            self.view.start_animation()

    def on_stop_clicked(self, event=None):
        """ stop auto-play for slideshow """
        self.playing_animation = False
        if hasattr(self.view, "stop_animation"):
            self.view.stop_animation()

    def on_exit_clicked(self, event=None):
        """ exit viewer and close the window """
        #& UPDATE: using new data manager where `close_requested` calls all task models to write their results and perform cleanup
        self.close_requested()