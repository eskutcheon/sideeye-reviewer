import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable, Any
# local imports
from .utils import disable_all_axis_elements
from .axes_wrappers import AxesData, ButtonAxesData, ImageAxesData, PanelData
from .figure_wrapper import PaneledFigureWrapper
from .figure_defaults import ConstFigureDefaults, SUPPORTED_PANEL_NAMES
from .axes_manager import AxesCreationManager


class FigureLayoutManager:
    """ layout manager for setting up the paneled figure and dynamically adjusting the subfigures and axes
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
        # TODO: ensure that I check that num_images is nonzero in the view classes
        if num_images > self.MAX_IMG_PER_FIGURE:
            raise ValueError(f"Too many images ({num_images}) for a single figure. Max is {self.MAX_IMG_PER_FIGURE}.")
        self.num_images = num_images
        self.num_buttons = num_buttons # will vary according to the view mode, not just the number of labels
        # should be set from the view classes later - defining it here for now at least keeps things neater
        #? NOTE: keepiing both `using_figure_elements` and `panels_in_use` to separate logic for axes and panels further
        self.using_figure_elements: Dict[str, bool] = {
            # NOTE: unfinished but I'm going to initialize it here for now to clean things up - eventually this wouldn't be set in the constructor
            "legend": use_legend,
            "checkboxes": use_checkboxes,
            "summary": use_summary,
        } # track which figure elements are being used (legend, checkboxes, summary box, etc.)
        # TODO: eventually expand this logic to check all axes to be used - defined somewhere else with other "supported" elements
        self.panels_in_use: Dict[str, bool] = {
            "left": use_summary,
            "right": use_checkboxes,
            "bottom": num_buttons > 0,  # always true if there are buttons
            "bottom_left": use_legend,  # not implemented yet
            "bottom_right": False,  # not implemented yet
            "main": True,  # always true for the main image panel
        }
        self.panel_defaults = ConstFigureDefaults()
        self.figure_wrapper = PaneledFigureWrapper(fig_size = self.FIGURE_DIMS)
        self.axes_manager = AxesCreationManager(self.panels_in_use)


    def create_figure_layout(self):
        """ define default panels and build them as subfigures """
        # following setter methods must be called before creating the figure and subfigures
        # any panels not present in the final figure should be set to "None" in self.figure_wrapper.panels
        self._set_bottom_panel()
        #self._set_optional_panel("left", self._create_summary_axes)  # for summary box
        self._set_optional_panel("left", self.axes_manager.create_summary_axes_data)  # for summary box
        #self._set_optional_panel("right", self._create_checkboxes)  # for checkboxes
        self._set_optional_panel("right", self.axes_manager.create_checkbox_axes_data)  # for checkboxes
        #self._set_optional_panel("bottom_left")  # for future use
        self._set_optional_panel("bottom_left", self.axes_manager.create_legend_axes_data)  # for legend
        self._set_optional_panel("bottom_right")  # for future use - radial buttons that affect image contents
        self._set_main_panel()
        # phase 1: create the figure and subfigures from general panel bounding boxes
        self.figure_wrapper.create_paneled_figure()
        # phase 2: place AxesData inside each panel's subfigure and create the actual Axes objects in subfigures
        self._create_and_register_image_axes()
        # create actual plt.Axes objects from the AxesData objects in each of the manager's panels
        self._place_figure_elements()

    ############* functions for setting the panel properties and creating the subfigures ############

    def _set_bottom_panel(self):
        """ set bottom panel for buttons using dynamic sizing """
        # this one will always be plotted so no need to check self.using_figure_elements, but we may have need to
            # adjust the size based on other elements such as when I finally add two (or more) rows of buttons
        if self.num_buttons == 0:
            raise RuntimeError("Something went wrong; no buttons were created.")
        bottom_panel_defaults = self.panel_defaults.get_panel_defaults("bottom")
        print("bottom panel defaults:", bottom_panel_defaults)
        bottom_panel = PanelData(name="bottom", **bottom_panel_defaults)
        self.figure_wrapper.add_panel("bottom", bottom_panel)
        buttons = self._create_and_register_button_axes()
        for btn in buttons:
            self.figure_wrapper.add_axes_data_to_panel("bottom", btn)

    def _set_main_panel(self):
        """ set main panel for images in the center """
        #~ ... code for dynamically determining the panel's size and position goes here (based on elements in self.using_figure_elements)
        main_panel_kwargs = self.panel_defaults.get_panel_defaults("main")
        main_panel = PanelData(name="main", **main_panel_kwargs)
        self.figure_wrapper.add_panel("main", main_panel)
        #self._create_and_register_image_axes()
        #? NOTE: can't initialize axes by calling self.figure_wrapper.create_image_axes() here since it needs to be called after the subfigures are created


    def _set_optional_panel(self, name: str, add_axes_func: Callable = None) -> None: #, defaults: Dict[str, Any]) -> None:
        """ set optional panels (from "left", "right", "bottom_left", or "bottom_right"] """
        if name not in SUPPORTED_PANEL_NAMES:
            raise ValueError(f"Panel '{name}' is not a currently supported panel option.")
        if not self.panels_in_use[name]:
            self.figure_wrapper.add_panel(name, None)  # set to None if not in use
        else:
            # set the panel's position and size based on the defaults and the current figure size
            panel_defaults = self.panel_defaults.get_panel_defaults(name)
            panel_data = PanelData(name=name, **panel_defaults)
            self.figure_wrapper.add_panel(name, panel_data)
            if add_axes_func:
                # create the axes for the panel if a function is provided
                axes_data = add_axes_func()
                print(f"{name} panel axes width: {axes_data.width}")
                self.figure_wrapper.add_axes_data_to_panel(name, axes_data)  # append an AxesData object to the panel


    ############* functions for creating the axes objects within the subfigures ############

    # TODO: revisit the inputs and outputs of the following function later
    def _place_figure_elements(self):
        """ Phase 2: create Axes in each subfigure from stored AxesData. and handle 'button_axes' in a list """
        for pname, panel in self.figure_wrapper.panels.items():
            if panel is None or panel.subfigure is None:
                continue
            # place each AxesData object
            if pname == "main":
                # TODO: might change this so that this function accepts arguments to call panel_wraper.create_image_axes
                continue  # skip the main panel for now, since it has its own method for instantiation called before this
            self.axes_manager.set_multiple_axes_objects(panel, panel.axes_items)

    def _create_and_register_image_axes(self):
        num_img_rows, num_img_cols = self._compute_image_grid_shape()
        if self.num_images > num_img_rows * num_img_cols:
            raise ValueError(f"Too many images ({self.num_images}) for the given grid size ({num_img_rows}x{num_img_cols})")
        main_panel = self.figure_wrapper.get_panel("main")
        if main_panel is None:
            raise ValueError("Main panel (mandatory) is not yet initialized.")
        axes_data: List[ImageAxesData] = self.axes_manager.create_image_axes_data(main_panel, self.num_images, num_img_rows, num_img_cols)
        #& still not sure whether I just want to add img_axes_data contents to the panel directly in the function call above - mainly a matter of transparency
        self.figure_wrapper.add_axes_data_to_panel("main", axes_data)


    def _create_and_register_button_axes(self) -> List[ButtonAxesData]:
        """ Creates a bottom-aligned button panel. """
        bottom_panel = self.figure_wrapper.get_panel("bottom")
        if bottom_panel is None:
            raise ValueError("Bottom panel (mandatory) is not yet initialized.")
        button_axes_data = self.axes_manager.create_button_axes_data(
            #bottom_panel,
            self.num_buttons,
            bottom_panel.left + self.panel_defaults.AXES_PADDING,
            bottom_panel.left + bottom_panel.width - self.panel_defaults.AXES_PADDING
        )
        self.figure_wrapper.add_axes_data_to_panel("bottom", button_axes_data)
        return button_axes_data

    def _compute_image_grid_shape(self) -> Tuple[int, int]:
        """ dynamically calculates the number of rows and columns needed based on image counts """
        return (
            self.num_images // self.MAX_IMG_COLS + (1 if self.num_images % self.MAX_IMG_COLS else 0),
            min(self.num_images, self.MAX_IMG_COLS),
        )

    ############* getter methods for accessing the created Axes and subfigures ############

    # TODO: reduce the use of these wherever possible in the view classes and move more of its methods here instead

    def get_subfigure(self, panel_name: str) -> plt.Figure:
        """ Returns the subfigure for the given panel name. """
        panel = self.figure_wrapper.get_initialized_panel(panel_name)
        return panel.subfigure # should still not be possible to return None here since it's tested for

    def get_axes(self, panel_name: str, axes_label: str) -> plt.Axes:
        all_axes: List[AxesData] = self.figure_wrapper.get_panel_axes(panel_name)
        if all_axes is None:
            raise ValueError(f"Panel '{panel_name}' is not in use.")
        for ax_obj in all_axes:
            if ax_obj.label == axes_label:
                return ax_obj.axes
        raise ValueError(f"Axes '{axes_label}' not found in panel '{panel_name}'.")

    def get_image_axes(self):
        return self.figure_wrapper.images

    def get_image_subaxes(self, idx) -> ImageAxesData:
        try:
            return self.figure_wrapper.images[idx]
        except IndexError:
            raise IndexError(f"Image index {idx} out of range in the layout's list of image axes.")

    def get_button_axes(self):
        return self.figure_wrapper.buttons

    def get_panel_position(self, panel_name: str) -> Tuple[float, float, float, float]:
        """ Returns the position of the given panel in the main figure. """
        panel = self.figure_wrapper.get_panel(panel_name)
        if panel is None:
            return None
        return panel.get_position()


    @property
    def fig(self):
        """ expose the manager's figure so that external code can do plt.show() references it """
        return self.figure_wrapper.fig


