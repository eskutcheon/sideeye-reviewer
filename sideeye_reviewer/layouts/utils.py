import matplotlib.pyplot as plt
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import numpy as np
from typing import List, Optional, Union, Iterable
# local imports
#? NOTE: may end moving these defaults to the files where they're actually used most
from .figure_defaults import ConstFigureDefaults


def disable_all_axis_elements():
    """ disable all axis elements (ticks, labels, spines) globally to avoid the issues with ax.axis("off") overwriting stuff 
        - TODO: will probably need to revisit this when implementing figures to plot as an image through the data generation model
    """
    # went through hell debugging this, so this is probably the easiest solution I'm gonna get for now
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
    #? NOTE: think this varies with screen resolution - need to look into it further
    # convert from points to inches (1 point = 1/72 inch)
    width_inch  = (max_x - min_x) / 72.0
    height_inch = (max_y - min_y) / 72.0
    # convert to fraction of your main figure size
    fig_w_inch, fig_h_inch = main_fig_size
    width_fraction  = width_inch  / fig_w_inch
    height_fraction = height_inch / fig_h_inch
    #width_fraction  *= 0.7
    #height_fraction *= 0.8
    return width_fraction, height_fraction


# TODO: might remove default arguments pulled from default bounds since they're set as such in the layout manager
def compute_button_positions(num_buttons: int, left_bound = None, right_bound = None) -> List[List[float]]:
    """ Re-implement get_button_axes using figure-relative coordinates - bottom right aligned """
    def get_total_width(w: float, s: float) -> float:
        return (w + s) * num_buttons - s
    # set default bounds if not provided
    default_bounds = ConstFigureDefaults()
    left_bound = left_bound or default_bounds.BOTTOM_PANEL_LEFT
    right_bound = right_bound or default_bounds.BOTTOM_PANEL_LEFT + default_bounds.BOTTOM_PANEL_WIDTH
    width, height = default_bounds.BUTTON_WIDTH, default_bounds.BUTTON_HEIGHT
    bottom_bound = default_bounds.BOTTOM_PANEL_BOTTOM + default_bounds.AXES_PADDING
    spacing = default_bounds.BUTTON_SPACING
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
        # create buttons starting from the right boundary - meaning positions are ordered from right to left
        left = right_bound - (i+1) * (width + spacing)
        # keep the bottom at 0.025 and the height at 0.075 so that the top of the buttons are all at 0.1
        positions.append([left, bottom_bound, width, height])
    return positions


def ensure_list(var: Union[float, int, List[float], List[int]]) -> Union[List[float], List[int]]:
    """ ensures that the given variable is a list of floats or ints (for setting axis position) """
    if not isinstance(var, Iterable):
        var = [var]
    assert len(var) <= 4, f"Position vector ({var}) must be of length 4 or less"
    return var