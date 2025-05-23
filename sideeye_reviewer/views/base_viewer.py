from typing import Optional, Dict, List
import matplotlib.pyplot as plt
# local imports
from .reviewer_button import ReviewerButton
from ..types import ControllerLike
from ..utils.utils import maximize_window
from ..layouts.layout_manager import FigureLayoutManager


"""
    - The new summary window should be set in the views like before with the associated callback from the
        controller, which accesses the data_manager and a new method for computing statistics, etc
    - for example:
        - suppose that we're reviewing semantic segmentation results and we want to simply list metrics (accuracy, precision, etc)
            on the right (in the new summary box); the data manager would have a method to load or compute this
        - suppose that we're reviewing object detection results with bounding box overlays and we want to list
            the box IoUs of each pair of object classes
"""


class BaseReviewerView:
    """ contains the common UI building logic and references for reviewer objects """
    def __init__(self, fig_title="Image Reviewer"):
        self.fig_title = fig_title
        self.fig = None
        self.layout = None  # FigureLayoutManager instance
        self.canvas_images = []
        self._stop_requested = False
        self.controller: ControllerLike = None  # set when we initialize the UI with setup_gui() called from the controller
        #! TEMP: setting to False unconditionally until it's integrated into the controller
        self.use_summary = False
        self.buttons_assigned = None # set after creation of the layout manager to index button positions
        #? NOTE: needed to avoid repeatedly overlaying text on the same position in the figure after the timer is added
        #self.subtitle_pos = (0.5, 0.95)  # default position for the subtitle text in the figure
        self.subtitle: plt.Text = None  # used to store the subtitle text object for updating
        self.warning_text: plt.Text = None  # used to store the warning text object for updating without continually creating new text objects
        self.summary_text: plt.Text = None  # used to store the summary text object for updating without continually creating new text objects
        # Buttons stored here - need to keep a reference to them for callback persistence regardless if they're ever used directly
        self.exit_button = None # formerly `self.stop_button`
        self.undo_button = None

    def setup_gui(
        self,
        controller: ControllerLike,
        num_axes: int = 1,
        num_buttons: int = 2,
        use_legend: bool = True,
        #! TEMP: setting to true unconditionally until it's integrated into the controller
        use_summary: bool = True,
        use_checkboxes: bool = False
    ):
        """ Create the figure, buttons, etc. Wire them to the controller's callback methods """
        self.controller = controller
        self.images_per_fig = self.controller.images_per_fig
        labels = self.controller.get_category_labels() if use_checkboxes else None
        self.use_summary = use_summary
        self.generate_layout(
            num_axes = num_axes,
            num_buttons = num_buttons,
            labels = labels,
            use_legend = use_legend,
            use_summary = use_summary,
            use_checkboxes = use_checkboxes
        )
        self.fig = self.layout.fig
        plt.ion()
        self.update_title(self.fig_title)
        maximize_window() # might need to come before plt.show
        # hook UI events for closing the figure to a cleanup function
        self.fig.canvas.mpl_connect("close_event", self._on_close)

    def generate_layout(self, num_axes: int = 1, num_buttons: int = 2, labels: List[str] = None, use_legend: bool = True, use_summary: bool = False, use_checkboxes: bool = False):
        """ Generate the layout for the figure, subplots, etc. """
        assert num_axes > 0, "Number of image axes must be greater than 0"
        self.layout = FigureLayoutManager(
            num_images = num_axes,
            num_buttons = num_buttons,
            labels = labels,
            use_legend = use_legend,
            use_summary = use_summary,
            use_checkboxes = use_checkboxes
        )
        self.layout.create_figure_layout()
        self.buttons_assigned = [False] * len(self.layout.get_button_axes())

    # TODO: feel like this should be added to the layout manager instead of here - could just pass the controller callbacks in a list
        # It does call into question the use of a new AxesManager like I wrote about here and there
    def _create_base_buttons(self):
        """ Creates EXIT and UNDO buttons in the bottom region of the figure. Subclasses add more buttons in separate functions """
        #? NOTE: these are returned in reverse order so that the rightmost button is at index 0
        btn_axes = self.layout.get_button_axes()
        exit_ax = btn_axes[0].axes # formerly `stop_ax`
        undo_ax = btn_axes[1].axes
        self.buttons_assigned[:2] = [True, True]  # mark the last two button positions (since they're added right to left) as assigned
        # Positions: [left, bottom, width, height]
        self.undo_button = ReviewerButton.factory(
            undo_ax,
            label = "UNDO",
            ax_pos = undo_ax.get_position().bounds,
            callback = self.controller.on_undo_clicked
        )
        self.exit_button = ReviewerButton.factory( # formerly `self.stop_button`
            exit_ax,
            label = "EXIT", # formerly labeled "STOP"
            ax_pos = exit_ax.get_position().bounds,
            callback = self.controller.on_exit_clicked
        )

    def _create_label_buttons(self, labels):
        raise NotImplementedError("Subclasses must implement this method to create label buttons")


    def _create_legend(self, legend_dict: Dict[str, str] = None):
        # bottom left corner to place the legend
        if legend_dict:
            panel_bbox = list(self.layout.get_panel_position("bottom_left"))
            # TODO: update this adjustment to be set dynamically based on the difference of the panel bbox and legend bbox
            #panel_bbox[0] += 0.01  # move the legend slightly to the right
            legend_kwargs = {
                "loc": "center",
                "bbox_to_anchor": panel_bbox,
                #"bbox_to_anchor": self.layout.get_axes("bottom_left", "legend").get_position().bounds,
                "fontsize": "x-large",
            }
            for label, color in legend_dict.items():
                plt.plot([], [], color=color, label=label, linewidth=6, alpha=0.4)
            self.fig.legend(**legend_kwargs)

    def display_image(self, image, ax_idx=0):
        """ show or update an image on self.axs; adjust accordingly for multiple axes """
        # if it's the first call, store the imshow result; otherwise update set_data().
        ax = self.layout.get_image_subaxes(ax_idx).axes
        if len(self.canvas_images) > ax_idx:
            self.canvas_images[ax_idx].set_data(image)
        else:
            # if the viewer is only displaying one image, don't set the aspect ratio to "auto" since it will be stretched
            aspect_ratio = "auto" if self.images_per_fig > 1 else None
            img_obj = ax.imshow(image, aspect=aspect_ratio)
            self.canvas_images.append(img_obj)
        self.fig.canvas.draw_idle()  # Update without forcing new figures

    def update_title(self, text, subtitle = None):
        if self.warning_text is not None:
            self.warning_text.set_visible(False)
        if self.fig:
            self.fig.suptitle(text, fontsize=24, fontweight="bold", wrap=True)
            if subtitle:
                self.update_subtitle(subtitle)  # update the subtitle if provided
            self.fig.canvas.draw_idle()

    def update_subtitle(self, text):
        """ updates the subtitle text in the figure """
        if self.fig:
            if self.subtitle is not None:
                # remove the previous subtitle if it exists
                self.subtitle.set_text(text)
            else:
                # create a new subtitle text object if it doesn't exist
                self.subtitle = plt.figtext(0.5, 0.95, text, ha='center', va='top', fontsize=18)

    #~ UPDATE: new summary axis with random extra stuff queued by the data manager
    def update_summary(self, text):
        """ updates the summary box with new text """
        if self.use_summary:
            if self.summary_text is not None:
                self.summary_text.set_text(text)
            else:
                # FIXME: may not be using this long term - should work for now
                summary_ax = self.layout.get_axes("left", "summary")
                if summary_ax:
                    self.summary_text = summary_ax.text(0.5, 0.5, text, wrap=True, ha="center", va="center", fontsize="large")
            self.fig.canvas.draw_idle()  # Update without forcing new figures

    def display_warning(self, message="Warning!", duration=2500):
        """ replicates the old 'display_warning()' from base_reviewer.py with purely UI functionality """
        if self.warning_text is None:
            self.warning_text = self.fig.text(0.5, 0.3, message, ha='center', va='center', fontsize=18, color='red', backgroundcolor='#263037')
        else:
            self.warning_text.set_text(message)
            self.warning_text.set_visible(True)  # make sure the text is visible
        self.fig.canvas.draw()
        def remove_text():
            try:
                self.warning_text.set_visible(False)
                self.fig.canvas.draw_idle()  # Update without forcing new figures
            except ValueError:
                pass
        # create a timer that will remove the text after `duration` milliseconds
        timer = self.fig.canvas.new_timer(interval=duration)
        timer.add_callback(remove_text)
        timer.start()

    def main_loop(self):
        """ Main loop: keep going until EXIT is triggered. The controller can call this,
            but the loop logic itself is the same: keep calling plt.pause() until stopped.
        """
        try:
            while not self._stop_requested and plt.fignum_exists(self.fig.number):
                plt.pause(0.05) # short pause to handle events
        except KeyboardInterrupt:
            # if the user interrupts the loop, we can handle it here
            print("[VIEWER] Keyboard interrupt detected. Stopping review...")
        # once we break from the loop, close the figure if it still exists
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

