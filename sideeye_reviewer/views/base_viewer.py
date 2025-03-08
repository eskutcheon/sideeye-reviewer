from typing import Optional, Dict
from numpy import ndarray
import matplotlib.pyplot as plt
# local imports
from .reviewer_button import ReviewerButton
from ..types import ControllerLike
from ..utils.utils import maximize_window

class BaseReviewerView:
    """ contains the common UI building logic and references for reviewer objects """
    def __init__(self, fig_title="Image Reviewer"):
        self.fig_title = fig_title
        self.fig = None
        self.axs = []
        self.canvas_images = []
        self._stop_requested = False
        self.controller: ControllerLike = None  # set when we initialize the UI with setup_gui() called from the controller
        # Buttons stored here
        self.stop_button = None
        self.undo_button = None

    def setup_gui(self, controller: ControllerLike, num_axes=1):
        """ Create the figure, buttons, etc. Wire them to the controller's callback methods """
        self.controller = controller
        plt.ion()
        # create figure, subplots, etc. (like in the old BaseReviewer.create_figure_and_axes())
        self.fig, ax_array = plt.subplots(1, num_axes, figsize=(9, 5), gridspec_kw={'wspace': 0.1})
        self.axs = ax_array if isinstance(ax_array, (list, tuple, ndarray)) else [ax_array]
        for ax in self.axs:
            ax.axis("off")
        self.update_title(self.fig_title)
        maximize_window()
        self.fig.canvas.mpl_connect("close_event", self._on_close)
        # create base buttons (STOP, UNDO) in the new structure, setting their callbacks later
        self._create_base_buttons()

    def _create_base_buttons(self):
        """ Creates STOP and UNDO buttons in the bottom region of the figure. Subclasses add more buttons in separate functions """
        # Positions: [left, bottom, width, height]
        self.undo_button = ReviewerButton.factory(
            fig=self.fig,
            label="UNDO",
            ax_pos=[0.75, 0.025, 0.10, 0.075],
            callback=self.controller.on_undo_clicked
        )
        self.stop_button = ReviewerButton.factory(
            fig=self.fig,
            # TODO: might want to change all instances of "STOP" buttons to "EXIT" for consistency with the viewer
            label="STOP",
            ax_pos=[0.86, 0.025, 0.10, 0.075],
            callback=self.controller.on_stop_clicked
        )

    def _create_label_buttons(self, labels):
        raise NotImplementedError("Subclasses must implement this method to create label buttons")

    def _create_legend(self):
        raise NotImplementedError("Subclasses must implement this method to create a legend")

    def display_image(self, image, ax_idx=0):
        """ show or update an image on self.axs; adjust accordingly for multiple axes """
        # If it's the first time, store the imshow result; otherwise update set_data().
        if len(self.canvas_images) <= ax_idx:
            # first time creation
            aspect_ratio = "auto" if len(self.axs) > 1 else None
            im_obj = self.axs[ax_idx].imshow(image, aspect=aspect_ratio)
            self.canvas_images.append(im_obj)
        else: # else update the existing image
            self.canvas_images[ax_idx].set_data(image)
        self.fig.canvas.draw()

    def update_title(self, text):
        if self.fig:
            self.fig.suptitle(text, fontsize="xx-large", wrap=True)

    def display_warning(self, message="Warning!", duration=3000):
        """ replicates the old 'display_warning()' from base_reviewer.py with purely UI functionality """
        txt = self.fig.text(0.5, 0.3, message, ha='center', va='center', fontsize=18, color='red', backgroundcolor='#263037')
        self.fig.canvas.draw()
        def remove_text():
            try:
                txt.set_visible(False)
                self.fig.canvas.draw()
            except ValueError:
                pass
        # create a timer that will remove the text after `duration` milliseconds
        timer = self.fig.canvas.new_timer(interval=duration)
        timer.add_callback(remove_text)
        timer.start()

    def main_loop(self):
        """ Main loop: keep going until STOP is triggered. The controller can call this,
            but the loop logic itself is the same: keep calling plt.pause() until stopped.
        """
        while not self._stop_requested and plt.fignum_exists(self.fig.number):
            plt.pause(0.05) # short pause to handle events
        # Once we break from the loop, close the figure if it still exists
        self.request_stop()

    def request_stop(self):
        """ used by the controller to tell the view to close everything """
        self._stop_requested = True
        if plt.fignum_exists(self.fig.number):
            plt.close(self.fig)

    def _on_close(self, event):
        # if user forcibly closes the window, notify the controller for cleanup actions
        plt.ioff()
        #if not self._stop_requested and self.controller:
        if self.controller:
            self.controller.on_window_closed()

