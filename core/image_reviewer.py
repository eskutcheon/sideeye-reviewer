'''
    My attempt at making something more general so we can reuse it for reviewing many parts of the dataset
'''

import os, sys, json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from matplotlib.backend_bases import Event, MouseEvent
import numpy as np
from time import sleep
from typing import Union, List, Tuple, Callable, Dict
from collections import OrderedDict, deque


# TODO: move this and other functions from the camera_type_review file to a utils file
def get_button_axes(num_buttons: int, right_bound: float, left_bound: float):
    if num_buttons > 8:
        raise NotImplementedError("Currently only supporting up to 8 buttons") # just how the math worked out
    width, spacing = 0.1, 0.01
    if right_bound-(width+spacing)*num_buttons < left_bound:
        width *= 0.75
        spacing *= 0.75
    left_bound = max(left_bound, right_bound-(width+spacing)*num_buttons)
    return [[left_bound + i*(width+spacing), 0.025, width, 0.075] for i in range(num_buttons)]

class BinManager(object):
    def __init__(self, labels, out_dir, outfile_name):
        self.out_dir = out_dir
        self.output_json = os.path.join(out_dir, outfile_name)
        self.sorting_dict = {}
        self.sort_history = deque()
        self.json_contents = {}
        for bin in labels:
            self.sorting_dict[bin] = deque()

    def add_filename(self, label, filename):
        if label not in self.sorting_dict:
            raise ValueError(f"No bin with label {label} found.")
        if filename not in self.sorting_dict[label]:
            self.sorting_dict[label].append(filename)
            self.sort_history.append((label, filename))
            print(f"Added {filename} to {label} bin")

    def undo_sort(self):
        if not self.sort_history:
            print("sort_history is empty")
            return
        last_label, last_string = self.sort_history.pop()
        # assuming all strings in a bin are unique
        self.sorting_dict[last_label].remove(last_string)
        print(f"Removed {last_string} from '{last_label}' bin.")

    def get_num_sorted(self):
        if not os.path.exists(self.output_json):
            return 0
        with open(self.output_json, 'r') as fptr:
            self.json_contents = dict(json.load(fptr))
        return sum([len(bin) for bin in self.json_contents.values()])

    # FIXME: There's something causing the json to be overwritten without existing elements when not giving the entire file_list to the sorter
    def write_to_outfiles(self):
        output_dict = {label: list(bin) for label, bin in self.sorting_dict.items()}
        for label, bin in self.json_contents.items():
            for filename in bin:
                output_dict[label].append(filename)
            output_dict[label] = sorted(list(set(output_dict[label])))
        with open(self.output_json, 'w') as fptr:
            json.dump(output_dict, fptr, indent=4)

class ImageSorter(object):
    def __init__(self, image_folders: Union[List[str], Tuple[str], str], out_dir: str, labels: List[str], file_list=None, json_name='sorting_output.json'):
        ''' constructor performs initial integrity check from driver and member variable initializations
            Args:
                image_folders: May be an iterable of up to 2 directory paths or a str for a single path
                out_dir: the directory in which output files will be written
                labels: the labels for the bins that the reviewer sorts filenames into
                file_list (optional): a list of filenames that will be used in place of all files in img_dirs
        '''
        if isinstance(image_folders, str):
            self.img_dirs = [image_folders]
        else:
            self.img_dirs = list(image_folders)
        # only supporting up to 2 folders for now
        self.num_dirs = len(self.img_dirs)
        if self.num_dirs > 2:
            raise NotImplementedError('ERROR: only supporting either a single image directory or pair of image and mask directories.')
        # if output path doesn't exist, create it recursively
        os.makedirs(out_dir, exist_ok=True)
        self.out_dir = out_dir
        # self.file_list will be returned upon call to self.get_file_list
        if file_list is not None:
            self.file_list = file_list
        # mainly making this to access from the reviewer to make buttons
        self.sorter_labels = labels
        # Initializes the container which will contain the bins that files will be sorted into
        self.bin_manager = BinManager(labels, out_dir, json_name)

    # Optional checkpoint flag allows a user to begin at square one even if file history exists
    def check_if_resuming(self, checkpoint=True) -> Union[None, int]:
        # TODO: may need to switch this to a class variable to ensure that checkpointing occurs correctly when file_list is given
            # will probably wrap this in two other functions if that is the case
        if not checkpoint:
            return None
        # inequality argument of 2 is just because bool can implicitly be an int in {0,1}
        if isinstance(checkpoint, int) and checkpoint >= 2:
            return checkpoint
        files_checked = self.bin_manager.get_num_sorted()
        # Handles the case of existing, but empty files
        if files_checked == 0:
            return None
        return files_checked

    def get_file_list(self, checkpoint=None) -> List[str]:
        # using a single file list under the assumption that all input will have the same names
        file_list = []
        if hasattr(self, 'file_list'):
            file_list = self.file_list
        else:
            file_list = os.listdir(self.img_dirs[0])
        # get part of list after checkpoint index if checkpoint is not None
        if checkpoint is not None and checkpoint < len(file_list):
            file_list = file_list[checkpoint:]
        return file_list

    def get_image_paths(self, img_name: str) -> List[str]:
        return [os.path.join(self.img_dirs[i], img_name) for i in range(self.num_dirs)]

    def set_current_image(self, img_name):
        self.current_image = img_name

    def update_bin(self, label, remove=False):
        if remove:
            self.bin_manager.undo_sort()
        else:
            self.bin_manager.add_filename(label, self.current_image)


# TODO: Consider creating a custom figure class to hold only the figs, buttons, etc
class ImageReviewer(object):
    def __init__(self, Sorter: ImageSorter, criteria_labels: dict=None):
        self.Sorter: ImageSorter = Sorter
        self.sorter_bins: List[str] = Sorter.sorter_labels
        self.criteria_dict = criteria_labels
        self.num_images_in_fig = self.Sorter.num_dirs
        self.fig, self.axs = plt.subplots(1, self.num_images_in_fig)
        self.main_fig_id = self.fig.number
        self.fig.canvas.mpl_connect('close_event', self.close_callback)
        self.state_flags = {'undo': False, 'stop': False, 'do_nothing': False, 'updated': False, 'showing_hint': False}
        # maximize the window by default
        self.manager = plt.get_current_fig_manager()
        # this apparently doesn't work in Linux and none of the options that the Exception recommended did the same job
        self.manager.window.state('zoomed')
        self.cidpress = self.fig.canvas.mpl_connect('button_press_event', self.on_button_press_callback)
        self.create_buttons(self.sorter_bins)
        # plt.ion() # run GUI event loop


    def create_buttons(self, sorter_labels):
        self.buttons: dict = {}
        ''' To implement later: take right boundary as 0.9 or 0.95, 0.5 as left boundary
            Note: Button width should be 10 units by default
        '''
        num_buttons = len(sorter_labels) + 2 # given buttons plus stop and undo buttons
        button_axes = get_button_axes(num_buttons, 0.95, 0.3)
        for idx, name in enumerate(sorter_labels):
            self.buttons[name] = Button(self.fig.add_axes(button_axes[idx]), label=name.upper())
            #self.buttons[name].on_clicked(self.get_update_bin_callback(name))
        self.buttons['undo'] = Button(self.fig.add_axes(button_axes[-2]), label='UNDO')
        #self.buttons['undo'].on_clicked(self.undo_callback)
        self.buttons['stop'] = Button(self.fig.add_axes(button_axes[-1]), label='STOP')
        #self.buttons['stop'].on_clicked(self.stop_callback)

    def create_legend(self, topic_labels: dict):
        if hasattr(self, 'hint_buttons'):
            raise Exception("In the case of single-image review, you cannot have both a legend and hint buttons")
        if np.all([isinstance(val, str) for val in list(topic_labels.values())]):
            for label, criterion in topic_labels.items():
                plt.plot([], [], color=criterion, label=label)
        self.legend = self.fig.legend(loc='lower left', fontsize='large', markerscale=3)

    def create_hint_buttons(self, hint_dict: dict):
        if hasattr(self, 'legend'):
            raise Exception("In the case of single-image review, you cannot have both a legend and hint buttons")
        self.hint_buttons = {}
        button_axes = np.array(get_button_axes(len(hint_dict.keys()), 0.98, 0.7))
        button_axes[:, (1,0)] = button_axes[:, (0,1)]
        button_axes[:,1] = 0.9 - button_axes[:,1]
        button_axes[:,0] -= 0.01
        for idx, key in enumerate(hint_dict.keys()):
            self.hint_buttons[key] = Button(self.fig.add_axes(button_axes[idx]), label=f"{key}\nhint".upper())
            #self.hint_buttons[key].on_clicked(self.get_show_hint_callback(key))

    def initialize_figure(self, images_to_read: List[str]):
        if self.num_images_in_fig > 1:
            self.axs[0].axis('off')
            self.axs[1].axis('off')
            self.canvas_images = [self.axs[i].imshow(plt.imread(images_to_read[i])) for i in range(self.num_images_in_fig)]
            plt.tight_layout()
            self.create_legend(self.criteria_dict)
        else:
            self.axs.axis('off')
            self.canvas_images = [self.axs.imshow(plt.imread(images_to_read[0]), aspect='auto')]
            self.create_hint_buttons({key: os.path.basename(val) for key, val in self.criteria_dict.items()})
        self.fig.canvas.mpl_connect('close_event', self.close_callback)

    def get_update_bin_callback(self, bin_name: str) -> Callable:
        def callback(event):
            self.Sorter.update_bin(bin_name)
            self.state_flags['updated'] = True
        return callback

    def get_show_hint_callback(self, hint_name: str):
        def callback(event):
            img_path = self.criteria_dict[hint_name]
            figure, axs = plt.subplots(1, 1)
            self.state_flags['showing_hint'] = True  # Set the flag to pause event handling
            axs.axis('off')
            figure.suptitle(t=f"Example of {hint_name.upper()}: {os.path.basename(img_path)}", fontsize='x-large')
            image = plt.imread(img_path)
            canvas = axs.imshow(image, aspect='auto')
            canvas.set_data(image)
            figure.canvas.draw()
            plt.show(block=True)
            plt.close(figure)  # Close the figure
            try:
                click_event = MouseEvent('button_press_event', self.fig.canvas, 0.995, 0.005, 1)
                self.fig.canvas.callbacks.process('button_press_event', click_event)
            except RuntimeError:
                pass
            plt.figure(self.main_fig_id)
        return callback

    def stop_review(self):
        print("Now stopping review process. This session will be saved.")
        self.Sorter.bin_manager.write_to_outfiles()
        # TODO: really need to replace this with a flag to exit back to the calling script
        self.state_flags['stop'] = True
        #sys.exit(0)

    def stop_callback(self, event):
        self.stop_review()

    # TODO: need to fix this error message every time the figure closes, so need to revist setting the stop flag
    def close_callback(self, event):
        if not self.state_flags['stop']:
            print('ERROR: figure closed unexpectedly. This event will be treated as a "STOP" selection.')
            self.stop_callback(event)

    def undo_callback(self, event):
        self.Sorter.update_bin('', remove=True)
        self.state_flags['undo'] = True

    def print_all_flags(self):
        for key, val in self.state_flags.items():
            print(f"flag {key} = {val}")

    def on_button_press_callback(self, event):
        # TODO: really want to use the buttons as intended, but it keeps messing up when processing clicks on both button and figure canvases
        # process button presses here
        try:
            if self.state_flags['showing_hint']:
                self.state_flags['showing_hint'] = False
                return
            if event.inaxes == self.buttons['undo'].ax:
                self.undo_callback(event)
            elif event.inaxes == self.buttons['stop'].ax:
                self.stop_callback(event)
            else:
                for name in self.sorter_bins:
                    if event.inaxes == self.buttons[name].ax:
                        self.get_update_bin_callback(name)(event)
                        break
                if hasattr(self, 'hint_buttons'):
                    for name in self.hint_buttons.keys():
                        if event.inaxes == self.hint_buttons[name].ax:
                            self.get_show_hint_callback(name)(event)
                            break
        except RuntimeError:
            pass

    def update_figure(self, img_paths: List[str], fig_title: str):
        images = [plt.imread(img_paths[i]) for i in range(self.num_images_in_fig)]
        self.fig.suptitle(t=fig_title, fontsize='x-large')
        for i in range(self.num_images_in_fig):
            self.canvas_images[i].set_data(images[i])
        self.fig.canvas.draw()

    def begin_review(self, checkpoint: Union[bool, int] = True):
        ''' still only meant to work with up to two images, in which case it's intended for segmentation masks with the same filename '''
        checkpoint_idx = self.Sorter.check_if_resuming(checkpoint)
        start_idx = 0 if checkpoint_idx is None else checkpoint_idx
        file_list = self.Sorter.get_file_list(checkpoint_idx)
        self.initialize_figure(self.Sorter.get_image_paths(file_list[0]))
        num_to_review = len(file_list)
        self.fig.show()
        idx = 0
        with plt.ion():
            while idx < num_to_review:
                if self.state_flags['stop']:
                    break
                self.Sorter.set_current_image(file_list[idx])
                img_paths = self.Sorter.get_image_paths(file_list[idx])
                fig_title = f"{file_list[idx]}\n{idx+1+start_idx}/{num_to_review+start_idx}"
                self.update_figure(img_paths, fig_title)
                try:
                    while plt.waitforbuttonpress():
                        plt.pause(0.1)
                except RuntimeError:
                    pass
                if self.state_flags['undo']:
                    if (idx > 0):
                        idx -= 1
                    self.state_flags['undo'] = False
                elif self.state_flags['do_nothing']:
                    self.state_flags['do_nothing'] = False
                elif self.state_flags['updated']:
                    if (idx < num_to_review-1):
                        idx += 1
                        self.state_flags['updated'] = False
                    else:
                        plt.close(self.fig)
                elif self.state_flags['showing_hint']:
                    self.state_flags['showing_hint'] = False
                else:
                    continue
                self.fig.canvas.flush_events()
        plt.close(self.fig)
        sleep(2)
