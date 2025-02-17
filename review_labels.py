import os
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from typing import Union
# from tqdm import tqdm



# TODO: break this back up into more functions
    # I had this decomposed further, but I started trying to add functionality without backing things up
def process_images(image_dir, label_dir, checkpoint=None):
    # sorted the list first just in case any machine-specific shuffling happens
    image_files = sorted(os.listdir(image_dir))
    label_files = sorted(os.listdir(label_dir))
    # get part of list after checkpoint index if checkpoint is not None
    if checkpoint is not None:
        image_files = image_files[checkpoint:]
        label_files = label_files[checkpoint:]
    # lists to save the pairs to
    agree_pairs = []
    disagree_pairs = []
    legend_labels = {'clean': 'black', 'transparent': 'green', 'semi-transparent': 'blue', 'opaque': 'red'}
    global stop
    stop = False
    for image_name, label_name in zip(image_files, label_files):
        # should only be triggered when stop button is called
        if stop:
            break
        image = plt.imread(os.path.join(image_dir, image_name))
        label = plt.imread(os.path.join(label_dir, label_name))
        # setup matplotlib figure and axes - 1 row, 2 columns
        fig, axs = plt.subplots(1, 2)
        fig.suptitle(image_name)
        axs[0].imshow(image, aspect='auto')
        axs[0].set_title("Image")
        axs[1].imshow(label, aspect='auto')
        axs[1].set_title("Label")
        plt.subplots_adjust(bottom=0.2)
        # create legend with the meaning of each color
        for label, color in legend_labels.items():
            plt.plot([], [], color=color, label=label)
        fig.legend(loc='lower left', fontsize='large')
        # setup agree, disagree and stop buttons
        agree_button = Button(fig.add_axes([0.59, 0.05, 0.1, 0.075]), 'Agree')
        disagree_button = Button(fig.add_axes([0.7, 0.05, 0.1, 0.075]), 'Disagree')
        stop_button = Button(fig.add_axes([0.81, 0.05, 0.1, 0.075]), 'Stop')
        # define button callbacks
        def agree_callback(event):
            agree_pairs.append((image_name, label_name))
            plt.close(fig)
        def disagree_callback(event):
            disagree_pairs.append((image_name, label_name))
            plt.close(fig)
        def stop_callback(event):
            global stop
            stop = True
            plt.close(fig)
        # link callbacks to each button
        agree_button.on_clicked(agree_callback)
        disagree_button.on_clicked(disagree_callback)
        stop_button.on_clicked(stop_callback)
        # TODO: need to stop the program when the window is prematurely closed with no answer
        # maximize the window and show plot
        manager = plt.get_current_fig_manager()
        manager.window.state('zoomed')
        plt.show()
    return agree_pairs, disagree_pairs


def check_output_path(out_dir, make_subdir=False):
    # check if the new directories exist
    def mkdir(path):
        if not os.path.isdir(path):
            os.makedirs(path)
    if make_subdir:
        for name in ['img', 'mask']:
            mkdir(os.path.join(out_dir, name))
    else:
        mkdir(out_dir)

# Unused - need to call it call it all properly in main and test that it works
def save_in_new_dir(img_dir, mask_dir, out_dir, file_pair):
    # write image and label to new directory
    check_output_path(out_dir, make_subdir=True)
    img_tensor = plt.imread(os.path.join(img_dir, file_pair[0]))
    plt.imsave(os.path.join(out_dir, 'img', file_pair[0]), img_tensor)
    mask_tensor = plt.imread(os.path.join(mask_dir, file_pair[1]))
    plt.imsave(os.path.join(out_dir, 'mask', file_pair[1]), mask_tensor)


def check_if_resuming(out_files: list) -> Union[None, int]:
    files_checked = 0
    for file in out_files:
        if not os.path.exists(file):
            return None
        with open(file, 'r') as fptr:
            files_checked += len(fptr.readlines())
    # Handles the case of existing, but empty files
    if files_checked == 0:
        return None
    return files_checked

if __name__ == "__main__":
    # change if doing this for the test directory too
    image_folder = os.path.join('..', 'data', 'soiling_dataset', 'train', 'rgbImages')
    label_folder = os.path.join('..', 'data', 'soiling_dataset', 'train', 'rgbLabels')
    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'disputed_labels')
    check_output_path(output_dir)
    # check if early stopping occurred and return count of files reviewed if so
    # NOTE: Comment this out if you want to start over, or it'll pick up where you left off
    checkpoint = check_if_resuming([os.path.join(output_dir, 'disputed_labels.txt'),
                                    os.path.join(output_dir, 'undisputed_labels.txt')])
    # main loop for reviewing the images - checkpoint allows for resumed reviewing
    agreed, disagreed = process_images(image_folder, label_folder, checkpoint)
    for name, file_list in zip(['disputed_labels.txt', 'undisputed_labels.txt'], [agreed, disagreed]):
        with open(os.path.join(output_dir, name), 'a') as fptr:
            for file_pair in file_list:
                fptr.write(f"{file_pair[0]}\n")