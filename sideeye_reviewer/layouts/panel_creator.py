from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
import matplotlib.pyplot as plt
from numpy import ndarray as NDarray
# local imports
from .axes_data import PanelData, AxesData


def get_axes_list(axes: Union[plt.Axes, List[plt.Axes], NDarray]) -> List[plt.Axes]:
    """ helper function to ensure that the axes are returned as a list of Axes objects """
    if not isinstance(axes, (list, NDarray)) and isinstance(axes, plt.Axes):
        axes = [axes]
    elif isinstance(axes, NDarray) and axes.ndim > 1:
        axes = axes.flatten()  # ensure axes is a 1D list of Axes objects
    # may still want to generalize this function further and assign axes to the panel's axes_items list
    return list(axes)

class PanelLayoutCreator:
    """
        Creates a two-row nested subfigure layout:
            - Top row can have [left, main, right] subfigures (some optional)
            - Bottom row can have [bottom_left, bottom, bottom_right] subfigures (some optional)
        The 'main' and 'bottom' panels are mandatory and occupy at least 1 column each.
        All panels are stored in self._panels, keyed by name.
    """
    def __init__(
        self,
        panel_data_dict: Dict[str, Union[PanelData, None]],
        fig_size=(12, 7)
    ):
        self.fig_size = fig_size
        #? NOTE: planning to set the widths and heights, etc upstream in the layout manager
        self.use_panels: Dict[str, bool] = self._get_present_panels(panel_data_dict)
        self._panels: Dict[str, PanelData] = {name: panel for name, panel in panel_data_dict.items() if self.use_panels[name]}
        # create the figure then the top & bottom subfigs
        self._fig = plt.figure(figsize=self.fig_size)
        # always 2 rows: top row for [left, main, right], bottom row for [bottom_left, bottom, bottom_right]
        self.top_subfig, self.bottom_subfig = self._fig.subfigures(
            nrows=2, ncols=1,
            height_ratios=[self._panels["main"].height, self._panels["bottom"].height],
        )
        # build the top row subfigures
        self._build_subfigure_row("top", ["left", "main", "right"])
        # build the bottom row subfigures
        self._build_subfigure_row("bottom", ["bottom_left", "bottom", "bottom_right"])


    def _get_present_panels(self, panel_data_dict: Dict[str, Union[PanelData, None]]) -> Dict[str, bool]:
        """ returns a dictionary of named keys with boolean values indicating if the panel is present in the layout """
        use_panels = {name: p is not None for name, p in panel_data_dict.items()}
        # ensure that the mandatory panels are always added
        if "main" not in use_panels or not use_panels["main"]:
            raise RuntimeError("Mandatory panel 'main' (for images) is not present in the layout.")
        if "bottom" not in use_panels or not use_panels["bottom"]:
            raise RuntimeError("Mandatory panel 'bottom' (for buttons) is not present in the layout.")
        return use_panels

    def _build_subfigure_row(self, row_name: str, panel_names: List[str]) -> None:
        """ helper function to build a subfigure row with the given panel names """
        #? NOTE: widths are normalized by default so this should never make overlapping subfigures
        print("self.use_panels:", self.use_panels)
        subfig_widths = [self._panels[name].width for name in panel_names if self.use_panels[name]]
        row_subfigs = getattr(self, f"{row_name}_subfig").subfigures(nrows=1, ncols=len(subfig_widths), width_ratios=subfig_widths)
        col_idx = 0
        for panel_name in panel_names:
            if self.use_panels[panel_name]:
                row_subfig = row_subfigs if len(subfig_widths) == 1 else row_subfigs[col_idx]
                self._add_subpanel(panel_name, row_subfig)
                col_idx += 1

    def _add_subpanel(self, name: str, subsubfig: plt.Figure) -> None:
        """ helper function to add a subpanel to the given subfigure """
        self._panels[name].initialize_subfigure(subsubfig)  # set the subfigure for the panel


    # TODO: determine if I should pass all the AxesData attributes via subplot_kwargs or use the new `AxesData.initialize_axes` method to set them after creation
    def create_image_axes(self, nrows=1, ncols=1, **subplot_kwargs) -> Union[plt.Axes, List[plt.Axes]]:
        """ example helper that places a grid of Axes for images in the 'main' panel's subfigure """
        if "main" not in self._panels:
            raise RuntimeError("No 'main' panel found in layout (this should never happen, 'main' is mandatory).")
        subfig = self._panels["main"].subfigure
        subplot_kwargs.setdefault("aspect", "auto")     # set the aspect ratio to auto for image axes
        subplot_kwargs.setdefault("adjustable", "box")  # set the adjustable to box for image axes
        # {'wspace': 0.1}
        return self.create_subplot_axes(subfig, nrows=nrows, ncols=ncols, **subplot_kwargs)  # create a grid of Axes for images

    def create_button_axes(self, nrows=1, ncols=1, **subplot_kwargs) -> Union[plt.Axes, List[plt.Axes]]:
        """ example helper that places a grid of Axes for buttons in the 'bottom' panel's subfigure """
        if "bottom" not in self._panels:
            raise RuntimeError("No 'bottom' panel found in layout (this should never happen, 'bottom' is mandatory).")
        subfig = self._panels["bottom"].subfigure
        # TODO: may need to rethink this if I want buttons right-aligned, but there may be a subplots kwarg for that
        #? just testing this anchor value to see if it can right-align the buttons - remove if it gives any problems:
        subplot_kwargs.setdefault("anchor", "E")  # set the anchor to the east (right) side of the subfigure
        return self.create_subplot_axes(subfig, nrows=nrows, ncols=ncols, **subplot_kwargs)  # create a grid of Axes for buttons


    # TODO: pass AxesData object rather than the kwargs when I figure out what I want to do?
    def create_single_axes(self, subfig: plt.Figure, **subplot_kwargs) -> plt.Axes:
        axes: Union[plt.Axes, List[plt.Axes]] = subfig.add_axes(**subplot_kwargs)
        return get_axes_list(axes)  # ensure that the axes are returned as a list of Axes objects

    def create_subplot_axes(self, subfig: plt.Figure, nrows=1, ncols=1, **subplot_kwargs) -> Union[plt.Axes, List[plt.Axes]]:
        axes: Union[plt.Axes, List[plt.Axes]] = subfig.subplots(nrows=nrows, ncols=ncols, subplot_kw=subplot_kwargs)
        return get_axes_list(axes)


    def get_panel(self, name: str) -> Optional[PanelData]:
        """ return the PanelData instance for a given panel name, or None if not present """
        return self._panels.get(name, None)

    # think a static factory method to return fig and panels may not be the right way to go since I may need to access the fig and row subfigures directly later

    @property
    def fig(self) -> plt.Figure:
        """ return the main figure for the layout """
        return self._fig

    @property
    def panels(self) -> Dict[str, PanelData]:
        """ return the dictionary of all panels that were actually created """
        return self._panels