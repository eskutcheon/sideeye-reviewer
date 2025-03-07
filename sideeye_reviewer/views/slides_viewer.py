from typing import Optional, Dict
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from numpy import ndarray
# local imports
from ..utils.utils import maximize_window
from ..types import ControllerLike
from .reviewer_button import ReviewerButton



class SlideshowViewerView:
    """ replaces the old SortResultsViewer for read-only playback with optional auto-play """
    def __init__(self, fig_title="Slideshow Viewer", slide_duration=2.5):
        self.fig_title = fig_title
        self.slide_duration = slide_duration # seconds per frame when playing the animation
        self.fig = None
        self.axes = []
        self.img_display = []
        self.controller = None
        self.playing_animation = False
        self.animator = None

    def setup_gui(self, controller: ControllerLike, num_axes=1):
        """ create figure, subplots, set up next/prev buttons, start/stop animation, etc. """
        self.controller = controller
        plt.ion()
        self.fig, self.axes = plt.subplots(1, num_axes, figsize=(10, 5))
        # TODO: still think this should be relegated to a helper function
        if not isinstance(self.axes, (list, tuple, ndarray)):
            self.axes = [self.axes]
        for ax in self.axes:
            ax.axis("off")
        #! TODO: add initial image display logic - now done by the new data manager
        self.update_title(self.fig_title)
        maximize_window()
        # Positions: [left, bottom, width, height]
        self.fig.tight_layout(rect=[0, 0.1, 1, 1])
        self.fig.canvas.mpl_connect("close_event", self._on_close)
        self._create_buttons()
        self._init_animator()

    def _create_buttons(self):
        # TODO: replace callbacks with the new controller's methods
        self.buttons = {
            "prev": ReviewerButton.factory(
                self.fig,
                label="PREV",
                ax_pos=[0.41, 0.025, 0.1, 0.075],
                callback=self.controller.on_prev_clicked),
            "next": ReviewerButton.factory(
                self.fig,
                label="NEXT",
                ax_pos=[0.52, 0.025, 0.1, 0.075],
                callback=self.controller.on_next_clicked),
            "start": ReviewerButton.factory(
                self.fig,
                label="START",
                ax_pos=[0.63, 0.025, 0.1, 0.075],
                callback=self.controller.on_start_clicked),
            "stop": ReviewerButton.factory(
                self.fig,
                label="STOP",
                ax_pos=[0.74, 0.025, 0.1, 0.075],
                callback=self.controller.on_stop_clicked),
            "exit": ReviewerButton.factory(
                self.fig,
                label="EXIT",
                ax_pos=[0.85, 0.025, 0.1, 0.075],
                callback=self.controller.on_exit_clicked)
        }

    def _init_animator(self):
        self.animator = FuncAnimation(self.fig, self._update_frame, interval=self.slide_duration * 1000, repeat=True, cache_frame_data=False) #blit=False)
        # manually start/stop it by toggling self.playing_animation
        self.playing_animation = False

    def _update_frame(self, frame):
        # updates the frame if currently playing the slideshow
        if self.playing_animation:
            #self.curr_idx = (self.curr_idx + 1) % self.num_reviewed
            #self.update_display(self.curr_idx)
            self.controller.on_next_clicked(event=None)

    def update_display(self, index):
        self.fig.canvas.draw()

    def display_image(self, image, ax_idx=0):
        """ displays or updates the image in the given axis """
        if ax_idx >= len(self.img_display):
            disp = self.axes[ax_idx].imshow(image)
            #self.axes[ax_idx].axis("off")
            self.img_display.append(disp)
        else:
            self.img_display[ax_idx].set_data(image)
        self.fig.canvas.draw()


    def update_title(self, text: str):
        # sets the suptitle
        self.fig.suptitle(
            #f"{self.fig_title}\n{self.file_list[self.curr_idx]}\nProgress: {self.curr_idx + 1}/{self.num_reviewed}",
            text,
            fontsize="xx-large",
            wrap=True
        )

    def start_animation(self):
        """Sets playing to True so _update_frame cycles images."""
        self.playing_animation = True

    def stop_animation(self):
        """Sets playing to False."""
        self.playing_animation = False

    def request_stop(self):
        """ closes the figure if it still exists and ends the loop """
        if plt.fignum_exists(self.fig.number):
            plt.close(self.fig)

    def main_loop(self):
        # or the animation approach from viewer.py
        #plt.show()
        """ Main loop: keep going until STOP is triggered. The controller can call this,
            but the loop logic itself is the same: keep calling plt.pause() until stopped.
        """
        while plt.fignum_exists(self.fig.number):
            plt.pause(0.05) # short pause to handle events
        # Once we break from the loop, close the figure if it still exists
        self.request_stop()

    def _on_close(self, event):
        # if user forcibly closes the window, notify the controller for cleanup actions
        plt.ioff()
        #if not self._stop_requested and self.controller:
        if self.controller:
            self.controller.on_window_closed()