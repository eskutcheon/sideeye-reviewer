import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
# local imports
from .utils import disable_all_axis_elements, measure_checkbox_labels, compute_button_positions
from .axes_data import ButtonAxesData, CheckboxAxesData, SummaryAxesData, LegendAxesData
from .figure_wrapper import PanelData, PaneledFigureWrapper
from .figure_defaults import ConstFigureDefaults


class FigureLayoutManager:
    """ Manages:
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
        if num_images > self.MAX_IMG_PER_FIGURE:
            raise ValueError(f"Too many images ({num_images}) for a single figure. Max is {self.MAX_IMG_PER_FIGURE}.")
        self.num_images = num_images
        self.num_buttons = num_buttons # will vary according to the view mode, not just the number of labels
        
        # should be set from the view classes later - defining it here for now at least keeps things neater
        self.using_figure_elements: Dict[str, bool] = {
            # NOTE: unfinished but I'm going to initialize it here for now to clean things up - eventually this wouldn't be set in the constructor
            "legend": use_legend,
            "checkboxes": use_checkboxes,
            "summary": use_summary,
        } # track which figure elements are being used (legend, checkboxes, summary box, etc.)
        self.panel_defaults = ConstFigureDefaults()
        self.manager = PaneledFigureWrapper(fig_size = self.FIGURE_DIMS)
        
        ###^ may not keep this
        self.checkbox_dims = None
        if labels and use_checkboxes:
            self.checkbox_dims = measure_checkbox_labels(labels)
            #self.checkbox_dims = approximate_checkbox_size(labels)
        # store the actual Axes objects in a dictionary for later access
        #self.axes: Dict[str, plt.Axes] = {}
        ###^


    def create_figure_layout(self):
        """ define default panels and build them as subfigures """
        self._set_bottom_panel()
        self._set_left_panel()
        self._set_right_panel()
        self._set_main_panel()
        # phase 1: create the figure and subfigures from general panel bounding boxes
        num_img_rows = self._compute_image_rows()
        num_img_cols = self._compute_image_cols()
        #? NOTE: still creates an AxesData object for each image, but it's done in the PaneledFigureWrapper
        #self.manager.create_image_axes(self.num_images, num_img_rows, num_img_cols)
        self.manager.create_paneled_figure(self.num_images, num_img_rows, num_img_cols)
        # phase 2: place AxesData inside each panel's subfigure and create the actual Axes objects in subfigures
        #self._create_image_axes()
        self.manager.place_figure_elements()


    def _set_bottom_panel(self):
        """ set bottom panel for buttons using dynamic sizing """
        # this one will always be plotted so no need to check self.using_figure_elements, but we may have need to
            # adjust the size based on other elements such as when I finally add two (or more) rows of buttons
        if self.num_buttons == 0:
            raise RuntimeError("Something went wrong; no buttons were created.")
        #TODO: eventually want to tune these dimensions based on the number of buttons and possibly the space needed by the left panel
        panel_idx = tuple([1, 1])
        bottom_panel_defaults = self.panel_defaults.get_panel_defaults("bottom")
        print("bottom panel defaults:", bottom_panel_defaults)
        bottom_panel = PanelData(name="bottom", grid_idx=panel_idx, **bottom_panel_defaults)
        self.manager.add_panel("bottom", bottom_panel)
        buttons = self._create_button_axes(bottom_panel.left, bottom_panel.left + bottom_panel.width)
        for btn in buttons:
            self.manager.add_axes_data_to_panel("bottom", btn)


    def _set_left_panel(self):
        """ set left panel for summary or static info, and optionally the legend """
        #? NOTE:: when not self.using_figure_elements["summary"], we still need to set the legend one way or another but no need
        #? NOTE: to make the left panel just for it, so maybe check for the left panel when making the main panel since that needs to be done anyway
        if self.using_figure_elements["summary"]:
            # TODO: eventually code should go here for dynamically determining the panel's size and position based on summary box contents' length
            left_panel_defaults = self.panel_defaults.get_panel_defaults("left")
            print("left panel defaults:", left_panel_defaults)
            left_panel = PanelData(name="left", grid_idx=(0, 0), **left_panel_defaults)
            self.manager.add_panel("left", left_panel)
            self.manager.add_axes_data_to_panel("left", self._create_summary_axes())


    def _set_right_panel(self):
        """ right panel for non-button interactive elements (e.g. checkboxes) """
        #~ ... code for dynamically determining the panel's size and position goes here (based on elements in self.using_figure_elements)
        if self.using_figure_elements["checkboxes"]:
            panel_idx = tuple([0, 1 + int(self.manager.panel_exists("left"))])
            right_panel_defaults = self.panel_defaults.get_panel_defaults("right")
            print("right panel defaults:", right_panel_defaults)
            right_panel = PanelData(name="right", grid_idx=panel_idx, **right_panel_defaults)
            self.manager.add_panel("right", right_panel)
            self.manager.add_axes_data_to_panel("right", self._create_checkboxes())

    def _set_main_panel(self):
        """ set main panel for images in the center """
        #~ ... code for dynamically determining the panel's size and position goes here (based on elements in self.using_figure_elements)
        main_panel_kwargs = self.panel_defaults.get_panel_defaults("main")
        print("main panel defaults:", main_panel_kwargs)
        panel_idx = tuple([0, int(self.manager.panel_exists("left"))])
        if not self.using_figure_elements["checkboxes"]:
            right_panel_defaults = self.panel_defaults.get_panel_defaults("right")
            # main_panel_kwargs["right"] = right_panel_defaults["right"]
            main_panel_kwargs["width"] += right_panel_defaults["width"]
            # may need to adjust the bottom but for now they should be the same
        if not self.using_figure_elements["summary"]:
            left_panel_defaults = self.panel_defaults.get_panel_defaults("left")
            main_panel_kwargs["left"] = left_panel_defaults["left"]
            main_panel_kwargs["width"] += left_panel_defaults["width"]
            # shouldn't mess with the bottom panel position since it defaults to the bottom of the figure
        main_panel = PanelData(name="main", grid_idx=panel_idx, **main_panel_kwargs)
        self.manager.add_panel("main", main_panel)

    ###### functions for creating the axes objects ######
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
            button_list.append(ButtonAxesData(*pos))
        return button_list

    def _create_summary_axes(self) -> SummaryAxesData:
        """ Creates a summary box aligned dynamically with checkboxes """
        # use defaults for now and maybe implement the dynamic sizing later
        return SummaryAxesData()
        # set summary height and use defaults on all other axes properties

    def _create_checkboxes(self) -> CheckboxAxesData:
        """ Creates checkboxes aligned above the button panel. """
        # use defaults for now and maybe implement the dynamic sizing later
        return CheckboxAxesData()
        # set checkbox bottom bound and use defaults on all other axes properties

    def _compute_image_cols(self) -> int:
        """ dynamically calculates the number of columns needed based on image counts """
        return min(self.num_images, self.MAX_IMG_COLS)

    def _compute_image_rows(self) -> int:
        """ calculates the number of rows needed for the given image count """
        return (self.num_images // self.MAX_IMG_COLS) + (1 if self.num_images % self.MAX_IMG_COLS else 0)

    # def _create_image_axes(self):
    #     """ Create one or more image axes in the subfigure of the main panel """
    #     num_img_rows = self._compute_image_rows()
    #     num_img_cols = self._compute_image_cols()
    #     #? NOTE: still creates an AxesData object for each image, but it's done in the PaneledFigureWrapper
    #     self.manager.create_image_axes(self.num_images, num_img_rows, num_img_cols)

    def get_subfigure(self, panel_name: str) -> plt.Figure:
        """ Returns the subfigure for the given panel name. """
        if not self.manager.panel_exists(panel_name):
            raise ValueError(f"Panel '{panel_name}' does not exist.")
        subfig_idx = self.manager.panels[panel_name].fig_idx
        return self.fig.subfigs[subfig_idx]

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


    @property
    def fig(self):
        """ expose the manager's figure so that external code can do plt.show() references it """
        return self.manager.fig


