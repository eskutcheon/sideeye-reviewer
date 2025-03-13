from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
# local imports
#from .figure_defaults import ConstFigureDefaults
from .axes_data import AxesData, ButtonAxesData, ImageAxesData


# TODO: add new dataclasses (maybe as FigureElementLike) and PaneledFigureWrapper to types.py

@dataclass
class PanelData:
    name: str
    left: float
    bottom: float
    #!! FIXME: disparity from the defaults which define width and height instead of the right and top bounds
    #!! simplest solution will be to change these to width and height to accept the arguments but adjust it in PaneledFigureWrapper
    width: float
    height: float
    #! facecolor: Optional[str] = "white"
    facecolor: Optional[str] = "white"  # background color of the panel
    alpha: Optional[float] = 1.0
    title: Optional[str] = None
    title_size: Optional[Union[int, str]] = "large"
    # the primary object that this class is meant to wrap - "panels" are subfigures of the main figure, created by the layout manager
    subfigure: Optional[plt.Figure] = None
    grid_idx: Optional[Tuple[int, int]] = None
    fig_idx: Optional[int] = None  # index of the subfigure in the main figure's subfigures array
    # list of AxesData to place in second phase of the layout creation
    axes_items: List[AxesData] = field(default_factory=list)

    def add_axes_item(self, ax_data: AxesData):
        self.axes_items.append(ax_data)

    def get_position(self) -> Tuple[float, float, float, float]:
        return self.left, self.bottom, self.width, self.height

    def set_subfig(self, subfig_arr: np.ndarray[plt.Figure]): #, nrows, ncols):
        # Convert figure-relative bounding box to indices to slice the subfigure array
        # nrows, ncols = subfig_arr.shape
        # left_idx = int(self.left * ncols)
        # right_idx = max(left_idx + 1, int((self.left + self.width) * ncols))
        # bottom_idx = int(self.bottom * nrows)
        # top_idx = max(bottom_idx + 1, int((self.bottom + self.height) * nrows))
        # print(f"testing indices for {self.name}:")
        # print(f"final indices: [bottom={bottom_idx}, top={top_idx}], [left={left_idx}, right={right_idx}]")
        row_idx, col_idx = self.grid_idx
        if subfig_arr.ndim != 2:
            self.subfigure = subfig_arr[col_idx]
        else:
            self.subfigure = subfig_arr[row_idx, col_idx] #[bottom_idx:top_idx, left_idx:right_idx]



class PaneledFigureWrapper:
    """ Encapsulates the logic for:
        1) Creating a main figure,
        2) Defining panel bounding boxes (PanelData),
        3) Creating SubFigures for each panel,
        4) Adding AxesData items to each panel,
        5) Constructing actual Axes in a second phase.
    """
    # TODO: think I'd rather remove the last two arguments later but I need to get the basic structure down first
    def __init__(self, fig_size=(12, 7)):
        self.fig_size = fig_size
        self.fig: Optional[plt.Figure] = None
        # dictionaries for storing panel data & created axes references: "left", "right", "bottom", "main"
        self.panels: Dict[str, PanelData] = {}
        # nested dictionary of final Axes created
        self.created_axes: Dict[str, Dict[str, plt.Axes]] = {}
        # maybe store references to button Axes in a single list
        self.button_axes: List[plt.Axes] = []  # or store ButtonAxesData first
        self.image_axes: List[plt.Axes] = []


    def _create_all_subfigures(self, num_images: int, num_img_rows: int, num_img_cols: int) -> np.ndarray[plt.Figure]:
        """ Create a GridSpec object for the main figure with the given number of images """
        if "main" not in self.panels:
            raise RuntimeError("Main panel not yet defined for the figure layout!")
        total_columns = 1 + int(self.panel_exists("left")) + int(self.panel_exists("right"))
        total_rows = 2 # main panel and button panel
        main_panel_width = 1.0
        bottom_panel_width = 1.0
        # total_columns = num_img_cols + int(self.panel_exists("left")) + int(self.panel_exists("right"))
        # total_rows = num_img_rows + int(self.panel_exists("bottom"))
        width_ratios = []
        if "left" in self.panels:
            main_panel_width -= self.panels["left"].width
            bottom_panel_width -= self.panels["left"].width
            width_ratios.append(round(self.panels["left"].width, 3))
        #width_ratios.extend([self.panels["main"].width/num_img_cols for _ in range(num_img_cols)])
        #width_ratios.append(round(self.panels["bottom"].width, 3))
        if "right" in self.panels:
            main_panel_width -= self.panels["right"].width
            bottom_panel_width -= self.panels["right"].width
            width_ratios.append(round(self.panels["right"].width, 3))
        width_ratios.insert(int("left" in self.panels), round(main_panel_width, 3))  # main panel width
        print("width_ratios: ", width_ratios)
        height_ratios = [
            round(self.panels["main"].height, 3),
            #*[self.panels["main"].height/num_img_rows for _ in range(num_img_rows)],
            round(self.panels["bottom"].height, 3)
        ]
        print("height_ratios: ", height_ratios)
        #gs = gridspec.GridSpec(total_rows, total_columns, figure=self.fig, width_ratios=width_ratios, height_ratios=height_ratios)
        #return gs
        # think this returned a nested list of subfigures and should be indexed like a gridspec object
        return self.fig.subfigures(total_rows, total_columns, width_ratios=width_ratios, height_ratios=height_ratios)

    def create_paneled_figure(self, num_images, num_img_rows, num_img_cols):
        """ Phase 1: create figure, dynamically compute panel bounding boxes, create subfigures """
        #* double check that frameon doesn't cause problems - should be helpful to avoid the white border around the figure
        if len(self.panels) == 0:
            raise RuntimeError("No panels defined for the figure layout!")
        self.fig: plt.Figure = plt.figure(figsize=self.fig_size, frameon=False)
        subfig_grid = self._create_all_subfigures(num_images, num_img_rows, num_img_cols)
        # create subfigures for each panel
        for idx, (key, pinfo) in enumerate(self.panels.items()):
            #subplotspec = pinfo.get_subplotspec(gs, nrows, ncols)
            print(f"SUBFIGURE IDX FOR {key}: {idx}")
            print(f"PANEL IDX TO CHECK FOR DUPLICATES: ", pinfo.grid_idx)
            print(f"SUBFIGURE (INTENDED) POSITION FOR {key}: {pinfo.get_position()}")
            pinfo.set_subfig(subfig_grid)
            # track order of addition to the subfigures array for reference from the main figure's `subfigs` attribute later
            pinfo.fig_idx = idx
            #pinfo.subfigure.patch.set_facecolor(pinfo.facecolor)
            pinfo.subfigure.set_facecolor(pinfo.facecolor)
            print(f"(ACTUAL) {key} panel (left, bottom, width, height): {pinfo.subfigure.get_window_extent()}")
            if pinfo.alpha < 1.0:
                pinfo.subfigure.patch.set_alpha(pinfo.alpha)
            if pinfo.title:
                pinfo.subfigure.suptitle(pinfo.title, fontsize=pinfo.title_size)
            #pinfo.subfigure = subfig
            if pinfo.name == "main":
                self.create_image_axes(subfig_grid, num_images, num_img_rows, num_img_cols)
        # from pprint import pprint
        # pprint(vars(self.fig), indent=3)

    def create_image_axes(self, subfig_grid: np.ndarray[plt.Figure], num_images, num_img_rows, num_img_cols) -> List[plt.Axes]:
        """ Call after main panel initialization to add image axes to subplots in the main subfigure """
        if "main" not in self.panels:
            raise RuntimeError("Main panel not yet defined for the figure layout!")
        main_panel = self.panels["main"]
        #nrows, ncols = subfig_grid.shape
        # img_axes = self.fig.subplots(num_img_rows, num_img_cols, gridspec_kw={
        #     'wspace': 0.1,
        #     'left': main_panel.left,
        #     'bottom': main_panel.bottom,
        #     'top': main_panel.bottom + main_panel.height,
        #     'right': main_panel.left + main_panel.width
        # })
        img_axes = main_panel.subfigure.subplots(
            num_img_rows,
            num_img_cols,
            # width_ratios = [image_ax_width] * num_img_cols,
            # height_ratios = [image_ax_height] * num_img_rows,
            gridspec_kw = {'wspace': 0.1} #, 'hspace': 0.1}
        )
        img_axes: List[plt.Axes] = img_axes.flatten() if isinstance(img_axes, Iterable) else [img_axes]
        for i in range(num_images):
            img_axes[i].set_aspect("auto", adjustable="box")
            self.image_axes.append(img_axes[i])
            self.add_axes_data_to_panel("main", ImageAxesData(ax=img_axes[i]))
        # hide any unused image axes
        for ax in img_axes[num_images:]:
            ax.set_visible(False)

    def place_figure_elements(self):
        """ Phase 2: create Axes in each subfigure from stored AxesData. and handle 'button_axes' in a list """
        for pname, panel in self.panels.items():
            if not panel.subfigure:
                continue
            self.created_axes[pname] = {}
            # place each AxesData object
            for ax_data in panel.axes_items:
                ax = ax_data.axes
                if ax is None:
                    # normalization since the axes would be working off of the relative subfigure dims
                    if pname == "right":
                        self.rescale_axes_in_panel(pname, ax_data)
                    ax: plt.Axes = panel.subfigure.add_axes([ax_data.left, ax_data.bottom, ax_data.width, ax_data.height])
                ax.set_facecolor(ax_data.color)
                if ax_data.alpha < 1.0:
                    ax.patch.set_alpha(ax_data.alpha)
                if ax_data.title:
                    ax.set_title(ax_data.title, fontsize=ax_data.title_size)
                if isinstance(ax_data, ButtonAxesData):
                    # store in self.button_axes instead of the nested dictionary
                    self.button_axes.append(ax)
                elif isinstance(ax_data, ImageAxesData):
                    #? NOTE: axes already exists in self.image_axes - this is just to set extra elements like color, alpha, title, etc
                    pass
                else:
                    self.created_axes[pname][ax_data.label] = ax

    def add_panel(self, key: str, panel: PanelData):
        """ register a panel definition (PanelData) that will become a SubFigure """
        if isinstance(panel, PanelData):
            self.panels[key] = panel
        else:
            raise TypeError("'panel' must be an instance of PanelData")

    def panel_exists(self, panel_name: str) -> bool:
        return panel_name in self.panels

    def get_panel_dims(self, panel_name: str) -> Tuple[float, float, float, float]:
        if panel_name not in self.panels:
            return None
        panel_ptr = self.panels[panel_name]
        return panel_ptr.left, panel_ptr.bottom, panel_ptr.width, panel_ptr.height

    def add_axes_data_to_panel(self, panel_key: str, ax_data: AxesData):
        """ instead of direct 'panel.add_axes_item(...)', we expose a method in the manager """
        if panel_key not in self.panels:
            raise ValueError(f"Panel '{panel_key}' not found in the layout")
        self.panels[panel_key].axes_items.append(ax_data)

    def get_axes(self, panel_name: str, axes_label: str) -> Union[plt.Axes, List[plt.Axes], None]:
        """ retrieve an Axes by combining the panel name with the axes label """
        # basically self.created_axes.get(panel_name, {}).get(axes_label, None)
        try:
            #? NOTE: returns a list of axes objects in the case that axes_label == "buttons"
            return self.created_axes[panel_name][axes_label]
        except KeyError:
            return None

    def rescale_axes_in_panel(self, panel_name: str, ax_data: AxesData):
        """ Rescale the axes to fit within the panel's bounding box """
        # TODO: might want to refactor this to iterate over all axes in the panel and rescale them
        try:
            panel = self.panels[panel_name]
        except KeyError:
            raise ValueError(f"Panel '{panel_name}' not found in the layout")
        if not panel.subfigure:
            raise RuntimeError(f"Subfigure for panel '{panel_name}' not yet created")
        # FIXME: should be using the axes' relative position
        width_prop = ax_data.width/panel.width
        height_prop = ax_data.height/panel.height
        ax_data.left = (ax_data.left - panel.left) * width_prop
        ax_data.bottom = (ax_data.bottom - panel.bottom) * height_prop
        ax_data.width = width_prop # *= ax_data.left/prev_left
        ax_data.height = height_prop # *= ax_data.bottom/prev_bottom

    @property
    def images(self) -> List[plt.Axes]:
        return self.image_axes

    @property
    def buttons(self) -> List[plt.Axes]:
        return self.button_axes

    @property
    def main_figure(self):
        return self.fig




