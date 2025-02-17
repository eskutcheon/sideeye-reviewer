'''
    Multilabel Image Reviewer for sorting images into multiple classes - under construction
        This is mainly made for to sort the contended segmentations into different groups based on why we disagree with them.
        The purpose will be both for documentation and identifying those that can be amended
    NOTE: May just integrate into the original image_reviewer.py file later, but I'm not sure how much has to change.
    ########################################################################################################################
    What needs to change + progress on task
    * BinManager will now need to accept multiple labels
        ~~- seems like add_filename can just be updated to iterate over new argument labels as a list of strings rather than a single string~~
        ~~- the elements of sort_history will need to now take the form of a filename and list of labels to push and pop properly~~
        ~~- the undo_sort function will need to be updated to pop from sort_history, get all labels, then pop from the sorting_dict ~~
            ~~ by iterating over the labels that were popped from the deque ~~
        ~~- get_num_sorted will need to be updated to properly do checkpointing of files ~~
            ~~ though it may be as easy as getting a single list of all filenames, removing duplicates, then counting them ~~
    * ImageSorter needs updates to work with BinManager changes
        - otherwise will only need work if I choose to compute new overlays in real time rather than reading from file
        ~~- Do need to ensure interface with BinManager is updated for the right inputs and outputs~~
            ~~- didn't update all the way to on_button_press_callback but the part it's in needs to be updated for checkboxes~~
    * ImageReviewer will need to handle most selection callbacks differently and process input only upon choosing "NEXT"
        - If I'm adding a "NEXT" button, need to ensure that the reviewer circles back to any images that are skipped with no selection
            - or possibly add a hovering warning message over the mouse when clicking "NEXT" in this state
        - Should add checkboxes for each of the contention types, "other" or "no contention"
            - "no contention" should trigger a resorting from the calling script to redo the old JSONs and ensure anything with this
            label is sorted among the "agreed" labels - If I don't get to this, at least make sure to update it manually later
        ~~- Probably need to consider removing the hint buttons - adds too much extra complexity with the Window management~~
        - May not need to change much in on_button_press_callback since I don't want to trigger actions except when buttons, not checkboxes, are clicked
            - do need to update the part with the user-created buttons
        - should probably deal with the self.manager member to not break on Linux (haven't checked functionality on Mac, etc)
        - if I remove the hint buttons, self.cidpress can be removed, buttons can be replaced with the on_clicked callbacks,
        and I don't have to handle each click of the canvas
'''

import os, sys, json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, CheckButtons
#from matplotlib.backend_bases import Event, MouseEvent
from matplotlib import get_backend
import numpy as np
from time import sleep
from typing import Union, List, Tuple, Callable, Dict, Deque
from collections import OrderedDict, deque



# UPDATE: now returns button axes centered between right_bound and left_bound
def get_button_axes(num_buttons: int, left_bound: float, right_bound: float):
    width, spacing = 0.1, 0.01
    total_width = (width + spacing)*num_buttons - spacing  # total width of all buttons including spacing
    if total_width > right_bound - left_bound:  # if total width exceeds available space, scale down
        scale = (right_bound - left_bound)/total_width
        width *= scale
        spacing *= scale
        total_width = (width + spacing)*num_buttons - spacing  # recalculate total width
    # calculate additional padding needed to center buttons
    padding = (right_bound - left_bound - total_width)/2
    left_bound += padding  # update left_bound to center buttons
    # TODO: adjust the lower and upper axes as needed later - top of buttons at 0.1 on figure
    return [[left_bound + i*(width + spacing), 0.025, width, 0.075] for i in range(num_buttons)]

class BinManager(object):
    def __init__(self, labels: List[str], out_dir: str, outfile_name: str):
        self.out_dir: str = out_dir
        self.output_json: str = os.path.join(out_dir, outfile_name)
        self.sorting_dict: Dict[str, List[str]] = {}
        self.sort_history: Deque[Dict[str, List[str]]] = deque()
        self.json_contents: Dict[str, List[str]] = {}
        for bin in labels:
            self.sorting_dict[bin] = deque()

    # UPDATE: changed function to iterate over a list of labels, so now labels is a list of strings and sort_history's elements are dicts
    def add_filename(self, labels: List[str], filename: str):
        if not isinstance(labels, list) and isinstance(labels, str):
            labels = [labels]
        for label in labels:
            if label not in self.sorting_dict:
                raise ValueError(f"No bin with label {label} found.")
            if filename not in self.sorting_dict[label]:
                self.sorting_dict[label].append(filename)
        self.sort_history.append({filename: labels})
        print(f"Added {filename} to bins {labels}")

    # UPDATE: changed function to remove the filename from all associated bins based on the dict popped from sort_history
    def undo_sort(self):
        if not self.sort_history:
            print("sort_history is empty")
            return
        last_file_dict = self.sort_history.pop()
        # assuming all strings in a bin should be unique
        for filename, label_list in last_file_dict.items():
            for label in label_list:
                self.sorting_dict[label].remove(filename)
            print(f"Removed {filename} from bins {label_list}.")

    # UPDATE: Now makes one big list of files across all bins, converts it to a set, and returns the length of the set
    def get_num_sorted(self):
        if not os.path.exists(self.output_json):
            return 0
        with open(self.output_json, 'r') as fptr:
            self.json_contents = dict(json.load(fptr))
        all_files = []
        for bin_list in self.json_contents.values():
            # TODO: Should really use append for efficiency's sake but this is only called once and I don't wanna read docs right now
            all_files = [*all_files, *bin_list]
        return len(set(all_files))

    # FIXME: There's something causing the json to be overwritten without existing elements when not giving the entire file_list to the sorter
    def write_to_outfiles(self):
        output_dict = {label: list(bin) for label, bin in self.sorting_dict.items()}
        for label, bin in self.json_contents.items():
            for filename in bin:
                try:
                    output_dict[label].append(filename)
                except:
                    raise KeyError(f"ERROR: Got unexpected key '{label}'. Ensure that JSON {self.output_json} is the intended output file.")
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

    def update_bin(self, labels: List[str], remove=False):
        if remove:
            self.bin_manager.undo_sort()
        else:
            self.bin_manager.add_filename(labels, self.current_image)


# TODO: Consider creating a custom figure class to hold only the figs, buttons, etc
class ImageReviewer(object):
    def __init__(self, Sorter: ImageSorter, criteria_labels: dict=None):
        self.Sorter: ImageSorter = Sorter
        self.sorter_bins: List[str] = Sorter.sorter_labels
        # TODO: rename this to something related to the segmentation labels or just color_labels
        self.criteria_dict = criteria_labels
        self.num_images_in_fig = self.Sorter.num_dirs
        self.fig, self.axs = plt.subplots(1, self.num_images_in_fig, facecolor = 'lightgray')
        self.main_fig_id = self.fig.number
        self.fig.canvas.mpl_connect('close_event', self.close_callback)
        self.state_flags = {'undo': False, 'stop': False, 'updated': False}
        # TODO: need to change this to something system agnostic since Linux doesn't use the same window backend (might just be able to set this manually)
        # maximize the window by default
        self.maximize_window()
        self.cidpress = self.fig.canvas.mpl_connect('button_press_event', self.on_button_press_callback)
        self.create_buttons()

    def maximize_window(self):
        self.manager = plt.get_current_fig_manager()
        backend = get_backend()
        if backend == 'TkAgg':
            if sys.platform.startswith('win'):  # For windows
                self.manager.window.state('zoomed')
            else:  # For Linux
                self.manager.window.wm_attributes('-zoomed', '1')
        elif backend == 'Qt5Agg':
            self.manager.window.showMaximized()
        elif backend == 'WXAgg':
            self.manager.window.Maximize()
        else:
            print(f"WARNING: Unsupported backend {backend} for maximize operation")

    # UPDATE: Removed user-defined buttons, added a "NEXT" button, and added checkboxes with the sorter label names
    def create_buttons(self):
        self.buttons: dict = {}
        # TODO: adjust left bound based on the legend size
        button_axes = get_button_axes(num_buttons=3, left_bound=0.25, right_bound=0.75)
        num_labels = len(self.sorter_bins)
        # parent figure for checkboxes - adjust position and size as needed
        rax = plt.axes([0.8, 0.025, 0.18, 0.125])
        # NOTE: Not sure about adding the axes since I'm not sure if this is inherited from AxisWidgets
        self.checkboxes = CheckButtons(self.fig.add_axes(rax), self.sorter_bins, actives=[False for _ in range(num_labels)])
        self.buttons['undo'] = Button(self.fig.add_axes(button_axes[0]), label='UNDO')
        #self.buttons['undo'].on_clicked(self.undo_callback)
        self.buttons['next'] = Button(self.fig.add_axes(button_axes[1]), label='NEXT')
        #self.buttons['undo'].on_clicked(self.next_callback)
        self.buttons['stop'] = Button(self.fig.add_axes(button_axes[2]), label='STOP')
        #self.buttons['stop'].on_clicked(self.stop_callback)

    def create_legend(self, topic_labels: dict):
        if np.all([isinstance(val, str) for val in list(topic_labels.values())]):
            for label, criterion in topic_labels.items():
                plt.plot([], [], color=criterion, label=label)
        self.legend = self.fig.legend(loc='lower left', fontsize='large', markerscale=5)

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
        self.fig.canvas.mpl_connect('close_event', self.close_callback)

    def stop_review(self):
        print("Now stopping review process. This session will be saved.")
        self.Sorter.bin_manager.write_to_outfiles()
        # TODO: really need to replace this with a flag to exit back to the calling script
        self.state_flags['stop'] = True

    def stop_callback(self, event):
        self.stop_review()

    # TODO: need to fix this error message every time the figure closes, so need to revist setting the stop flag
    def close_callback(self, event):
        if not self.state_flags['stop']:
            print('ERROR: figure closed unexpectedly. This event will be treated as a "STOP" selection.')
            self.stop_callback(event)

    def undo_callback(self, event):
        # Passing a list with an empty string to be consistent with arguments, but it's not used anywhere
        self.Sorter.update_bin([''], remove=True)
        self.state_flags['undo'] = True

    def display_warning(self, message="Warning!", duration=3000):
        txt = self.fig.text(0.5, 0.15, message, ha='center', va='center', fontsize=18, color='red')
        self.fig.canvas.draw()
        def remove_text():
            try:
                txt.remove()
                self.fig.canvas.draw()
            except ValueError:
                pass
        # Create a timer that will remove the text after `duration` milliseconds
        timer = self.fig.canvas.new_timer(interval=duration)
        timer.add_callback(remove_text)
        timer.start()

    def next_callback(self, event):
        checkbox_generator = zip(self.sorter_bins, self.checkboxes.get_status())
        chosen_bins = []
        for idx, (bin_name, box_status) in enumerate(checkbox_generator):
            if box_status:
                chosen_bins.append(bin_name)
                # toggle any checked boxes back to unchecked
                self.checkboxes.set_active(idx)
        if len(chosen_bins) != 0:
            self.Sorter.update_bin(chosen_bins)
            self.state_flags['updated'] = True
        else:
            self.display_warning("WARNING: Cannot choose 'NEXT' button with no checkboxes filled.", 5000)

    def print_all_flags(self):
        for key, val in self.state_flags.items():
            print(f"flag {key} = {val}")

    def on_button_press_callback(self, event):
        # TODO: really want to use the buttons as intended, but it keeps messing up when processing clicks on both button and figure canvases
        # process button presses here
        try:
            if event.inaxes == self.buttons['undo'].ax:
                self.undo_callback(event)
            elif event.inaxes == self.buttons['stop'].ax:
                self.stop_callback(event)
            elif event.inaxes == self.buttons['next'].ax:
                self.next_callback(event)
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
                elif self.state_flags['updated']:
                    if (idx < num_to_review-1):
                        idx += 1
                        self.state_flags['updated'] = False
                    else:
                        plt.close(self.fig)
                else:
                    continue
                self.fig.canvas.flush_events()
        plt.close(self.fig)
        sleep(2)
