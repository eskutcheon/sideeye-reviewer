from typing import Optional, List, Union
# local imports
from ..types import ViewerLike, DataManagerType
from .base_controller import BaseReviewController


class SlideshowController(BaseReviewController):
    """ Controller for slideshow viewer without labeling/annotation capabilities """
    def __init__(self, data_manager: DataManagerType, view: ViewerLike):
        super().__init__(data_manager, view)
        self.playing_animation = False

    def initialize(self, checkpoint = True):
        super().initialize(checkpoint)
        self.view.setup_gui(self, num_axes = self.data_manager.images_per_batch)
        if self.file_list:
            self._load_image(0)
        self.view.main_loop()

    def on_prev_clicked(self, event=None):
        """ returns to previous image """
        if len(self.file_list) > 0:
            self.current_idx = (self.current_idx - 1) % len(self.file_list)
            self._load_image(self.current_idx)

    def on_next_clicked(self, event=None):
        """ skips to next image """
        if len(self.file_list) > 0:
            self.current_idx = (self.current_idx + 1) % len(self.file_list)
            self._load_image(self.current_idx)

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
        self._stop_requested = True
        if hasattr(self.view, "request_stop"):
            self.view.request_stop()