from typing import Optional, Dict, List
from numpy import ndarray
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
        ###self.axs = []
        self.canvas_images = []
        self._stop_requested = False
        self.controller: ControllerLike = None  # set when we initialize the UI with setup_gui() called from the controller
        self.use_summary = False
        self.buttons_assigned = None # set after creation of the layout manager to index button positions
        # Buttons stored here
        self.stop_button = None
        self.undo_button = None

    def setup_gui(
        self,
        controller: ControllerLike,
        num_axes: int = 1,
        num_buttons: int = 2,
        use_legend: bool = True,
        use_summary: bool = False,
        use_checkboxes: bool = False
    ):
        """ Create the figure, buttons, etc. Wire them to the controller's callback methods """
        self.controller = controller
        self.images_per_fig = self.controller.images_per_fig
        labels = self.controller.get_category_labels() if use_checkboxes else None
        self.use_summary = use_summary
        #self.fig = plt.figure(clear=True, num=self.fig_title)
        self.generate_layout(
            num_axes = num_axes,
            num_buttons = num_buttons,
            labels = labels,
            use_legend = use_legend,
            use_summary = use_summary,
            use_checkboxes = use_checkboxes
        )
        self.fig = self.layout.fig
        ###self.axs = self.layout.axes
        plt.ion()
        self.update_title(self.fig_title)
        maximize_window() # might need to come before plt.show
        # hook UI events for closing the figure to a cleanup function
        self.fig.canvas.mpl_connect("close_event", self._on_close)
        # create base buttons (STOP, UNDO) in the new structure, setting their callbacks later
        self._create_base_buttons()

    def generate_layout(self, num_axes: int = 1, num_buttons: int = 2, labels: List[str] = None, use_legend: bool = True, use_summary: bool = False, use_checkboxes: bool = False):
        """ Generate the layout for the figure, subplots, etc. """
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


    def _create_base_buttons(self):
        """ Creates STOP and UNDO buttons in the bottom region of the figure. Subclasses add more buttons in separate functions """
        #! FIXME: buttons no longer located in PaneledFigureWrapper.created_axes - call new method for PaneledFigureWrapper.buttons
            #! also, buttons are now returned as the actual axes objects - fix this too
        btn_axes: List[plt.Axes] = self.layout.get_button_axes()
        undo_ax = btn_axes[1]
        stop_ax = btn_axes[0]
        self.buttons_assigned[:1] = [True, True]  # mark the last two button positions (since they're added right to left) as assigned
        # Positions: [left, bottom, width, height]
        self.undo_button = ReviewerButton.factory(
            fig = self.fig,
            label = "UNDO",
            ax_pos = undo_ax.get_position().bounds,
            callback = self.controller.on_undo_clicked
        )
        self.stop_button = ReviewerButton.factory(
            fig = self.fig,
            # TODO: might want to change all instances of "STOP" buttons to "EXIT" for consistency with the viewer
            label = "STOP",
            ax_pos = stop_ax.get_position().bounds,
            callback = self.controller.on_stop_clicked
        )

    def _create_summary_box(self):
        """ ensures the summary box is properly instantiated """
        if self.use_summary:
            #ax = self.layout.get_axes("summary")
            self.update_summary("Awaiting Label Selection...")

    def _create_label_buttons(self, labels):
        raise NotImplementedError("Subclasses must implement this method to create label buttons")

    # def _create_legend(self):
    #     raise NotImplementedError("Subclasses must implement this method to create a legend")
    def _create_legend(self, legend_dict: Dict[str, str] = None):
        # bottom left corner to place the legend
        if legend_dict:
            legend_kwargs = {
                "loc": "lower left",
                "fontsize": "x-large",
            }
            position = self.layout.get_panel_position("left")
            if position:
                #position: Tuple[float, float] = self.layout.get_axes("legend").get_position().p0
                legend_kwargs["bbox_to_anchor"] = self.layout.get_panel_position("left")[:2]
            for label, color in legend_dict.items():
                plt.plot([], [], color=color, label=label, linewidth=6, alpha=0.4)
            self.fig.legend(**legend_kwargs)

    def display_image(self, image, ax_idx=0):
        """ show or update an image on self.axs; adjust accordingly for multiple axes """
        # if it's the first call, store the imshow result; otherwise update set_data().
        #! FIXME: images no longer located in PaneledFigureWrapper.created_axes - call new method for PaneledFigureWrapper.image_axes
            #! also, buttons are now returned as the actual axes objects - fix this too
        ax = self.layout.get_image_subaxes(ax_idx)
        if len(self.canvas_images) > ax_idx:
            self.canvas_images[ax_idx].set_data(image)
        else:
            # if the viewer is only displaying one image, don't set the aspect ratio to "auto" since it will be stretched
            aspect_ratio = "auto" if self.images_per_fig > 1 else None
            img_obj = ax.imshow(image, aspect=aspect_ratio)
            self.canvas_images.append(img_obj)
        #self.fig.canvas.draw()
        self.fig.canvas.draw_idle()  # Update without forcing new figures

    def update_title(self, text, subtitle = None):
        # TODO: update to split text into a primary title and subtitles
        if self.fig:
            self.fig.suptitle(text, fontsize=24, fontweight="bold", wrap=True)
            if subtitle:
                try:
                    self.fig.texts[1].remove()  # remove the previous subtitle if it exists
                except IndexError:
                    pass
                self.fig.text(0.5, 0.95, subtitle, ha='center', va='top', fontsize=18)

    #~ UPDATE: new summary axis with random extra stuff queued by the data manager
    def update_summary(self, text):
        """ updates the summary box with new text """
        if self.use_summary:
            summary_ax = self.layout.get_axes("summary")
            if summary_ax:
                summary_ax.clear()
                summary_ax.text(0.5, 0.5, text, ha="center", va="center", fontsize="large")
                summary_ax.axis("off")
                #self.fig.canvas.draw()
                self.fig.canvas.draw_idle()  # Update without forcing new figures

    def display_warning(self, message="Warning!", duration=3000):
        """ replicates the old 'display_warning()' from base_reviewer.py with purely UI functionality """
        txt = self.fig.text(0.5, 0.3, message, ha='center', va='center', fontsize=18, color='red', backgroundcolor='#263037')
        #self.fig.canvas.draw()
        self.fig.canvas.draw_idle()  # Update without forcing new figures
        def remove_text():
            try:
                txt.set_visible(False)
                #self.fig.canvas.draw()
                self.fig.canvas.draw_idle()  # Update without forcing new figures
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
        try:
            while not self._stop_requested and plt.fignum_exists(self.fig.number):
                #self.fig.canvas.flush_events()  # Process events without blocking
                # self.fig.canvas.draw()
                plt.pause(0.05) # short pause to handle events
        except KeyboardInterrupt:
            # if the user interrupts the loop, we can handle it here
            print("[VIEWER] Keyboard interrupt detected. Stopping review...")
            #self.request_stop()
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

