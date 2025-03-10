from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
from dataclasses import dataclass, field
import matplotlib.pyplot as plt


# global constants for heights/widths that are unlikely to change but may be adjusted by the layout manager
BUTTON_HEIGHT = 0.075
BUTTON_PANEL_LEFT = 0.2
AXES_PADDING = 0.01
RIGHT_PANEL_WIDTH = 0.15



def ensure_list(var: Union[float, int, List[float], List[int]]) -> Union[List[float], List[int]]:
    """ ensures that the given variable is a list of floats or ints (for setting axis position) """
    if not isinstance(var, Iterable):
        var = [var]
    assert len(var) <= 4, f"Variable ({var}) must be of length 4 or less"
    return var



class AxesData:
    """ Data structure for storing information about the axes in a figure """
    ax_pos: List[float]
    label: str = ""
    color: str = None
    alpha: float = 1.0
    title: str = None
    title_size: Union[int, str] = "large"
    visible: bool = True

    # repeated logic for some axes creation methods
    def create_axes_object(self, fig: plt.Figure) -> plt.Axes:
        ax: plt.Axes = fig.add_axes(self.ax_pos)  # create a new Axes object with the given rectangle
        if self.color is not None:
            ax.set_facecolor(self.color)  # just to visualize
        else:
            ax.set_facecolor("none")
        if self.alpha != 1.0:
            ax.patch.set_alpha(self.alpha)
        if self.title:
            ax.set_title(self.title, fontsize=self.title_size)
        return ax

    def set_ax_pos(self, pos: Union[float, List[float]], idx = Union[int, List[int]]):
        """ sets the position of the axes in the figure """
        ensure_list(pos)
        ensure_list(idx)
        assert len(pos) == len(idx), f"Length of position list ({len(pos)}) does not match length of index list ({len(idx)})"
        for i, p in zip(idx, pos):
            self.ax_pos[i] = p


@dataclass
class LegendAxesData(AxesData):
    """ Data structure for storing information about the legend axes in a figure """
    # default ax_pos - should be edited by the layout manager
    ax_pos: List[float] = field(default_factory = lambda: [AXES_PADDING, AXES_PADDING, 0.2 - AXES_PADDING, 0.1 - AXES_PADDING])
    label: str = "legend"
    color: str = "gray"
    alpha: float = 0.0
    title: str = "Legend"
    title_size: str = "large"
    visible = True
    # not sure if I'm going to use this since ax_pos will be set by the layout manager
    loc: str = "lower left"



@dataclass
class ButtonPanelAxesData(AxesData):
    """ Data structure for storing information about the button panel axes in a figure """
    # default ax_pos - height should be constant (one row of buttons + padding), width may be adjusted by the layout manager
    ax_pos: List[float] = field(default_factory = lambda: [
        BUTTON_PANEL_LEFT,
        0.0,
        1 - BUTTON_PANEL_LEFT - AXES_PADDING,
        BUTTON_HEIGHT + 2*AXES_PADDING])
    label = "button_panel"
    color = "blue" #"skyblue"
    alpha = 0.5
    title = None
    visible = True


@dataclass
class ButtonAxesData(AxesData):
    """ Data structure for storing information about the button axes in a figure """
    # default ax_pos - should be edited by the layout manager
    ax_pos: List[float] = field(default_factory = lambda: [
        BUTTON_PANEL_LEFT + AXES_PADDING,
        AXES_PADDING,
        0.1,
        BUTTON_HEIGHT])
    label = "buttons"
    color = "#eeeeee"
    alpha = 1.0
    title = None
    visible = True


@dataclass
class CheckboxAxesData(AxesData):
    """ Data structure for storing information about the checkboxes axes in a figure """
    # default ax_pos - bottom set to slightly above the button panel (height needs to be adjusted)
    ax_pos: List[float] = field(default_factory = lambda: [0.8, BUTTON_HEIGHT + 2*AXES_PADDING, RIGHT_PANEL_WIDTH, 0.3])
    label = "checkboxes"
    color = "lightgray"
    alpha = 1.0
    title = "Checkbox Labels"
    title_size = "large"
    visible = True

@dataclass
class SummaryAxesData(AxesData):
    """ Data structure for storing information about the summary axes in a figure """
    # default ax_pos - bottom set to slightly above the button panel (assuming no checkboxes) - height needs adjustment
    ax_pos: List[float] = field(default_factory = lambda: [0.8, BUTTON_HEIGHT + 2*AXES_PADDING, RIGHT_PANEL_WIDTH, 0.25])
    label = "summary"
    color = "lightgray"
    alpha = 1.0
    title = "Image Summary"
    title_size = "large"
    visible = True

