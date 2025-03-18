import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable, Any
# local imports
from .utils import disable_all_axis_elements, measure_checkbox_labels, compute_button_positions
from .axes_data import AxesData, ButtonAxesData, CheckboxAxesData, SummaryAxesData, LegendAxesData, ImageAxesData, PanelData
from .figure_wrapper import PaneledFigureWrapper
from .figure_defaults import ConstFigureDefaults


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
            "bottom_left": False,  # not implemented yet
            "bottom_right": False,  # not implemented yet
            "main": True,  # always true for the main image panel
        }
        self.panel_defaults = ConstFigureDefaults()
        self.manager = PaneledFigureWrapper(fig_size = self.FIGURE_DIMS)
        ###^ may not keep this
        # self.checkbox_dims = None
        # if labels and use_checkboxes:
        #     self.checkbox_dims = measure_checkbox_labels(labels)
        #     #self.checkbox_dims = approximate_checkbox_size(labels)
        ###^


    def create_figure_layout(self):
        """ define default panels and build them as subfigures """
        # following setter methods must be called before creating the figure and subfigures
        # any panels not present in the final figure should be set to "None" in self.manager.panels
        self._set_bottom_panel()
        self._set_optional_panel("left", self._create_summary_axes)  # for summary box
        self._set_optional_panel("right", self._create_checkboxes)  # for checkboxes
        self._set_optional_panel("bottom_left")  # for future use
        self._set_optional_panel("bottom_right")  # for future use
        self._set_main_panel()
        # phase 1: create the figure and subfigures from general panel bounding boxes
        #self.manager.create_image_axes(self.num_images, num_img_rows, num_img_cols)
        self.manager.create_paneled_figure()
        # phase 2: place AxesData inside each panel's subfigure and create the actual Axes objects in subfigures
        num_img_rows, num_img_cols = self._compute_image_grid_shape()
        #? NOTE: still creates an AxesData object for each image, but it's done in the PaneledFigureWrapper
        self.manager.create_image_axes(self.num_images, num_img_rows, num_img_cols)  # create the image axes in the main subfigure
        # create actual plt.Axes objects from the AxesData objects in each of the manager's panels
        self.manager.place_figure_elements()

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
        self.manager.add_panel("bottom", bottom_panel)
        buttons = self._create_button_axes(bottom_panel.left, bottom_panel.left + bottom_panel.width)
        for btn in buttons:
            self.manager.add_axes_data_to_panel("bottom", btn)

    def _set_main_panel(self):
        """ set main panel for images in the center """
        #~ ... code for dynamically determining the panel's size and position goes here (based on elements in self.using_figure_elements)
        main_panel_kwargs = self.panel_defaults.get_panel_defaults("main")
        # print("main panel defaults:", main_panel_kwargs)
        # if not self.using_figure_elements["checkboxes"]:
        #     right_panel_defaults = self.panel_defaults.get_panel_defaults("right")
        #     # main_panel_kwargs["right"] = right_panel_defaults["right"]
        #     main_panel_kwargs["width"] += right_panel_defaults["width"]
        #     # may need to adjust the bottom but for now they should be the same
        # if not self.using_figure_elements["summary"]:
        #     left_panel_defaults = self.panel_defaults.get_panel_defaults("left")
        #     main_panel_kwargs["left"] = left_panel_defaults["left"]
        #     main_panel_kwargs["width"] += left_panel_defaults["width"]
            # shouldn't mess with the bottom panel position since it defaults to the bottom of the figure
        # main_panel = PanelData(name="main", grid_idx=panel_idx, **main_panel_kwargs)
        main_panel = PanelData(name="main", **main_panel_kwargs)
        self.manager.add_panel("main", main_panel)
        #? NOTE: can't initialize axes by calling self.manager.create_image_axes() here since it needs to be called after the subfigures are created


    def _set_optional_panel(self, name: str, add_axes_func: Callable = None) -> None: #, defaults: Dict[str, Any]) -> None:
        """ set optional panels (from "left", "right", "bottom_left", or "bottom_right"] """
        if name not in self.manager.supported_panels:
            raise ValueError(f"Panel '{name}' is not a supported panel option.")
        if not self.panels_in_use[name]:
            self.manager.add_panel(name, None)  # set to None if not in use
        else:
            # set the panel's position and size based on the defaults and the current figure size
            panel_defaults = self.panel_defaults.get_panel_defaults(name)
            panel_data = PanelData(name=name, **panel_defaults)
            self.manager.add_panel(name, panel_data)
            if add_axes_func:
                # create the axes for the panel if a function is provided
                axes_data = add_axes_func()
                self.manager.add_axes_data_to_panel(name, axes_data)  # append an AxesData object to the panel
            #& PREVIOUSLY: used self.manager.add_axes_data_to_panel - now address this in a separate method
            #& in particular, left: self._create_summary_axes() and right: self._create_checkboxes()
            #& later, we should allow a dynamic resizing callback to tweak the panel dims based on needed axes sizes

    ############* functions for creating the axes objects within the subfigures ############
    # TODO: may be greatly refactoring all of these
    def _create_legend_axes(self):
        # might leave this one to be created entirely within the PanelData object since it autofits to "loc" based on label lengths
        pass

    def _create_button_axes(self, left_bound: float, right_bound: float) -> List[ButtonAxesData]:
        """ Creates a bottom-aligned button panel. """
        # compute button positions (right-aligned)
        button_positions = compute_button_positions(self.num_buttons, left_bound, right_bound)
        button_list = []
        for pos in button_positions:
            print("button position: ", pos)
            # create a new button Axes object for each button
            # TODO: need to return button_positions as a dictionary from compute_button_positions and pass **kwargs later
            #! FIXME: having some color and transparency issues - fix later
            button_list.append(ButtonAxesData(*pos, color="lightgrey", alpha=0.5))
        return button_list

    def _create_summary_axes(self, adjust_position = False) -> SummaryAxesData:
        """ Creates a summary box aligned dynamically with checkboxes """
        # use defaults for now and maybe implement the dynamic sizing later
        return SummaryAxesData()
        # set summary height and use defaults on all other axes properties

    def _create_checkboxes(self, adjust_position = False) -> CheckboxAxesData:
        """ Creates checkboxes aligned above the button panel. """
        # use defaults for now and maybe implement the dynamic sizing later
        axes_data = CheckboxAxesData()
        self.autofit_axes_to_panel("right", axes_data)
        return axes_data
        # set checkbox bottom bound and use defaults on all other axes properties

    def _compute_image_grid_shape(self) -> Tuple[int, int]:
        """ dynamically calculates the number of rows and columns needed based on image counts """
        return (
            self.num_images // self.MAX_IMG_COLS + (1 if self.num_images % self.MAX_IMG_COLS else 0),
            min(self.num_images, self.MAX_IMG_COLS),
        )

    # TODO: add a method similar to _set_optional_panel to be called by the individual _create_axes methods to generalize creation and dynamic resizing of the panels
    def _set_axes_data(self, name: str, axes_data: AxesData) -> None:
        raise NotImplementedError("Not implemented yet. This should be called by the individual _create_axes methods to generalize creation and dynamic resizing of the panels.")


    ############* getter methods for accessing the created Axes and subfigures ############

    def get_subfigure(self, panel_name: str) -> plt.Figure:
        """ Returns the subfigure for the given panel name. """
        if not self.manager.panel_exists(panel_name):
            raise ValueError(f"Panel '{panel_name}' does not exist.")
        return self.manager.get_subfigure(panel_name)

    def get_axes(self, panel_name: str, axes_label: str):
        return self.manager.get_axes(panel_name, axes_label)

    def get_image_axes(self):
        return self.manager.images

    def get_image_subaxes(self, idx):
        try:
            return self.manager.images[idx]
        except IndexError:
            raise IndexError(f"Image index {idx} out of range in the layout's list of image axes.")

    def get_button_axes(self):
        return self.manager.buttons

    def get_panel_position(self, panel_name: str) -> Tuple[float, float, float, float]:
        if not self.manager.panel_exists(panel_name):
            return None
        # calls PanelData.get_position()
        return self.manager.panels[panel_name].get_position()

    #!! TEMP: just using for debugging - not sure if it should be kept:
    def autofit_axes_to_panel(self, panel_name: str, ax_data: AxesData):
        """ Rescale the axes to fit within the panel's bounding box """
        padding = self.panel_defaults.AXES_PADDING
        left, bottom, width, height = self.get_panel_position(panel_name)
        print(f"{panel_name} panel position: left={left}, bottom={bottom}, width={width}, height={height}")
        ax_data.update_position(left + padding, bottom + padding, width - 2*padding, height - 2*padding)
        #ax_data.update_position(left, bottom, width, height)


    @property
    def fig(self):
        """ expose the manager's figure so that external code can do plt.show() references it """
        return self.manager.main_figure


