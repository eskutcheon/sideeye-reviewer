from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
import numpy as np
# global constants for heights/widths that are unlikely to change but may be adjusted by the layout manager
from .figure_defaults import ConstAxesDefaults


def ensure_all_args_and_kwargs_set(defaults: Dict[str, Union[float, str]], **kwargs) -> Tuple[float, float, float, float, Dict[str, Union[float, str]]]:
    """ Helper function to ensure that all arguments are set, giving precedence to kwargs """
    # pop values from the dict if they're present in kwargs, otherwise use defaults; overwrite with defaults regardless if kwargs[key] is None
    left = kwargs.pop('left', defaults.get('left')) or defaults.get('left')
    bottom = kwargs.pop('bottom', defaults.get('bottom')) or defaults.get('bottom')
    width = kwargs.pop('width', defaults.get('width')) or defaults.get('width')
    height = kwargs.pop('height', defaults.get('height')) or defaults.get('height')
    # Update kwargs with any remaining defaults
    for key, value in defaults.items():
        if key not in kwargs and key not in ['left', 'bottom', 'width', 'height']:
            kwargs[key] = value
    return left, bottom, width, height, kwargs


@dataclass
class AxesData:
    """ Data structure for storing information about the axes in a figure """
    label: str
    #* WARNING: Note the difference between using width and height here vs right and top bounds in PanelData.
    left: float
    bottom: float
    width: float
    height: float
    color: Optional[str] = "white"
    alpha: Optional[float] = 1.0  # transparency of the axes background
    use_border: Optional[bool] = False  # whether to draw a border around the axes
    title: Optional[str] = None
    title_size: Optional[Union[int, str]] = "large"
    axes: plt.Axes = None
    parent: plt.Figure = None  # the parent (sub)figure of the axes

    def initialize_axes(self, ax: plt.Axes):
        """ set the facecolor and alpha for the axes """
        if self.color:
            ax.set_facecolor(self.color)
        if self.alpha < 1.0:
            ax.set_alpha(self.alpha)
        if self.title:
            ax.set_title(self.title, fontsize=self.title_size)
        if self.use_border:
            rect = plt.Rectangle((0, 0), 1, 1, edgecolor="black", fill=False, lw=1, clip_on = False) #, transform=ax.transAxes)
            ax.add_artist(rect)
            #ax.patch.set_edgecolor("black")
            #ax.patch.set_linewidth(20)
        self.axes = ax  # set the axes for the data

    def update_position(self, left: float, bottom: float, width: float, height: float):
        """ update the position of the axes """
        self.left = left
        self.bottom = bottom
        self.width = width
        self.height = height

    def __repr__(self):
        attr = ", ".join(f"{k}={v}" for k, v in self.__dict__.items())
        return f"AxesData({attr})"


@dataclass
class PanelData:
    name: str
    left: float
    bottom: float
    width: float
    height: float
    facecolor: Optional[str] = "white"  # background color of the panel
    alpha: Optional[float] = 1.0
    title: Optional[str] = None
    title_size: Optional[Union[int, str]] = "large"
    # the primary object that this class is meant to wrap - "panels" are subfigures of the main figure, created by the layout manager
    subfigure: Optional[plt.Figure] = None
    # list of AxesData to place in second phase of the layout creation
    axes_items: List[AxesData] = field(default_factory=list)

    def add_axes_item(self, ax_data: Union[AxesData, List[AxesData]]):
        """ add one or more AxesData object to the panel """
        if not isinstance(ax_data, list):
            ax_data = [ax_data]
        for ax in ax_data:
            if not issubclass(type(ax), AxesData):
                raise TypeError(f"Expected AxesData object, got {type(ax)}")
            self.axes_items.append(ax)
            ax.parent = self.subfigure  # set the parent (sub)figure of the axes

    def get_position(self) -> Tuple[float, float, float, float]:
        return self.left, self.bottom, self.width, self.height

    def initialize_subfigure(self, subfig: plt.Figure):
        subfig.set_facecolor(self.facecolor)  # set the facecolor for the subfigure
        if self.alpha < 1.0:
            subfig.patch.set_alpha(self.alpha)
        if self.title:
            subfig.suptitle(self.title, fontsize=self.title_size)
        self.subfigure = subfig  # set the subfigure for the panel

    def rescale_axes(self, ax_data: AxesData):
        """ Rescale the axes to fit within the panel's bounding box """
        # get the (subfigure) panel's position in the main figure
        panel_left, panel_bottom, panel_width, panel_height = self.get_position()
        # adjust the axes' position relative to the panel
        ax_data.left = (ax_data.left - panel_left) / panel_width
        ax_data.bottom = (ax_data.bottom - panel_bottom) / panel_height
        # rescale the axes' width and height relative to the panel
        ax_data.width /= panel_width
        ax_data.height /= panel_height



class CheckboxAxesData(AxesData):
    """ for storing checkboxes axes info """
    DEFAULT_KWARGS = ConstAxesDefaults.get_checkbox_defaults()
    def __init__(self, left=None, bottom=None, width=None, height=None, **kwargs):
        left, bottom, width, height, kwargs = ensure_all_args_and_kwargs_set(
            self.DEFAULT_KWARGS,
            left=left,
            bottom=bottom,
            width=width,
            height=height,
            **kwargs
        )
        super().__init__("checkboxes", left, bottom, width, height, **kwargs)


class SummaryAxesData(AxesData):
    """ for storing summary box axes info """
    DEFAULT_KWARGS = ConstAxesDefaults.get_summary_defaults()
    def __init__(self, left=None, bottom=None, width=None, height=None, **kwargs):
        left, bottom, width, height, kwargs = ensure_all_args_and_kwargs_set(
            self.DEFAULT_KWARGS,
            left=left, bottom=bottom,
            width=width,
            height=height,
            **kwargs
        )
        super().__init__("summary", left, bottom, width, height, **kwargs)

class LegendAxesData(AxesData):
    """ for storing legend axes info """
    DEFAULT_KWARGS = ConstAxesDefaults.get_legend_defaults()
    def __init__(self, left=None, bottom=None, width=None, height=None, **kwargs):
        left, bottom, width, height, kwargs = ensure_all_args_and_kwargs_set(
            self.DEFAULT_KWARGS,
            left=left,
            bottom=bottom,
            width=width,
            height=height,
            **kwargs
        )
        super().__init__("legend", left, bottom, width, height, **kwargs)


class ButtonAxesData(AxesData):
    """ for storing button axes info """
    DEFAULT_KWARGS = ConstAxesDefaults.get_button_defaults()
    def __init__(self, left=None, bottom=None, width=None, height=None, **kwargs):
        if left is None or bottom is None:
            # UPDATE: think I shouldn't have to check the kwargs here since they wouldn't be in kwargs without a duplicate argument error
            raise ValueError("ButtonAxesData must at the least be instantiated with 'left' and 'bottom'.")
        left, bottom, width, height, kwargs = ensure_all_args_and_kwargs_set(
            self.DEFAULT_KWARGS,
            left=left,
            bottom=bottom,
            width=width,
            height=height,
            **kwargs
        )
        super().__init__("buttons", left, bottom, width, height, **kwargs)


#** may not use this anyway since the new panel layout creator is using subplots
class ImageAxesData(AxesData):
    """ for storing image axes info """
    def __init__(self, ax: plt.Axes = None, **kwargs):
        if ax is None:
            raise ValueError("ImageAxesData must be instantiated with an existing plt.Axes object")
        pos = ax.get_position().bounds
        kwargs.update({"left": pos[0], "bottom": pos[1], "width": pos[2], "height": pos[3]})
        super().__init__("image", **kwargs)
        self.initialize_axes(ax)  # set the facecolor and alpha for the axes

