import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons
# local imports
from .base_viewer import BaseReviewerView
from .reviewer_button import ReviewerButton
from ..utils.utils import get_button_axes



class MultiLabelReviewerView(BaseReviewerView):
    def __init__(self, fig_title="Multi-Label Reviewer", legend_dict=None):
        super().__init__(fig_title)
        self.legend_dict = legend_dict
        self.next_button = None
        self.checkboxes = None

    def setup_gui(self, controller, labels, num_axes=1):
        super().setup_gui(controller, num_axes)
        # Create checkboxes and next button
        self._create_checkboxes(labels)
        self.add_next_button()
        # Possibly create a legend the same way
        self._create_legend()

    def _create_legend(self):
        # Possibly create a legend if needed
        if self.legend_dict:
            for label, color in self.legend_dict.items():
                plt.plot([], [], color=color, label=label, linewidth=4, alpha=0.4)
            self.fig.legend(loc="lower left", fontsize="large")

    def _create_checkboxes(self, labels):
        """ Create the checkboxes for multi-label usage """
        num_labels = len(labels)
        # REMINDER: order is [left, bottom, width, height]
        checkbox_bound = max(self.undo_button.ax_pos[0], self.stop_button.ax_pos[0])
        bottom_bound = self.stop_button.ax_pos[1] + 0.15
        height = 0.05 * num_labels
        # NOTE: may have to figure out how to reposition the existing axes to add this right
        ax_ck = self.fig.add_axes([checkbox_bound + 0.01, bottom_bound, 0.10, height])
        self.fig.subplots_adjust(left=0.05, bottom = bottom_bound - 0.05, right=0.85)  # images only use 0-0.85 of the width
        # Define properties for labels and checkboxes
        label_props = {'color': ['black'] * len(labels), 'fontsize': ['large'] * len(labels)}
        check_props = {'facecolor': ['blue'] * len(labels), 'sizes': [75] * len(labels)}
        frame_props = {'edgecolor': 'black', 'sizes': [125] * len(labels), 'facecolor': 'white'}
        self.checkboxes = CheckButtons(ax_ck, labels, label_props=label_props, check_props=check_props, frame_props=frame_props)
        self.checkboxes.ax.set_facecolor('lightgray')
        self.checkboxes.ax.set_title("Select all that apply", fontsize="x-large")

    def add_next_button(self):
        right_bound = min(self.undo_button.ax_pos[0] - 0.01, self.stop_button.ax_pos[0] - 0.01)
        left_bound = max(0.05, right_bound - 0.1)
        # NOTE: selecting first element since there's only one in this case and that's how the factory expects it
        positions = get_button_axes(num_buttons=1, left_bound=left_bound, right_bound=right_bound)[0]
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