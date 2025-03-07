from typing import List
import matplotlib.pyplot as plt
# local imports
from .base_viewer import BaseReviewerView
from .reviewer_button import ReviewerButton
from ..utils.utils import get_button_axes

class SingleLabelReviewerView(BaseReviewerView):
    """ specialized view for single-label reviewing - one button per label which calls 'on_label_clicked()' in the controller """
    def __init__(self, fig_title="Single-Label Reviewer", legend_dict=None):
        super().__init__(fig_title)
        self.legend_dict = legend_dict
        self.label_buttons = []

    def setup_gui(self, controller, labels: List[str], num_axes: int = 1):
        # first perform base setup (creates figure, base buttons, etc.)
        super().setup_gui(controller, num_axes)
        # Now create label-specific buttons
        self._create_label_buttons(labels)
        # Optionally create the legend
        self._create_legend()

    def _create_legend(self):
        if self.legend_dict:
            for label, color in self.legend_dict.items():
                plt.plot([], [], color=color, label=label, linewidth=4, alpha=0.4)
            self.fig.legend(loc="lower left", fontsize="large")
        # adjust figure for space if needed
        self.fig.subplots_adjust(left=0.05, right=0.95)  # images use 0-0.95 of the width

    def _create_label_buttons(self, labels: List[str]):
        """ called after the base class sets up the figure and base buttons to place label-specific buttons """
        # for each label, create a button:
        num_labels = len(labels)
        # alighned at the bottom, right side
        right_bound = min(self.undo_button.ax_pos[0] - 0.01, self.stop_button.ax_pos[0] - 0.01)
        left_bound = max(0.05, right_bound - 0.1 * num_labels + 0.01)
        positions = get_button_axes(num_buttons=num_labels, left_bound=left_bound, right_bound=right_bound)
        for lbl, pos in zip(labels, positions):
            btn = ReviewerButton.factory(
                fig=self.fig,
                label=lbl.upper(),
                ax_pos=pos,
                callback = self.controller.get_on_label_clicked_cb(lbl)
            )
            self.label_buttons.append(btn)

    # optional: any extra code specifically for single-label UI