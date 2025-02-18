import os
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from matplotlib.animation import FuncAnimation
from PIL import Image
from typing import List
# local imports
from sideeye_reviewer.utils.utils import maximize_window


class SortResultsViewer:
    """ A read-only viewer for a set of images (and optionally their masks), stepping forward/back or auto-playing. Derived from the old show_sort_results.py """
    def __init__(self, file_list: List[str], img_dirs: List[str], figure_header: str):
        """
            :param file_list: the filenames to iterate over
            :param img_dirs: 1 or 2 directories to look in
            :param figure_header: text to display as a heading
        """
        self.file_list = file_list
        self.img_dirs = img_dirs
        self.num_dir = len(img_dirs)
        if not (1 <= self.num_dir <= 2):
            raise ValueError("Only support 1 or 2 image directories.")
        self.curr_idx = 0
        self.num_reviewed = len(file_list)
        self.figure_header = figure_header
        self.playing_animation = False
        self.initialize_figure()
        self.create_buttons()
        self.set_animator()
        plt.show()

    def initialize_figure(self):
        # Prepare the figure
        self.fig, self.axes = plt.subplots(1, self.num_dir, figsize=(10, 5))
        if self.num_dir == 1:
            self.axes = [self.axes]
        # Show the first image(s)
        self.img_display = []
        for i in range(self.num_dir):
            im = Image.open(os.path.join(self.img_dirs[i], self.file_list[self.curr_idx]))
            disp = self.axes[i].imshow(im)
            self.axes[i].axis("off")
            self.img_display.append(disp)
        self.fig.suptitle(
            f"{self.figure_header}\n{self.file_list[self.curr_idx]}\nProgress: {self.curr_idx + 1}/{self.num_reviewed}",
            fontsize="xx-large",
            wrap=True
        )
        maximize_window()
        # Positions: [left, bottom, width, height]
        self.fig.tight_layout(rect=[0, 0.1, 1, 1])
        self.fig.canvas.mpl_connect("close_event", self._on_close)

    def create_buttons(self):
        self.buttons = {
            "prev": Button(plt.axes([0.52, 0.025, 0.1, 0.075]), "PREVIOUS"),
            "next": Button(plt.axes([0.63, 0.025, 0.1, 0.075]), "NEXT"),
            "start": Button(plt.axes([0.74, 0.025, 0.1, 0.075]), "START"),
            "stop": Button(plt.axes([0.85, 0.025, 0.1, 0.075]), "STOP"),
        }
        # TODO: might want to add an 'exit' button to exit more cleanly
        self.buttons["start"].on_clicked(self.start_animation)
        self.buttons["stop"].on_clicked(self.stop_animation)
        # We also handle next/prev in a single callback
        self.fig.canvas.mpl_connect("button_press_event", self.on_button_click)

    def set_animator(self):
        secs_per_frame = 2.5
        self.ani = FuncAnimation(self.fig, self.update_frame, interval=secs_per_frame * 1000, repeat=True, cache_frame_data=False)
        # We'll manually start/stop it by toggling self.playing_animation

    def on_button_click(self, event):
        if event.inaxes == self.buttons["next"].ax:
            self.curr_idx = (self.curr_idx + 1) % self.num_reviewed
            self.update_display(self.curr_idx)
        elif event.inaxes == self.buttons["prev"].ax:
            self.curr_idx = (self.curr_idx - 1) % self.num_reviewed
            self.update_display(self.curr_idx)

    def update_frame(self, frame):
        if self.playing_animation:
            self.curr_idx = (self.curr_idx + 1) % self.num_reviewed
            self.update_display(self.curr_idx)

    def update_display(self, index):
        for i in range(self.num_dir):
            pth = os.path.join(self.img_dirs[i], self.file_list[index])
            im = Image.open(pth)
            self.img_display[i].set_data(im)
        self.fig.suptitle(
            f"{self.figure_header}\n{self.file_list[self.curr_idx]}\nProgress: {self.curr_idx + 1}/{self.num_reviewed}",
            fontsize="xx-large",
            wrap=True
        )
        self.fig.canvas.draw()

    def start_animation(self, event):
        self.playing_animation = True

    def stop_animation(self, event):
        self.playing_animation = False

    def _on_close(self, event):
        plt.close("all")
