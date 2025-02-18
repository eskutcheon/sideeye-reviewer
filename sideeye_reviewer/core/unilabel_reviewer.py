import matplotlib.pyplot as plt
from typing import Optional, Dict
from .base_reviewer import BaseReviewer
from .reviewer_button import ReviewerButton
from .sorter import ImageSorter
from sideeye_reviewer.utils.utils import get_button_axes


class SingleLabelReviewer(BaseReviewer):
    """ Each labeled button sorts the current image into that label bin, then advances to the next image """
    def __init__(self, sorter: ImageSorter, fig_title: str = "Single-Label Reviewer", legend_dict: Optional[Dict[str, str]] = None):
        super().__init__(sorter, fig_title)
        self.legend_dict = legend_dict
        self.label_buttons = []

    def create_subclass_buttons(self):
        """ called after the base class sets up the figure and base buttons to place label-specific buttons """
        labels = self.sorter.sorter_labels
        num_labels = len(labels)
        # We'll place them near the bottom, left side
        right_bound = min(self.undo_button.ax_pos[0] - 0.01, self.stop_button.ax_pos[0] - 0.01)
        left_bound = max(0.05, right_bound - 0.1 * num_labels + 0.01)
        positions = get_button_axes(num_buttons=num_labels, left_bound=left_bound, right_bound=right_bound)
        for lbl, pos in zip(labels, positions):
            btn = ReviewerButton.factory(
                fig=self.fig,
                label=lbl.upper(),
                ax_pos=pos,
                callback=self._make_label_callback(lbl)
            )
            self.label_buttons.append(btn)

    def _make_label_callback(self, label: str):
        """ returns a callback function that, when clicked, calls sorter.update_bin(label) and moves to the next image """
        def _callback(event):
            # sort the current image into the given label then move to the next image
            current_file = self.file_list[self.current_idx]
            self.sorter.set_current_image(current_file)
            self.sorter.update_bin(label)
            self.next_image()
        return _callback

    def create_figure_and_axes(self):
        """ Extend the base method to also place the legend, if any. """
        super().create_figure_and_axes()
        if self.legend_dict:
            # Make a basic legend: e.g., {'clean':'black', 'transparent':'green'}
            for label, color in self.legend_dict.items():
                plt.plot([], [], color=color, label=label)
            plt.legend(loc="lower left", fontsize="medium")
        self.fig.subplots_adjust(left=0.05, right=0.95)  # images use 0-0.95 of the width

    def begin_review(self, checkpoint=True):
        """ Override to add a step to create label buttons after the base figure is created but before the main loop starts. """
        super().begin_review(checkpoint)
        # Because we want to create the base figure, then create our label buttons,
        # we must do so after the figure exists. Easiest is: do it right after base calls it:
        if self.fig and not self._stop_requested:
            self.create_subclass_buttons()
            # Re-draw them
            self.fig.canvas.draw()
            self.main_loop()