import matplotlib.pyplot as plt
from typing import List, Tuple
from matplotlib.widgets import CheckButtons
# local imports
from ..types import ControllerLike
from .base_viewer import BaseReviewerView
from .reviewer_button import ReviewerButton
from ..utils.utils import get_button_axes



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
        self._create_legend()
        self._create_summary_box()

    def _create_legend(self):
        # bottom left corner to place the legend
        if self.legend_dict:
            position: Tuple[float, float] = self.layout.get_axes("legend").get_position().p0
            for label, color in self.legend_dict.items():
                plt.plot([], [], color=color, label=label, linewidth=6, alpha=0.4)
            self.fig.legend(bbox_to_anchor = position, loc="lower left", fontsize="x-large")

        # adjust figure for space if needed
        #self.fig.subplots_adjust(left=0.05, right=0.95)  # images use 0-0.95 of the width

    def _create_checkboxes(self, labels):
        """ Create the checkboxes for multi-label usage """
        num_labels = len(labels)
        # # REMINDER: order is [left, bottom, width, height]
        ax_checkboxes = self.layout.get_axes("checkboxes")
        # Define properties for labels and checkboxes
        label_props = {'color': ['black'] * num_labels, 'fontsize': ['x-large'] * num_labels}
        check_props = {'facecolor': ['blue'] * num_labels, 'sizes': [100] * num_labels}
        frame_props = {'edgecolor': 'black', 'sizes': [200] * num_labels, 'facecolor': 'white'}
        self.checkboxes = CheckButtons(ax_checkboxes, labels, label_props=label_props, check_props=check_props, frame_props=frame_props)
        self.checkboxes.ax.set_title("Select all that apply.", fontsize="x-large")
        
        from pprint import pprint
        pprint(vars(self.fig))
        print()
        print(self.checkboxes)
        pprint(vars(self.checkboxes))

    def add_next_button(self):
        # # NOTE: selecting first element since there's only one in this case and that's how the factory expects it
        # positions = get_button_axes(num_buttons=1, left_bound=left_bound, right_bound=right_bound)[0]
        positions = self.layout.get_axes("buttons")[-1].get_position().bounds
        self.next_button = ReviewerButton.factory(
            fig=self.fig,
            label="NEXT",
            ax_pos=positions,
            callback=self.controller.on_next_clicked
        )

    def get_checked_labels(self, clear_after=False):
        """ controller calls this to retrieve which boxes are checked """
        # return self.checkboxes.get_checked_labels() or a custom method
        # NOTE: CheckButtons object in matplotlib 3.7+ has get_status() to use, but older versions may not
        status = self.checkboxes.get_status()  # list of bools
        labels = self.checkboxes.labels
        chosen = [label.get_text() for label, s in zip(labels, status) if s]
        # optionally uncheck the boxes in the view
        if clear_after:
            self.checkboxes.clear()
        return chosen

    def _create_summary_box(self):
        """ ensure the summary box is properly formatted """
        if self.use_summary:
            self.update_summary("Awaiting Image Review...")