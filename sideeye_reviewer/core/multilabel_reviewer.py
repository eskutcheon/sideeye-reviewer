import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons
from typing import Optional, Dict
# local imports
from .base_reviewer import BaseReviewer
from .reviewer_button import ReviewerButton
from .sorter import ImageSorter
from sideeye_reviewer.utils.utils import get_button_axes


class MultiLabelReviewer(BaseReviewer):
    """ Each label is a checkbox where users can check one or more, then click NEXT to finish labeling the current file """
    def __init__(self, sorter: ImageSorter, fig_title: str = "Multi-Label Reviewer", legend_dict: Optional[Dict[str, str]] = None):
        super().__init__(sorter, fig_title)
        self.legend_dict = legend_dict
        self.checkboxes = None
        self.next_button = None

    def create_subclass_widgets(self):
        """ Create the checkboxes and NEXT button for multi-label usage """
        labels = self.sorter.sorter_labels
        num_labels = len(labels)
        # REMINDER: order is [left, bottom, width, height]
        checkbox_bound = max(self.undo_button.ax_pos[0], self.stop_button.ax_pos[0])
        bottom_bound = self.stop_button.ax_pos[1] + 0.15
        height = 0.05 * num_labels
        # NOTE: may have to figure out how to reposition the existing axes to add this right
        ax_ck = self.fig.add_axes([checkbox_bound + 0.01, bottom_bound, 0.10, height])
        #ax_ck = self.fig.add_axes([0.91, 0.3, 0.10, 0.05 * num_labels])
        self.fig.subplots_adjust(left=0.05, right=0.85)  # images only use 0-0.85 of the width
        # Define properties for labels and checkboxes
        label_props = {
            'color': ['black'] * len(labels),
            'fontsize': ['large'] * len(labels)
        }
        check_props = {
            'facecolor': ['blue'] * len(labels),
            'sizes': [75] * len(labels),
        }
        frame_props = {
            'edgecolor': 'black',
            'sizes': [125] * len(labels),
            'facecolor': 'white'
        }
        self.checkboxes = CheckButtons(ax_ck, labels, label_props=label_props, check_props=check_props, frame_props=frame_props)
        self.checkboxes.ax.set_facecolor('lightgray')
        self.checkboxes.ax.set_title("Select all that apply", fontsize="x-large")
        self.add_next_button()

    def add_next_button(self):
        right_bound = min(self.undo_button.ax_pos[0] - 0.01, self.stop_button.ax_pos[0] - 0.01)
        left_bound = max(0.05, right_bound - 0.1)
        # NOTE: selecting first element since there's only one in this case and that's how the factory expects it
        positions = get_button_axes(num_buttons=1, left_bound=left_bound, right_bound=right_bound)[0]
        self.next_button = ReviewerButton.factory(
            fig=self.fig,
            label="NEXT",
            ax_pos=positions,
            callback=self.on_next_clicked
        )

    def on_next_clicked(self, event):
        if not self.file_list:
            return
        # Determine which checkboxes are checked
        chosen = self.checkboxes.get_checked_labels()
        print("chosen:", chosen)
        if not chosen:
            self.display_warning(message="Please select at least one checkbox before clicking 'NEXT'.")
            return
        # Sort the current image into those bins
        current_file = self.file_list[self.current_idx]
        self.sorter.set_current_image(current_file)
        self.sorter.update_bin(chosen)
        # uncheck all boxes for the next image
        self.checkboxes.clear()
        # Move to next
        self.next_image()


    def create_figure_and_axes(self):
        super().create_figure_and_axes()
        # Possibly create a legend if needed
        if self.legend_dict:
            for label, color in self.legend_dict.items():
                plt.plot([], [], color=color, label=label, linewidth=4, alpha=0.4)
            plt.legend(loc="lower left", fontsize="large")


    def begin_review(self, checkpoint=True):
        super().begin_review(checkpoint)
        if self.fig and not self._stop_requested:
            self.create_subclass_widgets()
            self.fig.canvas.draw()
            self.main_loop()
