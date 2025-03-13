from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
# global constants for heights/widths that are unlikely to change but may be adjusted by the layout manager
from .figure_defaults import ConstAxesDefaults


def ensure_all_args_set(defaults: Dict[str, Union[float, str]], left: float, bottom: float, width: float, height: float, **kwargs):
    """ helper function to ensure that all arguments are set """
    if left is None and 'left' not in kwargs:
        left = defaults.pop('left')
    if bottom is None and 'bottom' not in kwargs:
        bottom = defaults.pop('bottom')
    if width is None and 'width' not in kwargs:
        width = defaults.pop('width')
    if height is None and 'height' not in kwargs:
        height = defaults.pop('height')
    return left, bottom, width, height

def ensure_all_kwargs_set(defaults: Dict[str, Union[float, str]], kwargs):
    """ helper function to ensure that all arguments are set """
    for key, value in defaults.items():
        if key not in kwargs:
            kwargs[key] = value
    return kwargs


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
    title: Optional[str] = None
    title_size: Optional[Union[int, str]] = "large"
    axes: plt.Axes = None



#@dataclass
class CheckboxAxesData(AxesData):
    """ for storing checkboxes axes info """
    DEFAULT_KWARGS = ConstAxesDefaults.get_checkbox_defaults()
    def __init__(self, left=None, bottom=None, width=None, height=None, **kwargs):
        # args = ensure_all_args_set(self.DEFAULT_KWARGS, left, bottom, width, height, **kwargs)
        # kwargs = ensure_all_kwargs_set(self.DEFAULT_KWARGS, kwargs)
        # super().__init__("checkboxes", *args, **kwargs)
        left, bottom, width, height, kwargs = ensure_all_args_and_kwargs_set(
            self.DEFAULT_KWARGS,
            left=left,
            bottom=bottom,
            width=width,
            height=height,
            **kwargs
        )
        print(f"CheckboxAxesData kwargs: left={left}, bottom={bottom}, width={width}, height={height}, {kwargs}")
        super().__init__("checkboxes", left, bottom, width, height, **kwargs)


#@dataclass
class SummaryAxesData(AxesData):
    """ for storing summary box axes info """
    DEFAULT_KWARGS = ConstAxesDefaults.get_summary_defaults()
    def __init__(self, left=None, bottom=None, width=None, height=None, **kwargs):
        # args = ensure_all_args_set(self.DEFAULT_KWARGS, left, bottom, width, height, **kwargs)
        # kwargs = ensure_all_kwargs_set(self.DEFAULT_KWARGS, kwargs)
        # super().__init__("summary", *args, **kwargs)
        left, bottom, width, height, kwargs = ensure_all_args_and_kwargs_set(
            self.DEFAULT_KWARGS,
            left=left, bottom=bottom,
            width=width,
            height=height,
            **kwargs
        )
        print(f"SummaryAxesData kwargs: left={left}, bottom={bottom}, width={width}, height={height}, {kwargs}")
        super().__init__("summary", left, bottom, width, height, **kwargs)

class LegendAxesData(AxesData):
    """ for storing legend axes info """
    DEFAULT_KWARGS = ConstAxesDefaults.get_legend_defaults()
    def __init__(self, left=None, bottom=None, width=None, height=None, **kwargs):
        # args = ensure_all_args_set(self.DEFAULT_KWARGS, left, bottom, width, height, **kwargs)
        # kwargs = ensure_all_kwargs_set(self.DEFAULT_KWARGS, kwargs)
        # super().__init__("legend", *args, **kwargs)
        left, bottom, width, height, kwargs = ensure_all_args_and_kwargs_set(
            self.DEFAULT_KWARGS,
            left=left,
            bottom=bottom,
            width=width,
            height=height,
            **kwargs
        )
        print(f"LegendAxesData kwargs: left={left}, bottom={bottom}, width={width}, height={height}, {kwargs}")
        super().__init__("legend", left, bottom, width, height, **kwargs)


class ButtonAxesData(AxesData):
    """ for storing button axes info """
    DEFAULT_KWARGS = ConstAxesDefaults.get_button_defaults()
    def __init__(self, left=None, bottom=None, width=None, height=None, **kwargs):
        # if (left is None and "left" not in kwargs) or (bottom is None and "bottom" not in kwargs):
        #     raise ValueError("ButtonAxesData must at the least be instantiated with 'left' and 'bottom'.")
        # args = ensure_all_args_set(self.DEFAULT_KWARGS, left, bottom, width, height, **kwargs)
        # kwargs = ensure_all_kwargs_set(self.DEFAULT_KWARGS, kwargs)
        # super().__init__("buttons", *args, **kwargs)
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
        print(f"ButtonAxesData kwargs: left={left}, bottom={bottom}, width={width}, height={height}, {kwargs}")
        super().__init__("buttons", left, bottom, width, height, **kwargs)


# TODO: create ImageAxesData class for storing image axes info - handling default subplot adjustment for now
class ImageAxesData(AxesData):
    """ for storing image axes info """
    # TODO: add non-positional default arguments for things like color, alpha, title, etc
    def __init__(self, ax: plt.Axes = None, **kwargs):
        if ax is None:
            raise ValueError("ImageAxesData must be instantiated with an existing plt.Axes object")
        pos = ax.get_position().bounds
        kwargs.update({"left": pos[0], "bottom": pos[1], "width": pos[2], "height": pos[3]})
        print(f"ImageAxesData kwargs: {kwargs}")
        super().__init__("image", axes = ax, **kwargs)

