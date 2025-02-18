import os
import sys
import json
from collections import Counter
from typing import Dict, List, Union, Tuple
from matplotlib import get_backend
import matplotlib.pyplot as plt


def maximize_window():
    manager = plt.get_current_fig_manager()
    backend = get_backend()
    if backend in ['TkAgg', 'tkagg']:
        if sys.platform.startswith('win'):  # For windows
            manager.window.state('zoomed')
        else:  # For Linux
            manager.window.wm_attributes('-zoomed', '1')
    elif backend in ["Qt5Agg", "qtagg"]:
        manager.window.showMaximized()
    elif backend == 'WXAgg':
        manager.window.Maximize()
    else:
        print(f"WARNING: Unsupported backend {backend} for maximize operation")


# UPDATE: now returns button axes centered between right_bound and left_bound
def get_button_axes(num_buttons: int, left_bound: float = 0.3, right_bound: float = 0.95):
    width, spacing = 0.1, 0.01
    total_width = (width + spacing) * num_buttons - spacing  # total width of all buttons including spacing
    if total_width > right_bound - left_bound:  # if total width exceeds available space, scale down
        scale = (right_bound - left_bound)/total_width
        width *= scale
        spacing *= scale
        total_width = (width + spacing) * num_buttons - spacing  # recalculate total width
    # calculate additional padding needed to center buttons
    padding = (right_bound - left_bound - total_width)/2
    left_bound += padding  # update left_bound to center buttons
    # TODO: adjust the lower and upper axes as needed later - top of buttons at 0.1 on figure
    return [[left_bound + i*(width + spacing), 0.025, width, 0.075] for i in range(num_buttons)]


def get_user_confirmation(prompt):
    answers = {'y': True, 'n': False}
    response = input(f"[Y/n] {prompt} ").lower()
    while response not in answers:
        print("Invalid input. Please enter 'y' or 'n' (not case sensitive).")
        response = input(f"[Y/n] {prompt} ").lower()
    return answers[response]



#* file contents handling helper functions:

def remove_newlines(file_list: List[str]) -> List[str]:
    return list(map(lambda x: x.rstrip('\n'), file_list))

def get_all_duplicates(file_list: List[str]) -> List[str]:
    counts = Counter(file_list)
    return [filename for filename in counts if counts[filename] > 1 for _ in range(counts[filename]-1)]

def check_file_path(out_file_path: str, extension: str):
    if not os.path.exists(out_file_path):
        raise FileNotFoundError(f"{out_file_path} not found")
    _, output_ext = os.path.splitext(out_file_path)
    # reason for the redunancy is just that the above will miss existing files with the wrong extension
    if output_ext != extension:
        raise ValueError(f"out_file_path must include the file's name including '{extension}'")

def check_if_double_sorted(files_reviewed, file_list):
    if any(map(lambda x: x in files_reviewed, file_list)):
        print("ERROR: duplicate file names found between multiple txt files:")
        print(set(file_list).intersection(files_reviewed))
        raise Exception("files double sorted")

def remove_duplicate_files_txt(duplicates: Dict[str, List[str]], out_dir: str):
    # weird setup - duplicates should have duplicate elements for the case where more than 2 duplicates were found in the files
    for name in duplicates.keys():
        out_file_path = os.path.join(out_dir, f'{name}_labels.txt')
        check_file_path(out_file_path, extension='.txt')
        with open(os.path.join(out_dir, f'{name}_labels.txt'), 'r') as fptr:
            file_list = fptr.readlines()
        for duplicate in duplicates[name]:
            if duplicate in file_list:
                file_list.remove(duplicate)  # remove only the first occurrence of duplicate
        print(f'length of {name}_labels.txt after duplicate removal: {len(file_list)}')
        with open(os.path.join(out_dir, f'{name}_labels.txt'), 'w') as fptr:
            for file in file_list:
                fptr.write(file)

def remove_duplicate_files_json(out_file_path: str):
    check_file_path(out_file_path, extension='.json')
    out_dict = {}
    with open(out_file_path, 'r') as fptr:
        out_dict = dict(json.load(fptr))
        for key in out_dict.keys():
            out_dict[key] = sorted(list(set(out_dict[key])))
    with open(out_file_path, 'w') as fptr:
        json.dump(out_dict, fptr, indent=4)

# get a flat list of all sorted files while removing duplicates and finding double sorted files
def get_all_reviewed_files_txt(out_dir: str, sorter_labels: List[str]) -> List[str]:
    duplicates = {}
    # Put this in a loop because the method I was using wasn't getting them all - might be redundant
    while len(filter(lambda x: len(x) != 0, duplicates.values())) != 0:
        for name in sorter_labels:
            out_file_path = os.path.join(out_dir, f'{name}_labels.txt')
            check_file_path(out_file_path, extension='.txt')
            with open(out_file_path, 'r') as fptr:
                file_list = fptr.readlines()
            check_if_double_sorted(files_reviewed, file_list)
            duplicates[name] = get_all_duplicates(file_list)
            files_reviewed = [*files_reviewed, *file_list]
        remove_duplicate_files_txt(duplicates, out_dir)
    return files_reviewed

# get a flat list of all sorted files while removing duplicates and finding double sorted files
def get_all_reviewed_files_json(out_file_path: str) -> List[str]:
    check_file_path(out_file_path, extension='.json')
    remove_duplicate_files_json(out_file_path)
    files_reviewed = []
    with open(out_file_path, 'r') as fptr:
        out_dict = dict(json.load(fptr))
    for key in out_dict.keys():
        file_list = list(out_dict[key].values())
        check_if_double_sorted(files_reviewed, file_list)
        files_reviewed = [*files_reviewed, *file_list]
    return files_reviewed


def aggregate_txt2json(input_file_dict: Dict[str, str], out_file_path: str):
    ''' Reads several .txt files given in input_file_list
        Args:
            input_file_dict: dictionary with intended json labels as keys and full input file paths as values
            out_file_path: path including the name of the output json
    '''
    out_dir = os.path.dirname(out_file_path)
    _, output_ext = os.path.splitext(out_file_path)
    if output_ext != '.json':
        raise ValueError("out_file_path must include the json file's name including '.json'")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    out_dict = {}
    if os.path.exists(out_file_path):
        with open(out_file_path, 'r') as fptr:
            out_dict = json.load(fptr)
    for label, file_path in input_file_dict.items():
        with open(file_path, 'r') as fptr:
            out_dict[label] = sorted(remove_newlines(fptr.readlines()))
    with open(out_file_path, 'w') as json_ptr:
        json.dump(out_dict, json_ptr, indent=4)