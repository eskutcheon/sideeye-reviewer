import matplotlib.pyplot as plt
from typing import List, Tuple
from matplotlib.widgets import CheckButtons
# local imports
from ..types import ControllerLike
from .base_viewer import BaseReviewerView
from .reviewer_button import ReviewerButton


class MultiLabelReviewerView(BaseReviewerView):
    def __init__(self, fig_title="Multi-Label Reviewer", legend_dict=None):
        super().__init__(fig_title)
        self.legend_dict = legend_dict
        self.next_button = None
        self.checkboxes = None
        self.use_summary = False

    def setup_gui(
        self,
        controller: ControllerLike,
        labels: List[str],
        num_axes: int = 1,
        use_summary: bool = False,
    ):
        #super().setup_gui(controller, num_axes)
        self.use_summary = use_summary
        use_legend = bool(self.legend_dict)
        n_btn = 3  # 3 for the base buttons (STOP, UNDO) and NEXT for "NEXT" for this subclass
        super().setup_gui(controller, num_axes, num_buttons = n_btn, use_legend=use_legend, use_summary = use_summary, use_checkboxes = True)
        # create checkboxes and next button
        self._create_checkboxes(labels)
        self.add_next_button()
        # optionally create a legend the same way
        self._create_legend(self.legend_dict)
        self._create_summary_box()

    def _create_checkboxes(self, labels):
        """ Create the checkboxes for multi-label usage """
        num_labels = len(labels)
        # # REMINDER: order is [left, bottom, width, height]
        # TODO: might refactor to retrieve AxesData object instead of the axes directly - reference bounds this way
        ax_checkboxes: plt.Axes = self.layout.get_axes("right", "checkboxes") #[0]
        print("ax_checkboxes: ", ax_checkboxes)
        #ax_checkboxes = ax_checkboxes.axes
        print("ax_checkboxes position: ", ax_checkboxes.get_position().bounds)
        # Define properties for labels and checkboxes
        label_props = {'color': ['black'] * num_labels, 'fontsize': ['x-large'] * num_labels}
        check_props = {'facecolor': ['blue'] * num_labels, 'sizes': [100] * num_labels}
        frame_props = {'edgecolor': 'black', 'sizes': [200] * num_labels, 'facecolor': 'white'}
        self.checkboxes = CheckButtons(ax=ax_checkboxes, labels=labels, label_props=label_props, check_props=check_props, frame_props=frame_props)
        self.checkboxes.ax.set_title("Select all that apply.", fontsize="x-large")
        print("checkbox dimensions after creation: ", self.checkboxes.ax.get_position().bounds)


    def add_next_button(self):
        # # NOTE: selecting first element since there's only one in this case and that's how the factory expects it
        # get leftmost button to assign "NEXT" label (since get_button_axes() returns them in reverse order)
        print(self.layout.get_button_axes())
        position = self.layout.get_button_axes()[-1].axes.get_position().bounds
        subfig = self.layout.get_subfigure("bottom")
        # FIXME: need to fix the position back into something relevant to the enclosing panel
        self.next_button = ReviewerButton.factory(
            fig=subfig,
            label="NEXT",
            ax_pos=position,
            callback=self.controller.on_next_clicked
        )

    def get_checked_labels(self, clear_after=True):
        """ controller calls this to retrieve which boxes are checked """
        # NOTE: CheckButtons object in matplotlib 3.7+ has get_status() to use, but older versions may not
        status = self.checkboxes.get_status()  # list of bools
        labels = self.checkboxes.labels
        chosen = [label.get_text() for label, s in zip(labels, status) if s]
        # optionally uncheck the boxes in the view - tbh, not sure why I wouldn't but this was recommended
        if clear_after:
            self.checkboxes.clear()
        return chosen
