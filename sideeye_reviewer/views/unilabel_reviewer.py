from typing import List, Tuple
import matplotlib.pyplot as plt
# local imports
from ..types import ControllerLike
from .base_viewer import BaseReviewerView
from .reviewer_button import ReviewerButton


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
        #! TEMP: setting to true by default until it's integrated into the controller
        use_summary: bool = True,
    ):
        self.use_summary = use_summary
        use_legend = bool(self.legend_dict)
        n_btn = len(labels) + 2  # 2 for the base buttons (EXIT, UNDO) and the rest for labels
        # call the base class's setup_gui() to create the figure, subplots, etc.
        super().setup_gui(controller, num_axes, num_buttons = n_btn, use_legend=use_legend, use_summary = use_summary)
        # create base buttons (EXIT, UNDO) in the new structure, setting their callbacks later
        self._create_base_buttons()
        # unfortunately, it seems that subfigure objects don't support setting the layout engine and using fig.set_layout() doesn't work correctly
        self.fig.tight_layout()
        # create label-specific buttons
        self._create_label_buttons(labels)
        # optionally create the legend
        self._create_legend(self.legend_dict)
        # initialize summary box with filler text
        # create summary box if using summary
        self.update_summary("Awaiting Label Selection...")

    def _create_label_buttons(self, labels: List[str]):
        """ called after the base class sets up the figure and base buttons to place label-specific buttons """
        #? NOTE: these are returned in reverse order so that the rightmost button is at index 0
        # reversing button axes order back to left-to-right to lay out labels in the order they were given
        button_axes_data = self.layout.get_button_axes()[::-1]
        button_axes: List[plt.Axes] = [ax_data.axes for ax_data in button_axes_data]
        num_btn = len(button_axes)
        # drop buttons that have already been assigned (primarily the EXIT and UNDO Buttons set by the base class)
            #? NOTE: this will probably be changed in the future when I update the slideshow viewer to inherit from the same base class
        available_axes = []
        for i, ax in enumerate(button_axes):
            if not self.buttons_assigned[num_btn - i - 1]:
                available_axes.append(ax)
                self.buttons_assigned[num_btn - i - 1] = True  # mark this button as assigned
        for lbl, ax in zip(labels, available_axes):
            btn = ReviewerButton.factory(
                ax,
                label=lbl.upper(),
                ax_pos = ax.get_position().bounds,
                callback = self.controller.get_on_label_clicked_cb(lbl)
            )
            self.label_buttons.append(btn)
