from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
#from dataclasses import dataclass, field
import matplotlib.pyplot as plt
# local imports
from .axes_wrappers import AxesData, PanelData #, ButtonAxesData, ImageAxesData


# TODO: add new dataclasses (maybe as FigureElementLike) and PaneledFigureWrapper to types.py


# TODO: strip out any code blocks related to the dynamic sizing of the figure and handle that in the manager
class PaneledFigureWrapper:
    """
        Creates a two-row nested subfigure layout:
            - Top row can have [left, main, right] subfigures (some optional)
            - Bottom row can have [bottom_left, bottom, bottom_right] subfigures (some optional)
        The 'main' and 'bottom' panels are mandatory and occupy at least 1 column each.
        All panels are stored in self._panels, keyed by name.
    """
    # defining this constant here to easily locate and edit it in the future
    supported_panels = {
        "top": ["left", "main", "right"],
        "bottom": ["bottom_left", "bottom", "bottom_right"],
    }
    def __init__(self, fig_size=(12, 7)):
        self.fig_size = fig_size
        # initialized as empty, panels are populated by the manager, then it's filtered further in create_paneled_figure()
        self._panels: Dict[str, PanelData] = {}
        # initialize the use_panels dictionary to False for all supported panels and set incrementally
        self.panel_is_set = {name: False for name in self.supported_panels["top"] + self.supported_panels["bottom"]}
        #? NOTE: the way the manager is set up requires this object to exist, but it would have no panels initially
            # continue writing to self._panels which is initially empty, then filter it like below later


    def create_paneled_figure(self) -> None:
        """ Phase 1: create the main figure and subfigures for each panel based on dictionary created in the manager """
        if len(self._panels) == 0:
            raise RuntimeError("No panels defined. Please add panels before creating the main figure.")
        #self.panel_wrapper = PanelLayoutCreator(self.panels)
        self.panel_is_set: Dict[str, bool] = self._get_present_panels()
        self._panels: Dict[str, PanelData] = {name: panel for name, panel in self._panels.items() if self.panel_is_set[name]}
        # create the figure then the top & bottom subfigs
        self._fig = plt.figure(figsize=self.fig_size)
        # always 2 rows: top row for [left, main, right], bottom row for [bottom_left, bottom, bottom_right]
        self.top_subfig, self.bottom_subfig = self._fig.subfigures(
            nrows=2, ncols=1,
            height_ratios=[self._panels["main"].height, self._panels["bottom"].height],
        )
        # build the top row subfigures then bottom row subfigures
        for row_name, panel_names in self.supported_panels.items():
            self._build_subfigure_row(row_name, panel_names)
        # draw borders around the panels for visual separation
        self._draw_panel_borders()


    def _draw_panel_borders(self):
        for panel in self._panels.values():
            rect = plt.Rectangle((0,0), 1, 1, edgecolor="black", fill=False, clip_on=False, lw=2)
            panel.subfigure.add_artist(rect, clip=True)


    def _get_present_panels(self) -> Dict[str, bool]:
        """ returns a dictionary of named keys with boolean values indicating if the panel is present in the layout """
        use_panels = {name: p is not None for name, p in self._panels.items()}
        # ensure that the mandatory panels are always added and that they weren't passed as NoneType
        if "main" not in use_panels or not use_panels["main"]:
            raise RuntimeError("Mandatory panel 'main' (for images) is not present in the layout.")
        if "bottom" not in use_panels or not use_panels["bottom"]:
            raise RuntimeError("Mandatory panel 'bottom' (for buttons) is not present in the layout.")
        return use_panels

    def _build_subfigure_row(self, row_name: str, panel_names: List[str]) -> None:
        """ helper function to build a subfigure row with the given panel names """
        #? NOTE: widths are normalized by default so this should never make overlapping subfigures
        subfig_widths = [self._panels[name].width for name in panel_names if self.panel_is_set[name]]
        #? NOTE: pretty sure the implicit width normalization is what causes top and bottom borders to be misaligned when the list lengths are different
        #print("subfig_widths: ", subfig_widths)
        row_subfigs = getattr(self, f"{row_name}_subfig").subfigures(nrows=1, ncols=len(subfig_widths), width_ratios=subfig_widths)
        col_idx = 0
        for panel_name in panel_names:
            if self.panel_is_set[panel_name]:
                row_subfig = row_subfigs if len(subfig_widths) == 1 else row_subfigs[col_idx]
                self._add_subpanel(panel_name, row_subfig)
                col_idx += 1

    def _add_subpanel(self, name: str, subsubfig: plt.Figure) -> None:
        """ helper function to add a subpanel to the given subfigure """
        self._panels[name].initialize_subfigure(subsubfig)  # set the subfigure for the panel

    #########################################################################################################################
    # PANEL SETTER AND GETTER METHODS
    #########################################################################################################################

    def add_panel(self, key: str, panel: PanelData):
        """ register a panel definition (PanelData) that will be used to generate a SubFigure """
        if key not in self.supported_panels["top"] + self.supported_panels["bottom"]:
            raise ValueError(f"Panel '{key}' is not supported. Currently supported panels are: {self.supported_panels}")
        if not isinstance(panel, PanelData) and panel is not None:
            raise TypeError(f"'panel' must be an instance of PanelData or None; got {type(panel)}")
        self._panels[key] = panel
        self.panel_is_set[key] = True if panel is not None else False  # set the use_panels dictionary to True for the given key

    def add_axes_data_to_panel(self, panel_key: str, ax_data: Union[AxesData, List[AxesData]]):
        """ instead of direct 'panel.add_axes_item(...)', we expose a method here """
        if not self.panel_exists(panel_key):
            raise ValueError(f"Panel '{panel_key}' not found in the layout or not initialized")
        self._panels[panel_key].add_axes_item(ax_data)  # add the AxesData to the panel's list of axes items


    def panel_exists(self, panel_name: str) -> bool:
        #! REMOVE LATER - using the message for debugging for now
        if len(self._panels) == 0:
            raise RuntimeError("No panels defined. Please add panels before creating the main figure.")
        return panel_name in self._panels and self.panel_is_set[panel_name]

    def get_panel(self, name: str) -> Optional[PanelData]:
        """ return the PanelData instance for a given panel name, or None if not present """
        return self._panels.get(name, None)

    def get_panel_subfigure(self, panel_name: str) -> Optional[plt.Figure]:
        panel = self.get_panel(panel_name)
        #return None if panel is None else panel.subfigure
        return panel.subfigure # panel.subfigure is always set to None in the PanelData constructor

    def get_panel_axes(self, panel_name: str) -> Optional[List[AxesData]]:
        panel = self.get_panel(panel_name)
        return None if panel is None else panel.axes_items #[axes_label]  #? NOTE: this is a list of AxesData objects


    def get_initialized_panel(self, name: str) -> PanelData:
        """ return the PanelData instance for a given panel name, or raise an error if not present or not initialized """
        panel = self.get_panel(name)
        if panel is None:
            raise ValueError(f"Panel '{name}' not found in layout.")
        if panel.subfigure is None:
            raise ValueError(f"Panel '{name}' has no initialized subfigure.")
        return panel

    # think a static factory method to return fig and panels may not be the right way to go since I may need to access the fig and row subfigures directly later

    @property
    def fig(self) -> plt.Figure:
        """ return the main figure for the layout """
        return self._fig

    @property
    def panels(self) -> Dict[str, PanelData]:
        """ return the dictionary of all panels that were actually created """
        return self._panels

    @property
    def images(self) -> List[AxesData]:
        """ return the list of AxesData objects for images in the 'main' panel """
        return self.get_panel("main").axes_items

    @property
    def buttons(self) -> List[AxesData]:
        """ return the list of AxesData objects for buttons in the 'bottom' panel """
        return self.get_panel("bottom").axes_items




