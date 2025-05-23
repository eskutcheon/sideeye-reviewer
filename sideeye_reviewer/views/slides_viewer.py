from typing import Optional, Dict
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
# local imports
from .base_viewer import BaseReviewerView
from .reviewer_button import ReviewerButton
from ..types import ControllerLike


class SlideshowViewerView(BaseReviewerView):
    """ Viewer for simple slideshow playback with navigation and animation, built on new BaseReviewerView layout """
    def __init__(self, fig_title="Slideshow Viewer", legend_dict = None, slide_duration=2.5):
        super().__init__(fig_title)
        self.legend_dict = legend_dict  # optional legend dictionary for future use
        self.slide_duration = slide_duration
        self.animator = None
        self.playing_animation = False
        self.buttons = {}  # dictionary to hold button references

    def setup_gui(self, controller: ControllerLike, num_axes=1):
        """ initialize layout and GUI components with read-only behavior and no checkbox/labeling """
        self.controller = controller
        super().setup_gui(
            controller,
            num_axes = num_axes,
            num_buttons = 5,  # NEXT, PREV, START, STOP, EXIT
            use_legend = self.legend_dict is not None,
            use_summary = False,
            use_checkboxes = False
        )
        self._create_slideshow_buttons()
        self._init_animator()
        self.fig.tight_layout()

    def _create_slideshow_buttons(self):
        """ instantiate buttons for PREV, NEXT, START, STOP, EXIT """
        btn_axes_data = self.layout.get_button_axes()
        label_callbacks = [
            ("PREV", self.controller.on_prev_clicked),
            ("NEXT", self.controller.on_next_clicked),
            ("START", self.controller.on_start_clicked),
            ("STOP", self.controller.on_stop_clicked),
            ("EXIT", self.controller.on_exit_clicked),
        ]
        for i, (label, cb) in enumerate(label_callbacks):
            if i >= len(btn_axes_data):
                raise ValueError(f"Not enough button axes available for {len(label_callbacks)} buttons.")
                #break  # fallback safety
            btn_ax = btn_axes_data[-(i+1)].axes
            self.buttons[label.lower()] = ReviewerButton.factory(
                btn_ax,
                label=label,
                ax_pos=btn_ax.get_position().bounds,
                callback=cb
            )
            self.buttons_assigned[-(i+1)] = True

    def _init_animator(self):
        self.animator = FuncAnimation(
            self.fig,
            self._update_frame,
            interval=self.slide_duration * 1000,
            repeat=True,
            cache_frame_data=False
        )
        # manually start/stop it by toggling self.playing_animation
        self.playing_animation = False

    def _update_frame(self, frame):
        # updates the frame if currently playing the slideshow
        if self.playing_animation:
            self.controller.on_next_clicked()

    def start_animation(self):
        self.playing_animation = True

    def stop_animation(self):
        self.playing_animation = False

    def request_stop(self):
        self._stop_requested = True
        super().request_stop()

    def main_loop(self):
        """ keep UI responsive while slideshow is active with plt.pause calls """
        while not self._stop_requested and self.fig.number in plt.get_fignums():
            plt.pause(0.05)
        # once we break from the loop, close the figure if it still exists
        self.request_stop()

    def _on_close(self, event):
        # if user forcibly closes the window, notify the controller for cleanup actions
        plt.ioff()
        #if not self._stop_requested and self.controller:
        if self.controller:
            self.controller.on_window_closed()
