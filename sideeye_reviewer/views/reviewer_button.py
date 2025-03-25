import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from matplotlib.patches import FancyBboxPatch
from typing import Callable, List, Optional


class ReviewerButton:
    """ wrapper class for matplotlib.widgets.Button to track relevant info: label, position, callback, the button widget"""
    def __init__(self, label: str, ax_pos: List[float], callback: Callable, hovercolor: Optional[str] = "0.975"):
        """
            :param label: text shown on the button
            :param ax_pos: [left, bottom, width, height] for the button
            :param callback: a function(event) -> None
            :param hovercolor: button color on hover
        """
        self.label = label
        self.ax_pos = ax_pos
        self.callback = callback
        self.hovercolor = hovercolor
        self.label_size = 24  # default font size for the button label
        self.button_widget = None  # will hold the Button object once created
        self.use_bevel = True  # change later if needed

    def create_button(self, ax: plt.Axes):
        """ Actually create the Axes and the Button, then attach the callback """
        self.button_widget = Button(ax, self.label, hovercolor=self.hovercolor)
        self.button_widget.label.set_fontsize(self.label_size)
        self.button_widget.on_clicked(self.callback)
        # REMINDER: I set the button axes to have alpha = 0 - without styling, it would blend into the panel background
        if self.button_widget is not None and self.use_bevel:
            self.stylize_button(ax)

    def stylize_button(self, ax: plt.Axes):
        """ Apply additional styling to the button if needed """
        # clear existing patches to remove the default rectangle and replace with rounded patch
        ax_facecolor = ax.get_facecolor()
        ax.patch.set_visible(False)
        #subfig_facecolor = ax.figure.get_facecolor()
        #ax.patch.set_facecolor(subfig_facecolor) #'none')  # make the background transparent
        #ax.patch.set_alpha(0)
        rounded_patch = FancyBboxPatch(
            #(0.05, 0.05), 0.90, 0.90,
            (0.0, 0.0), 1, 1,
            #boxstyle = "round,pad=0.05,rounding_size=0.1",
            boxstyle = "round,pad=0.0,rounding_size=0.1",
            transform = ax.transAxes,
            facecolor = ax_facecolor, # keep current color
            edgecolor = 'black',
            linewidth = 1.5,
            zorder = 1
        )
        ax.add_patch(rounded_patch)
        # Optionally simulate a "bevel" with a shadow/highlight effect
        highlight = FancyBboxPatch(
            (0.05, 0.1), 1, 1,
            boxstyle = "round,pad=0.0,rounding_size=0.1",
            transform = ax.transAxes,
            facecolor = 'white',
            edgecolor = 'none',
            alpha = 0.5,
            zorder = 2
        )
        ax.add_patch(highlight)
        self.button_widget.label.set_fontsize(self.button_widget.label.get_fontsize() * 0.95)  # decrease font size to avoid clipping
        self.button_widget.label.set_fontweight('bold')

    @staticmethod
    def factory(fig: plt.Figure, label: str, ax_pos: List[float], callback: Callable, hovercolor: str = "0.975") -> "ReviewerButton":
        """ Alternate: create and return a ReviewerButton in one shot """
        rb = ReviewerButton(label, ax_pos, callback, hovercolor)
        rb.create_button(fig)
        return rb


