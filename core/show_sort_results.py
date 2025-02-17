import os, sys, json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from matplotlib.animation import FuncAnimation
from PIL import Image
from typing import Dict, List


class SortResultsViewer(object):
    def __init__(self, file_list: List[str], img_dirs: List[str], figure_header: str):
        self.file_list = file_list
        self.img_dirs = img_dirs
        self.num_dir = len(img_dirs)
        if self.num_dir > 2 or self.num_dir < 1:
            raise ValueError(f"Only supporting 1 or 2 images per figure, stored in separate directories; got {self.num_dir} directories.")
        self.curr_idx = 0 # current index of image/mask pair to display
        self.num_reviewed = len(file_list)
        self.figure_header = figure_header
        self.create_figure()
        self.create_buttons()
        self.playing_animation = False
        self.set_animator()
        plt.show()

    def create_figure(self):
        # create figure and axes
        self.fig, self.axes = plt.subplots(1, self.num_dir, figsize=(10, 5))
        fig_title = f"{self.figure_header}\n{self.file_list[self.curr_idx]}\nProgress: {self.curr_idx+1}/{self.num_reviewed}"
        self.fig.suptitle(t=fig_title, fontsize='x-large', wrap=True)
        manager = plt.get_current_fig_manager()
        # this apparently doesn't work in Linux and none of the options that the Exception recommended did the same job
        #manager.window.state('zoomed')
        # making self.axes a list since plt.subplots(1,1) gives a non-iterable type axes
        if self.num_dir == 1:
            self.axes = [self.axes]
        # load and initialize axes with initial images
        self.img_display = [None for _ in range(self.num_dir)]
        for i in range(self.num_dir):
            img = Image.open(os.path.join(self.img_dirs[i], self.file_list[self.curr_idx]))
            self.img_display[i] = self.axes[i].imshow(img)
            self.axes[i].axis('off')
        self.fig.set_tight_layout(True)

    def create_buttons(self):
        # axes args order: [left, bottom, width, height]
        self.buttons = {
            'prev': Button(plt.axes([0.52, 0.025, 0.1, 0.075]), 'PREVIOUS'),
            'next': Button(plt.axes([0.63, 0.025, 0.1, 0.075]), 'NEXT'),
            'start': Button(plt.axes([0.74, 0.025, 0.1, 0.075]), 'START'),
            'stop': Button(plt.axes([0.85, 0.025, 0.1, 0.075]), 'STOP')
        }
        self.buttons['start'].on_clicked(self.start_animation)
        self.buttons['stop'].on_clicked(self.stop_animation)
        # register event handler
        self.fig.canvas.mpl_connect('button_press_event', self.on_button_click)

    def set_animator(self):
        # animation object (initially not running)
        SECONDS_PER_FRAME = 2.5
        self.ani = FuncAnimation(self.fig, self.update_frame, init_func=(lambda : []), interval=SECONDS_PER_FRAME*1000, repeat=True)
        # ani.event_source.stop()  # stop animation

    # update display function
    def update_display(self, index):
        for i in range(self.num_dir):
            file_path = os.path.join(self.img_dirs[i], self.file_list[index])
            img = Image.open(file_path)
            self.img_display[i].set_data(img)
        # redraw canvas
        fig_title = f"{self.figure_header}\n{self.file_list[self.curr_idx]}\n{self.curr_idx+1}/{self.num_reviewed}"
        self.fig.suptitle(t=fig_title, fontsize='x-large', wrap=True)
        self.fig.canvas.draw()
        #fig.set_tight_layout(True)

    # button event handler
    def on_button_click(self, event):
        # update current index
        if event.inaxes == self.buttons['next'].ax:
            self.curr_idx = (self.curr_idx + 1) % self.num_reviewed
        elif event.inaxes == self.buttons['prev'].ax:
            self.curr_idx = (self.curr_idx - 1) % self.num_reviewed
        # update display
        self.update_display(self.curr_idx)

    # animation update function
    def update_frame(self, frame):
        # increment current index and wrap around at end of list
        if self.playing_animation:
            self.curr_idx = (self.curr_idx + 1) % self.num_reviewed
            # update display
            self.update_display(self.curr_idx)

    # start/stop button event handlers
    def start_animation(self, event):
        #ani.event_source.start()
        self.playing_animation = True

    def stop_animation(self, event):
        #ani.event_source.stop()
        self.playing_animation = False


'''if __name__ == "__main__":
    # reading intended files to review from the json
    output_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'disputed_labels', 'sorting_output.json')
    with open(output_path, 'r') as fptr:
        sorted_dict = dict(json.load(fptr))
    # directories
    seg_dirs = [os.path.join('data', 'soiling_dataset', 'train', 'rgbImages'),
                os.path.join('data', 'soiling_dataset', 'train', 'rgbLabels')]
    # get sorted list of file names in both directories
    image_files = sorted(sorted_dict['disagree'])
    sort_viewer = SortResultsViewer(image_files, seg_dirs, "Disputed Labels")'''