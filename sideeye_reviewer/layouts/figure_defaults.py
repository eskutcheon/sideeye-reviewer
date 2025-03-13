"""
    seemingly convoluted way to abstract the default positions of the axes and subfigures, but it has a couple benefits:
        1. the default positions are easily accessible and modifiable
        2. default positions are largely not based on just a few hard-coded constants that were the least likely to change
        3. the dataclasses are frozen, which avoids the possibility of code injection into a complex API like matplotlib
            by encouraging the use of the provided methods to access only subsets of the default values
        4. fairly efficient (and safe) compared to a more complex system of inheritance and method overriding
"""

from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable
from dataclasses import dataclass, field, fields


""" UNFINISHED COPILOT PROMPT
The `PanelData` objects are meant to be constructed one by one from the layout manager based on whether it's using
default arguments and whether other panels are included or not. What would be the best way to make a default panel generator
function that makes a single defaults dataclass of type `ConstFigureDefaults` to avoid unneeded recreation for each new panel
and used a single instantiation instead? It could keep track of the panels already added and use new "getter" methods from the
`ConstFigureDefaults` dataclass to easily group related default values. How should this be implemented 

"""

#? NOTE: DEFAULTS ASSUME ALL FIGURE ELEMENTS ARE IN USE - if not, bounds are adjusted to fit the remaining elements

@dataclass(frozen=True)
class ConstFigureDefaults:
    FIGURE_DEFAULT_SIZE: Tuple[int, int] = (12, 7)
    MAX_IMG_PER_FIGURE: int = 4
    MAX_IMG_COLS: int = 3
    AXES_PADDING: float = 0.02
    # button related constants
    BUTTON_SPACING: float = 0.01
    BUTTON_WIDTH: float = 0.1
    BUTTON_HEIGHT: float = 0.075
    BUTTON_COLOR: str = "#eeeeee"
    # # NEW: bottom left panel
    BOTTOM_LEFT_PANEL_LEFT: float = 0.0
    BOTTOM_LEFT_PANEL_BOTTOM: float = 0.0
    BOTTOM_LEFT_PANEL_WIDTH: float = 0.15 #field(init=False)
    BOTTOM_LEFT_PANEL_HEIGHT: float = field(init=False) # set to button panel height
    BOTTOM_LEFT_PANEL_FACECOLOR: str = "lightgray"
    BOTTOM_LEFT_PANEL_ALPHA: float = 0.25 # transparency of the axes background
    # NEW: bottom right panel - intended to be fixed and ever-present, but might treat it the same as the main panel (full width) later
    BOTTOM_RIGHT_PANEL_LEFT: float = field(init=False) # depends on right panel width or button panel right bound
    BOTTOM_RIGHT_PANEL_BOTTOM: float = 0.0
    BOTTOM_RIGHT_PANEL_WIDTH: float = field(init=False)  # set to bottom left panel width
    BOTTOM_RIGHT_PANEL_HEIGHT: float = field(init=False) # set to button panel height
    BOTTOM_RIGHT_PANEL_FACECOLOR: str = "lime"
    BOTTOM_RIGHT_PANEL_ALPHA: float = 0.25 # transparency of the axes background
    # button panel related constants
        # intended to be fixed and ever-present, but might treat it the same as the main panel (full width from adjacent unused panels) later
    BOTTOM_PANEL_LEFT: float = 0.15 #field(init=False) # depends on on bottom left panel right bound
    BOTTOM_PANEL_BOTTOM: float = 0.0
    BOTTOM_PANEL_WIDTH: float = field(init=False) # depends on bottom left and bottom right widths
    BOTTOM_PANEL_HEIGHT: float = field(init=False) # depends on bottom left and right panel heights
    BOTTOM_PANEL_FACECOLOR: str = "skyblue"
    BOTTOM_PANEL_ALPHA: float = 0.25 # transparency of the axes background
    # right panel related constants
    RIGHT_PANEL_LEFT: float = field(init=False)
    RIGHT_PANEL_BOTTOM: float = field(init=False)
    RIGHT_PANEL_WIDTH: float = 0.15 #field(init=False)
    #? NOTE: might make this based on the main panel, but I'd have to figure out the space reserved for titles
    RIGHT_PANEL_HEIGHT: float = field(init=False)
    RIGHT_PANEL_FACECOLOR: str = "red"
    RIGHT_PANEL_ALPHA: float = 0.25 # transparency of the axes background
    # left panel related constants
    LEFT_PANEL_LEFT: float = 0.0
    LEFT_PANEL_BOTTOM: float = 0.0 #field(init=False)
    LEFT_PANEL_WIDTH: float = 0.15
    LEFT_PANEL_HEIGHT: float = 1.0
    LEFT_PANEL_FACECOLOR: str = "lightgray"
    LEFT_PANEL_ALPHA: float = 0.25
    # main panel (image plotting region) related constants
    MAIN_PANEL_LEFT: float = field(init=False)
    MAIN_PANEL_BOTTOM: float = field(init=False)
    MAIN_PANEL_WIDTH: float = field(init=False)
    MAIN_PANEL_HEIGHT: float = field(init=False)
    MAIN_PANEL_FACECOLOR: str = "none"
    #MAIN_PANEL_ALPHA: float = 0.0

    def __post_init__(self):
        """ using the post init to set constants derived from others """
        # bottom left panel resides in the bottom corner, meant for the legend - primarily added with the bottom right to handle subfigure widths and heights
        #object.__setattr__(self, 'BOTTOM_LEFT_PANEL_HEIGHT', self.BOTTOM_PANEL_HEIGHT) # set to button panel height
        # right-aligned button panel
        object.__setattr__(self, 'BOTTOM_PANEL_WIDTH', 1.0 - self.BOTTOM_PANEL_LEFT - self.RIGHT_PANEL_WIDTH) # - self.AXES_PADDING)
        # padding on top and bottom of the button axes
        object.__setattr__(self, 'BOTTOM_PANEL_HEIGHT', self.BUTTON_HEIGHT + 4.0*self.AXES_PADDING)
        # aligned against extreme edge with no padding
        # essentially defaulting to the same panel width on the right and left.
        #object.__setattr__(self, 'RIGHT_PANEL_WIDTH', self.LEFT_PANEL_WIDTH)
        object.__setattr__(self, 'RIGHT_PANEL_LEFT', 1.0 - self.RIGHT_PANEL_WIDTH) # - self.AXES_PADDING)
        # right panel bottom == button panel top
        object.__setattr__(self, 'RIGHT_PANEL_BOTTOM', self.BOTTOM_PANEL_BOTTOM + self.BOTTOM_PANEL_HEIGHT)#self.BUTTON_HEIGHT + 2.0*self.AXES_PADDING)
        object.__setattr__(self, 'RIGHT_PANEL_HEIGHT', 1.0 - self.RIGHT_PANEL_BOTTOM)
        # main panel is the remaining space after determining bounds
        object.__setattr__(self, 'MAIN_PANEL_LEFT', self.LEFT_PANEL_LEFT + self.LEFT_PANEL_WIDTH)
        object.__setattr__(self, 'MAIN_PANEL_BOTTOM', self.BOTTOM_PANEL_BOTTOM + self.BOTTOM_PANEL_HEIGHT)
        object.__setattr__(self, 'MAIN_PANEL_WIDTH', self.RIGHT_PANEL_LEFT - self.MAIN_PANEL_LEFT)
        object.__setattr__(self, 'MAIN_PANEL_HEIGHT', 1.0 - self.MAIN_PANEL_BOTTOM)

    #? NOTE: these work exactly the same as if they were static methods but this way is supposedly safer when using init=False
    @classmethod
    def get_figure_defaults(cls):
        return {
            'figsize': cls.FIGURE_DEFAULT_SIZE,
            'max_img_per_figure': cls.MAX_IMG_PER_FIGURE,
            'max_img_cols': cls.MAX_IMG_COLS,
            'axes_padding': cls.AXES_PADDING,
            # 'dpi': 100,
            # 'frameon': False
        }

    @classmethod
    def get_button_defaults(cls):
        return {
            'spacing': cls.BUTTON_SPACING,
            'width': cls.BUTTON_WIDTH,
            'height': cls.BUTTON_HEIGHT,
            'color': cls.BUTTON_COLOR
        }

    def get_panel_defaults(self, panel_name: str) -> Dict[str, float]:
        # should only be run after instantiation of the class so that __post_init__ assigns all fields
        panel_name_upper = panel_name.upper()
        defaults = {}
        for field_name in [var_field.name for var_field in fields(self)]:
            full_panel_name = f"{panel_name_upper}_PANEL"
            #? NOTE: if I let the field names vary from ending in "left, right, etc" this will need to be updated
            if field_name.startswith(full_panel_name):
                key = field_name[(len(full_panel_name) + 1):].lower()
                defaults[key] = getattr(self, field_name)
        return defaults



@dataclass(frozen=True)
class ConstAxesDefaults:
    # default axes properties
    AXES_COLOR: str = "white"
    AXES_ALPHA: float = 1.0
    AXES_TITLE_SIZE: str = "large"
    # default checkbox axes properties
    # CHECKBOX_LABEL: str = "checkboxes"
    CHECKBOX_LEFT: float = field(init=False)
    CHECKBOX_BOTTOM: float = field(init=False)
    CHECKBOX_WIDTH: float = field(init=False)
    CHECKBOX_HEIGHT: float = field(init=False)
    CHECKBOX_COLOR: str = "lightgray"
    # default summary box axes properties
    # SUMMARY_LABEL: str = "summary"
    SUMMARY_LEFT: float = field(init=False)
    SUMMARY_BOTTOM: float = field(init=False)
    SUMMARY_WIDTH: float = field(init=False)
    SUMMARY_HEIGHT: float = field(init=False)
    SUMMARY_COLOR: str = "lightgray"
    # default legend axes properties
    # LEGEND_LABEL: str = "legend"
    LEGEND_LEFT: float = field(init=False)
    LEGEND_BOTTOM: float = field(init=False)
    LEGEND_WIDTH: float = field(init=False)
    LEGEND_HEIGHT: float = field(init=False)
    LEGEND_COLOR: str = "gray"



    def __post_init__(self):
        """ using the post init to set constants derived from ConstFigureDefaults """
        position_defaults = ConstFigureDefaults()
        object.__setattr__(self, 'CHECKBOX_LEFT', position_defaults.RIGHT_PANEL_LEFT + position_defaults.AXES_PADDING)
        object.__setattr__(self, 'CHECKBOX_BOTTOM', position_defaults.RIGHT_PANEL_BOTTOM + position_defaults.AXES_PADDING)
        object.__setattr__(self, 'CHECKBOX_WIDTH', position_defaults.RIGHT_PANEL_WIDTH - 2 * position_defaults.AXES_PADDING)
        object.__setattr__(self, 'CHECKBOX_HEIGHT', position_defaults.RIGHT_PANEL_HEIGHT - 2 * position_defaults.AXES_PADDING)
        object.__setattr__(self, 'SUMMARY_LEFT', position_defaults.LEFT_PANEL_LEFT + position_defaults.AXES_PADDING)
        object.__setattr__(self, 'SUMMARY_BOTTOM', position_defaults.LEFT_PANEL_BOTTOM + position_defaults.AXES_PADDING)
        object.__setattr__(self, 'SUMMARY_WIDTH', position_defaults.LEFT_PANEL_WIDTH - 2 * position_defaults.AXES_PADDING)
        object.__setattr__(self, 'SUMMARY_HEIGHT', position_defaults.LEFT_PANEL_HEIGHT - 2 * position_defaults.AXES_PADDING)
        object.__setattr__(self, 'LEGEND_LEFT', position_defaults.AXES_PADDING)
        object.__setattr__(self, 'LEGEND_BOTTOM', position_defaults.AXES_PADDING)
        object.__setattr__(self, 'LEGEND_WIDTH', position_defaults.LEFT_PANEL_WIDTH - 2 * position_defaults.AXES_PADDING)
        object.__setattr__(self, 'LEGEND_HEIGHT', position_defaults.BOTTOM_PANEL_HEIGHT - position_defaults.AXES_PADDING)

    @staticmethod
    def get_checkbox_defaults():
        defaults = ConstAxesDefaults()
        return {
            # 'label': defaults.CHECKBOX_LABEL,
            'left': defaults.CHECKBOX_LEFT,
            'bottom': defaults.CHECKBOX_BOTTOM,
            'width': defaults.CHECKBOX_WIDTH,
            'height': defaults.CHECKBOX_HEIGHT,
            'color': defaults.CHECKBOX_COLOR
        }

    @staticmethod
    def get_summary_defaults():
        defaults = ConstAxesDefaults()
        return {
            # 'label': defaults.SUMMARY_LABEL,
            'left': defaults.SUMMARY_LEFT,
            'bottom': defaults.SUMMARY_BOTTOM,
            'width': defaults.SUMMARY_WIDTH,
            'height': defaults.SUMMARY_HEIGHT,
            'color': defaults.SUMMARY_COLOR
        }

    @staticmethod
    def get_legend_defaults():
        defaults = ConstAxesDefaults()
        return {
            # 'label': defaults.LEGEND_LABEL,
            'left': defaults.LEGEND_LEFT,
            'bottom': defaults.LEGEND_BOTTOM,
            'width': defaults.LEGEND_WIDTH,
            'height': defaults.LEGEND_HEIGHT,
            'color': defaults.LEGEND_COLOR,
            'alpha': 0.0
        }

    @staticmethod
    def get_button_defaults():
        defaults = ConstFigureDefaults.get_button_defaults()
        #? NOTE: button defaults don't have a left or bottom since these need to be explicitly set, their absence raises an error
        return {
            'width': defaults["width"],
            'height': defaults["height"],
            'color': defaults["color"]
        }