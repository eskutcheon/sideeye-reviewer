from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
# local imports
#from .figure_defaults import ConstFigureDefaults
from .axes_data import AxesData, ButtonAxesData, ImageAxesData, PanelData
from .panel_creator import PanelLayoutCreator


# TODO: add new dataclasses (maybe as FigureElementLike) and PaneledFigureWrapper to types.py






# TODO: think I want to strip out any code blocks related to the dynamic sizing of the figure and
    # TODO: retain this code for being a true wrapper for all subfigures and axes in the figure
class PaneledFigureWrapper:
    """ Encapsulates the logic for:
        1) Creating a main figure,
        2) Defining panel bounding boxes (PanelData),
        3) Creating SubFigures for each panel,
        4) Adding AxesData items to each panel,
        5) Constructing actual Axes in a second phase.
    """
    supported_panels = ["left", "right", "bottom_left", "bottom_right", "main", "bottom"]
    def __init__(self, fig_size=(12, 7)):
        self.fig_size = fig_size
        self.fig: Optional[plt.Figure] = None
        # dictionaries for storing panel data & created axes references: "left", "right", "bottom", "main"
        self.panels: Dict[str, PanelData] = {}
        # nested dictionary of final Axes created
        #: Dict[str, Dict[str, plt.Axes]] = {}
        # maybe store references to button Axes in a single list
        # TODO: kind of want to handle these by `created_axes` instead of separate lists, but I need to allow more flexibility in public access
        #self.button_axes: List[plt.Axes] = []  # or store ButtonAxesData first
        #self.image_axes: List[plt.Axes] = [] # still not sure if I'm keeping this or storing it elsewhere


    #? NOTE: an object of this class is created without instantiating the main figure - figure that out later depending on whether I keep this class at all
    def create_paneled_figure(self) -> None:
        """ Phase 1: create the main figure and subfigures for each panel based on dictionary created in the manager """
        if not self.panels:
            raise RuntimeError("No panels defined. Please add panels before creating the main figure.")
        self.panel_wrapper = PanelLayoutCreator(self.panels, fig_size=self.fig_size)



    def create_image_axes(self, num_images, num_img_rows, num_img_cols) -> List[plt.Axes]:
        """ Call after main panel initialization to add image axes to subplots in the main subfigure """
        if num_images > num_img_rows * num_img_cols:
            raise ValueError(f"Too many images ({num_images}) for the given grid size ({num_img_rows}x{num_img_cols})")
        img_axes = self.panel_wrapper.create_image_axes(num_img_rows, num_img_cols)
        for ax in img_axes[:num_images]:
            ax.set_aspect("auto", adjustable="box")
            axes_data = ImageAxesData(ax)
            self.add_axes_data_to_panel("main", axes_data)
        # hide any unused image axes
        for ax in img_axes[num_images:]:
            ax.set_visible(False)

    ######^ main two functions remaining to refactor:

    def place_figure_elements(self):
        """ Phase 2: create Axes in each subfigure from stored AxesData. and handle 'button_axes' in a list """
        for pname, panel in self.panels.items():
            if panel is None or panel.subfigure is None:
                continue
            # place each AxesData object
            if pname == "main":
                # TODO: might change this so that this function accepts argument to call panel_wraper.create_image_axes
                continue  # skip the main panel for now, since it has its own method for instantiation called before this
            self._create_axes(panel.axes_items, pname)
            # for ax_data in panel.axes_items:
            #     self.create_axes(ax_data, panel)  # create the Axes in the subfigure

    def _create_axes(self, ax_data_list: List[AxesData], panel_name: str) -> None:
        # if panel_name == "bottom":
        # #     #! FIXME: this isn't going to go well without specifying positions, but I need to get it working first
        # #     btn_axes = self.panel_wrapper.create_button_axes(1, len(ax_data_list))
        # #     self.add_axes_data_to_panel("bottom", btn_axes)
        #     for ax in ax_data_list:
        #         self.rescale_axes_in_panel(panel_name, ax)
        # if panel_name == "right":
        #     # ax = self.panel_wrapper.create_subplot_axes(self.panels["right"].subfigure, nrows=1, ncols=1)
        #     # ax_data_list[0].initialize_axes(ax[0])
        #     for ax in ax_data_list:
        #         self.rescale_axes_in_panel(panel_name, ax)
        #     #return
        for ax_data in ax_data_list:
            ax = ax_data.axes
            if ax is None:
                # normalization since the axes would be working off of the relative subfigure dims
                # FIXME: shouldn't have to keep this if I do the rest correctly later
                # if panel_data.name == "right":
                #     self.rescale_axes_in_panel(panel_data.name, ax_data)
                self.rescale_axes_in_panel(panel_name, ax_data)
                if panel_name == "right":
                    ax_data.height *= 0.5  # TODO: make this a constant somewhere
                ax: plt.Axes = self.panel_wrapper.create_single_axes(
                    self.panels[panel_name].subfigure, # should never be None if called from place_figure_elements
                    rect = [ax_data.left, ax_data.bottom, ax_data.width, ax_data.height]
                )
                # TODO: ax is always returned as a list of axes from the panel_wrapper - may want to rethink that
                ax_data.initialize_axes(ax[0])  # set the facecolor and alpha for the axes
    ######^

    #!! Most of these functions below could be removed and added directly to the FigureLayoutManager
        # overall, it's looking like the new PanelLayoutCreator can replace the rest

    def add_panel(self, key: str, panel: PanelData):
        """ register a panel definition (PanelData) that will be used to generate a SubFigure """
        if isinstance(panel, PanelData) or panel is None:
            self.panels[key] = panel
        else:
            raise TypeError(f"'panel' must be an instance of PanelData; got {type(panel)}")

    def panel_exists(self, panel_name: str) -> bool:
        return panel_name in self.panels and self.panels[panel_name] is not None

    def add_axes_data_to_panel(self, panel_key: str, ax_data: Union[AxesData, List[AxesData]]):
        """ instead of direct 'panel.add_axes_item(...)', we expose a method in the manager """
        if panel_key not in self.panels:
            raise ValueError(f"Panel '{panel_key}' not found in the layout")
        if isinstance(ax_data, list):
            self.panels[panel_key].axes_items.extend(ax_data)
        else:
            self.panels[panel_key].axes_items.append(ax_data)

    def get_axes(self, panel_name: str, axes_label: str) -> Union[plt.Axes, List[plt.Axes], None]:
        """ retrieve an Axes by combining the panel name with the axes label """
        # basically self.created_axes.get(panel_name, {}).get(axes_label, None)
        try:
            #? NOTE: returns a list of axes objects in the case that axes_label == "buttons"
            return self.panel_wrapper.panels[panel_name].axes_items #[axes_label]  #? NOTE: this is a list of AxesData objects
            #return self.created_axes[panel_name][axes_label]
        except KeyError:
            return None

    def get_subfigure(self, panel_name: str) -> plt.Figure:
        """ retrieve the subfigure for the given panel """
        panel = self.panels[panel_name]
        return None if panel is None else panel.subfigure

    def rescale_axes_in_panel(self, panel_name: str, ax_data: AxesData):
        """ Rescale the axes to fit within the panel's bounding box """
        # TODO: might want to refactor this to iterate over all axes in the panel and rescale them if needed
        try:
            panel = self.panels[panel_name]
        except KeyError:
            raise ValueError(f"Panel '{panel_name}' not found in the layout")
        if not panel.subfigure:
            raise RuntimeError(f"Subfigure for panel '{panel_name}' not yet created")
        # get the (subfigure) panel's position in the main figure
        panel_left, panel_bottom, panel_width, panel_height = panel.get_position()
        # adjust the axes' position relative to the panel
        ax_data.left = (ax_data.left - panel_left) / panel_width
        ax_data.bottom = (ax_data.bottom - panel_bottom) / panel_height
        # rescale the axes' width and height relative to the panel
        ax_data.width /= panel_width
        ax_data.height /= panel_height

    @property
    def images(self) -> List[plt.Axes]:
        # TODO: track down usage and replace with returning the actual plt.Axes objects rather than AxesData
        return self.panel_wrapper.panels["main"].axes_items

    @property
    def buttons(self) -> List[plt.Axes]:
        # TODO: track down usage and replace with returning the actual plt.Axes objects rather than AxesData
        return self.panel_wrapper.panels["bottom"].axes_items

    @property
    def main_figure(self):
        return self.panel_wrapper.fig




