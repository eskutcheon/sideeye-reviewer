from typing import List, Tuple
import matplotlib.pyplot as plt
# local imports
from ..types import ControllerLike
from .base_viewer import BaseReviewerView
from .reviewer_button import ReviewerButton
# from ..utils.utils import get_button_axes

class SingleLabelReviewerView(BaseReviewerView):
    """ specialized view for single-label reviewing - one button per label which calls 'on_label_clicked()' in the controller """
    def __init__(self, fig_title="Single-Label Reviewer", legend_dict=None):
        super().__init__(fig_title)
        self.legend_dict = legend_dict
        self.label_buttons = []
        self.use_summary = False

    def setup_gui(
        self,
        controller: ControllerLike,
        labels: List[str],
        num_axes: int = 1,
        use_summary: bool = False,
    ):
        self.use_summary = use_summary
        use_legend = bool(self.legend_dict)
        n_btn = len(labels) + 2  # 2 for the base buttons (STOP, UNDO) and the rest for labels
        # call the base class's setup_gui() to create the figure, subplots, etc.
        super().setup_gui(controller, num_axes, num_buttons = n_btn, use_legend=use_legend, use_summary = use_summary)
        # Now create label-specific buttons
        self._create_label_buttons(labels)
        # Optionally create the legend
        self._create_legend()
        # initialize summary box with filler text
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

    def _create_label_buttons(self, labels: List[str]):
        """ called after the base class sets up the figure and base buttons to place label-specific buttons """
        # for each label, create a button, aligned at the bottom, right side
        button_axes: List[plt.Axes] = self.layout.get_axes("buttons")[::-1]
        num_btn = len(button_axes)
        open_positions = [pos.get_position().bounds for i, pos in enumerate(button_axes) if self.buttons_assigned[num_btn - i] is False]
        for lbl, pos in zip(labels, open_positions):
            btn = ReviewerButton.factory(
                fig=self.fig,
                label=lbl.upper(),
                ax_pos=pos, #.get_position().bounds,
                callback = self.controller.get_on_label_clicked_cb(lbl)
            )
            self.label_buttons.append(btn)

    def _create_summary_box(self):
        """ Ensures the summary box is properly formatted. """
        if self.use_summary:
            self.update_summary("Awaiting Label Selection...")
