import matplotlib.pyplot as plt
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import numpy as np
from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
# local imports
from .axes_data import (
    LegendAxesData,
    SummaryAxesData,
    ButtonAxesData,
    CheckboxAxesData,
    ButtonPanelAxesData,
    AXES_PADDING, # padding between axes in the figure
    BUTTON_HEIGHT
)

def disable_all_axis_elements():
    """ went through hell debugging this, so this is probably the easiest solution I'm gonna get for now """
    plt.rcParams['axes.spines.left'] = False
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.bottom'] = False
    plt.rcParams['xtick.bottom'] = False
    plt.rcParams['xtick.labelbottom'] = False
    plt.rcParams['ytick.labelleft'] = False
    plt.rcParams['ytick.left'] = False

def measure_checkbox_labels(labels, main_fig_size=(12, 7), fontsize=16, line_spacing=1.2):
    """ returns (total_width, total_height) in "text units" for stacked labels,
        computed purely via text path metrics (no figure or event loop).
    """
    # create FontProperties instance for desired font & size
    font = FontProperties(size=fontsize)
    # track bounding box extremes for each label - subsequent labels placed at negative y offsets => "stacking" downward
    min_x, min_y, max_x, max_y = np.inf, np.inf, -np.inf, -np.inf
    baseline_y = 0.0
    # iterate over labels while tracking extents
    for lbl in labels:
        # create TextPath at (x=0, y=baseline_y)
        tp = TextPath(xy=(0, baseline_y), s=lbl, prop=font)
        # textpath's bounding box => a matplotlib.path.Path in user coords
        bbox = tp.get_extents()
        # union bounding box
        min_x = min(min_x, bbox.x0)
        min_y = min(min_y, bbox.y0)
        max_x = max(max_x, bbox.x1)
        max_y = max(max_y, bbox.y1)
        # typical line spacing = line_spacing * single-line offset
        line_height = (bbox.y1 - bbox.y0) * line_spacing
        # reduce baseline downward for next label
        baseline_y -= line_height
    total_w_pts = max_x - min_x
    total_h_pts = max_y - min_y
    # convert from points to inches (1 point = 1/72 inch)
    width_inch  = total_w_pts  / 72.0
    height_inch = total_h_pts / 72.0
    # convert to fraction of your main figure size
    fig_w_inch, fig_h_inch = main_fig_size
    width_fraction  = width_inch  / fig_w_inch
    height_fraction = height_inch / fig_h_inch
    # add a bit of padding so text doesn’t clip
    width_fraction  *= 0.7
    #height_fraction *= 0.8
    return width_fraction, height_fraction


# def approximate_checkbox_size(labels, fontsize=14, char_width_factor=0.6, line_spacing=1.2):
#     """
#     Very rough approximation: each char ~ char_width_factor * fontsize wide,
#     each line ~ fontsize * line_spacing high.
#     Returns (approx_width, approx_height) in "pixel-ish" units if you treat fontsize as px.
#     """
#     if not labels:
#         return (0.0, 0.0)
#     max_chars = max(len(lbl) for lbl in labels)
#     max_width = max_chars * char_width_factor * fontsize
#     total_height = len(labels) * fontsize * line_spacing
#     # Add some padding
#     return (max_width * 1.1, total_height * 1.1)


class ReviewFigureLayout:
    """
        Manages:
        1) A row (or sub-row) of image Axes for 1..N images.
        2) An optional right-side region for a legend or checkboxes.
        3) A bottom row for horizontally aligned buttons.
        4) References to all Axes in a dictionary.
    """
    MAX_IMG_PER_FIGURE = 4  # max number of images per figure - throw error if num_images > this
    MAX_IMG_COLS = 3  # max number of image per row
    FIGURE_DIMS = (12, 7)  # default figure dimensions (width, height)

    def __init__(
        self,
        num_images: int,
        num_buttons: int,
        labels: Union[List[str], None],
        use_legend: bool,
        use_summary: bool,
        use_checkboxes: bool,
    ):
        disable_all_axis_elements()
        if num_images > self.MAX_IMG_PER_FIGURE:
            raise ValueError(f"Too many images ({num_images}) for a single figure. Max is {self.MAX_IMG_PER_FIGURE}.")
        self.num_images = num_images
        self.checkbox_dims = None
        #import sys
        if labels and use_checkboxes:
            self.checkbox_dims = measure_checkbox_labels(labels)
            #self.checkbox_dims = approximate_checkbox_size(labels)
            print("checkbox dims: ", self.checkbox_dims)
            #sys.exit(0)
        self.use_legend = use_legend
        self.use_checkboxes = use_checkboxes
        self.use_summary = use_summary
        self.num_buttons = num_buttons
        # store the actual Axes objects in a dictionary for later access
        self.axes: Dict[str, plt.Axes] = {}
        # may also want to store the final figure reference
        self.fig: Optional[plt.Figure] = None

    def create_layout(self):
        """ Dynamically creates the layout with adaptable axes for images, legends, checkboxes, summary boxes, and buttons """
        #has_right_column = self.use_summary or self.use_checkboxes
        # create the figure that everything will be based on
        # self.fig = plt.figure(figsize=(12, 7), subplotpars={'wspace': 0.1}) # or gridspec_kw - formerly used in plt.subplots
        self.fig = plt.figure(figsize=self.FIGURE_DIMS)
        # NOTE: writing these as steps because the order of creation matters for dynamically determining the layout
        # 1. create bottom row for right-aligned buttons - easiest to base other relative axes on the panel's position
        self._create_button_axes()
        buttons_top = self.axes["button_panel"].get_position().y1  # Top of button panel
        #buttons_top = self.axes["button_panel"].get_position().bounds[1] + self.axes["button_panel"].get_position().bounds[3]
        # 2. optionally create legend in the bottom left corner
        legend_top = 0.3
        if self.use_legend:
            self._create_legend(buttons_top) # default placement: left of button panel
            # top bound of legend to align image axes
            legend_top = self.axes["legend"].get_position().y1 + AXES_PADDING
        # 3. optionally create checkboxes (above button panel)
        if self.use_checkboxes:
            checkboxes_bottom = buttons_top + AXES_PADDING
            self._create_checkboxes(checkboxes_bottom)
        # 4. optionally create summary box (above checkboxes or centered with the img axes' position
        if self.use_summary:
            checkboxes_top = self.axes["button_panel"].get_position().y1 + AXES_PADDING
            if self.use_checkboxes:
                checkboxes_top = self.axes["checkboxes"].get_position().y1 + AXES_PADDING
            self._create_summary_box(checkboxes_top)
        # 5. assign remaining space to image axes
        self._create_image_axes(legend_top)


    def _create_legend(self, button_top):
        """ Creates a dynamically scaled legend to fit within available space. """
        legend_height = button_top + 0.05  # TODO: adjust height to fit labels
        legend_ax_obj = LegendAxesData()
        # set legend height and use defaults on all other axes properties
        legend_ax_obj.set_ax_pos([legend_height], [3])
        self.axes["legend"] = legend_ax_obj.create_axes_object(self.fig)


    def _create_checkboxes(self, checkboxes_bottom):
        """ Creates checkboxes aligned above the button panel. """
        checkbox_ax_obj = CheckboxAxesData()
        kwargs = {"pos": [checkboxes_bottom], "idx": [1]}  # set checkbox height
        if self.checkbox_dims:
            # set checkbox width dynamically based on the longest label
            kwargs["pos"].append(1 - self.checkbox_dims[0] - AXES_PADDING)  # left bound of checkbox column
            kwargs["pos"].extend(self.checkbox_dims)
            kwargs["idx"].extend([0, 2, 3])
        # set checkbox bottom bound and use defaults on all other axes properties
        checkbox_ax_obj.set_ax_pos(**kwargs)
        self.axes["checkboxes"] = checkbox_ax_obj.create_axes_object(self.fig)

    def _create_summary_box(self, checkboxes_top):
        """ Creates a summary box aligned dynamically with checkboxes. """
        summary_ax_obj = SummaryAxesData()
        bottom = checkboxes_top + AXES_PADDING if self.use_checkboxes else 0.5 - (summary_ax_obj.ax_pos[3]/2)  # else center vertically
        kwargs = {"pos": [bottom], "idx": [1]}  # set summary height
        if self.checkbox_dims:
            # set summary width dynamically based on the longest label
            kwargs["pos"].append(1 - self.checkbox_dims[0] - AXES_PADDING)  # left bound of checkbox column
            kwargs["pos"].extend(self.checkbox_dims)
            kwargs["idx"].extend([0, 2, 3])
        summary_ax_obj.set_ax_pos(**kwargs)
        self.axes["summary"] = summary_ax_obj.create_axes_object(self.fig)


    def _create_image_axes(self, bottom_bound):
        """ Allocates remaining space for image axes. """
        num_img_rows = self._compute_image_rows()
        num_img_cols = self._compute_image_cols()
        # FIXME: work with existing axes to determine the available space for images and judge by the legend top, not right bound
        # Determine right bound (left of summary/checkbox column, if present)
        if self.use_summary or self.use_checkboxes:
            try:
                image_right_bound = self.axes["summary"].get_position().x0 - AXES_PADDING
            except KeyError:
                image_right_bound = self.axes["checkboxes"].get_position().x0 - AXES_PADDING
        else:
            image_right_bound = 0.95  # Full width available
        # Compute figure width and height dynamically
        image_ax_width = image_right_bound - AXES_PADDING
        image_ax_height = bottom_bound - AXES_PADDING
        # Create subplots inside self.fig (avoids opening a new figure)
        img_axes = self.fig.subplots(
            num_img_rows,
            num_img_cols,
            width_ratios = [image_ax_width] * num_img_cols,
            height_ratios = [image_ax_height] * num_img_rows,
            gridspec_kw = {'wspace': 0.1} #, 'hspace': 0.1}
        )
        self.fig.subplots_adjust(
            left = 5*AXES_PADDING,
            right = image_right_bound,
            bottom = bottom_bound - AXES_PADDING
        )
        # flatten axes if multiple rows exist
        self.axes["images"] = []
        img_axes: List[plt.Axes] = img_axes.flatten() if isinstance(img_axes, Iterable) else [img_axes]
        for i in range(self.num_images):
            img_axes[i].set_aspect("auto", adjustable="box")
            img_axes[i].axis("off")
            self.axes["images"].append(img_axes[i])
        # hide any unused image axes
        for ax in img_axes[self.num_images:]:
            ax.set_visible(False)


    def _create_button_axes(self):
        """ Creates a bottom-aligned button panel. """
        panel_ax_obj = ButtonPanelAxesData()
        print("panel axes color: ", panel_ax_obj.color)
        self.axes["button_panel"] = panel_ax_obj.create_axes_object(self.fig)
        #self.axes["button_panel"].set_visible(True)  # just to visualize
        # compute button positions (right-aligned)
        #~ NOTE: still considering creating the legend first to make it wider, just in case labels are long
        # setting the left and right bound just in case the defaults here ever change from axes_data.py
        left_bound = self.axes["button_panel"].get_position().x0  # left bound of button panel
        right_bound = self.axes["button_panel"].get_position().x1  # right bound of button panel
        button_positions = self._compute_button_positions(self.num_buttons, left_bound, right_bound)
        self.axes["buttons"] = []
        for pos in button_positions:
            # create a new button Axes object for each button
            btn_ax_obj = ButtonAxesData(ax_pos = pos)
            self.axes["buttons"].append(btn_ax_obj.create_axes_object(self.fig))

    def _compute_button_positions(self, num_buttons: int, left_bound = 0.3, right_bound = 0.95) -> List[List[float]]:
        """ Re-implement get_button_axes using figure-relative coordinates - bottom right aligned """
        def get_total_width(w: float, s: float) -> float:
            return (w + s) * num_buttons - s
        width, spacing = 0.1, 0.01
        total_width = get_total_width(width, spacing)
        # rescale if total width exceeds available space
            # eventually, might want to allocate enough vertical space (more than the default 0.15) to have extra button rows
        if total_width > right_bound - left_bound:
            scale = (right_bound - left_bound)/total_width
            width *= scale
            spacing *= scale
            total_width = get_total_width(width, spacing)
        padding = (right_bound - left_bound - total_width)/2
        left_bound += padding
        positions = []
        for i in range(num_buttons):
            #left = left_bound + i*(width + spacing)
            right = right_bound - (i+1)*(width + spacing)
            # keep the bottom at 0.025 and the height at 0.075 so that the top of the buttons are all at 0.1
            #positions.append([left, AXES_PADDING, width, BUTTON_HEIGHT])
            positions.append([right, AXES_PADDING, width, BUTTON_HEIGHT])
        return positions


    def _compute_image_cols(self) -> int:
        """ dynamically calculates the number of columns needed based on image counts """
        return min(self.num_images, self.MAX_IMG_COLS)

    def _compute_image_rows(self) -> int:
        """ calculates the number of rows needed for the given image count """
        return (self.num_images // self.MAX_IMG_COLS) + (1 if self.num_images % self.MAX_IMG_COLS else 0)

    def get_axes(self, name: str) -> Optional[Union[plt.Axes, List[plt.Axes]]]:
        """ Utility to retrieve an Axes reference by name (e.g. "legend", "summary", "button_panel") """
        return self.axes.get(name, None)

    def get_subaxes(self, name: str, idx: int) -> plt.Axes:
        """ Utility to retrieve a list of sub-axes by name (e.g. "images", "buttons") and by index (self.axes[name][idx]) """
        try:
            return self.axes.get(name, [])[idx]
        except IndexError:
            raise IndexError(f"Index {idx} out of range for axes list '{name}'.")

    def finalize(self):
        """ final processing steps - e.g. 'tight_layout()' or other final steps.
            NOTE: often with custom coords, it messes up positions however
        """
        # plt.tight_layout()  # Optional, but might cause legend overlap.
        pass
