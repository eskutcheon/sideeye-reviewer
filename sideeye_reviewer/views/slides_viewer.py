from typing import Optional, Dict
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from numpy import ndarray
# local imports
from .base_viewer import BaseReviewerView
from .reviewer_button import ReviewerButton
from ..utils.utils import maximize_window
from ..types import ControllerLike



# class SlideshowViewerView: #(BaseReviewerView):
#     """ replaces the old SortResultsViewer for read-only playback with optional auto-play """
#     def __init__(self, fig_title="Slideshow Viewer", slide_duration=2.5): # legend_dict=None,
#         self.fig_title = fig_title
#         self.slide_duration = slide_duration # seconds per frame when playing the animation
#         self.fig = None # self.fig is now self.layout.fig
#         self.axes = []
#         self.img_display = []
#         self.controller = None
#         self.playing_animation = False
#         self.animator = None

#     def setup_gui(self, controller: ControllerLike, num_axes=1):
#         """ create figure, subplots, set up next/prev buttons, start/stop animation, etc. """
#         self.controller = controller
#         plt.ion()
#         self.fig, self.axes = plt.subplots(1, num_axes, figsize=(10, 5))
#         # TODO: still think this should be relegated to a helper function
#         if not isinstance(self.axes, (list, tuple, ndarray)):
#             self.axes = [self.axes]
#         for ax in self.axes:
#             ax.axis("off")
#         self.update_title(self.fig_title)
#         maximize_window()
#         # Positions: [left, bottom, width, height]
#         self.fig.tight_layout(rect=[0, 0.1, 1, 1])
#         self.fig.canvas.mpl_connect("close_event", self._on_close)
#         self._create_buttons()
#         self._init_animator()

#     def _create_buttons(self):
#         # TODO: replace callbacks with the new controller's methods
#         self.buttons = {
#             "prev": ReviewerButton.factory(
#                 self.fig,
#                 label="PREV",
#                 ax_pos=[0.41, 0.025, 0.1, 0.075],
#                 callback=self.controller.on_prev_clicked),
#             "next": ReviewerButton.factory(
#                 self.fig,
#                 label="NEXT",
#                 ax_pos=[0.52, 0.025, 0.1, 0.075],
#                 callback=self.controller.on_next_clicked),
#             "start": ReviewerButton.factory(
#                 self.fig,
#                 label="START",
#                 ax_pos=[0.63, 0.025, 0.1, 0.075],
#                 callback=self.controller.on_start_clicked),
#             "stop": ReviewerButton.factory(
#                 self.fig,
#                 label="STOP",
#                 ax_pos=[0.74, 0.025, 0.1, 0.075],
#                 callback=self.controller.on_stop_clicked),
#             "exit": ReviewerButton.factory(
#                 self.fig,
#                 label="EXIT",
#                 ax_pos=[0.85, 0.025, 0.1, 0.075],
#                 callback=self.controller.on_exit_clicked)
#         }

#     def _init_animator(self):
#         self.animator = FuncAnimation(self.fig, self._update_frame, interval=self.slide_duration * 1000, repeat=True, cache_frame_data=False) #blit=False)
#         # manually start/stop it by toggling self.playing_animation
#         self.playing_animation = False

#     def _update_frame(self, frame):
#         # updates the frame if currently playing the slideshow
#         if self.playing_animation:
#             #self.curr_idx = (self.curr_idx + 1) % self.num_reviewed
#             #self.update_display(self.curr_idx)
#             self.controller.on_next_clicked(event=None)

#     def update_display(self, index):
#         self.fig.canvas.draw()

#     def display_image(self, image, ax_idx=0):
#         """ displays or updates the image in the given axis """
#         if ax_idx >= len(self.img_display):
#             disp = self.axes[ax_idx].imshow(image)
#             #self.axes[ax_idx].axis("off")
#             self.img_display.append(disp)
#         else:
#             self.img_display[ax_idx].set_data(image)
#         self.fig.canvas.draw()


#     def update_title(self, text: str):
#         # sets the suptitle
#         self.fig.suptitle(
#             #f"{self.fig_title}\n{self.file_list[self.curr_idx]}\nProgress: {self.curr_idx + 1}/{self.num_reviewed}",
#             text,
#             fontsize="xx-large",
#             wrap=True
#         )

#     def start_animation(self):
#         """Sets playing to True so _update_frame cycles images."""
#         self.playing_animation = True

#     def stop_animation(self):
#         """Sets playing to False."""
#         self.playing_animation = False

#     def request_stop(self):
#         """ closes the figure if it still exists and ends the loop """
#         if plt.fignum_exists(self.fig.number):
#             plt.close(self.fig)

#     def main_loop(self):
#         # or the animation approach from viewer.py
#         #plt.show()
#         """ Main loop: keep going until STOP is triggered. The controller can call this,
#             but the loop logic itself is the same: keep calling plt.pause() until stopped.
#         """
#         while plt.fignum_exists(self.fig.number):
#             plt.pause(0.05) # short pause to handle events
#         # Once we break from the loop, close the figure if it still exists
#         self.request_stop()

#     def _on_close(self, event):
#         # if user forcibly closes the window, notify the controller for cleanup actions
#         plt.ioff()
#         #if not self._stop_requested and self.controller:
#         if self.controller:
#             self.controller.on_window_closed()



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
