import os
import sys
import json
from collections import Counter
from typing import Dict, List
from matplotlib import get_backend
import matplotlib.pyplot as plt


def maximize_window():
    manager = plt.get_current_fig_manager()
    backend = get_backend()
    if backend in ['TkAgg', 'tkagg']:
        if sys.platform.startswith('win'):  # windows
            manager.window.state('zoomed')
        else:  # for linux (not actually tested with any alternate OS yet)
            manager.window.wm_attributes('-zoomed', '1')
    elif backend in ["Qt5Agg", "qtagg"]:
        manager.window.showMaximized()
    elif backend == 'WXAgg':
        manager.window.Maximize()
    else:
        print(f"WARNING: Unsupported backend {backend} for maximize operation")


#& commented out for now since its job was taken over by the static method `AxesCreationManager.compute_button_positions`
    #~ The two approaches could both still be used and might benefit as helper functions called by an orchestrator function
# UPDATE: now returns button axes centered between right_bound and left_bound
# def compute_button_positions(     #? NOTE: formerly named `get_button_axes`
#     num_buttons: int,
#     # TODO: consider passing a Rect-like list of left, bottom, width, height for full button panel location instead
#     left_bound: float = 0.3,
#     right_bound: float = 0.95,
#     width: float = 0.1,
#     spacing: float = 0.01
# ) -> List[List[float]]:
#     total_width = (width + spacing) * num_buttons - spacing  # total width of all buttons including spacing
#     if total_width > right_bound - left_bound:  # if total width exceeds available space, scale down
#         scale = (right_bound - left_bound)/total_width
#         width *= scale
#         spacing *= scale
#         # dynamically reduce the total horizontal width for a larger number of buttons
#         total_width = (width + spacing) * num_buttons - spacing
#     # calculate additional padding needed to center buttons
#     padding = (right_bound - left_bound - total_width)/2
#     left_bound += padding  # update left_bound to center buttons
#     # TODO: add logic for variable button heights and eventually multiple rows of button axes
#     return [[left_bound + i*(width + spacing), 0.025, width, 0.075] for i in range(num_buttons)]


#& MIGHT REMOVE - currently not used anywhere but I'm nearly certain there may come a need eventually
# def get_user_confirmation(prompt):
#     answers = {'y': True, 'n': False}
#     response = input(f"{prompt} [Y/n]  ").lower()
#     while response not in answers:
#         print("Invalid input. Please enter 'y' or 'n' (not case sensitive).")
#         response = input(f"{prompt} [Y/n]  ").lower()
#     return answers[response]


#* file contents handling helper functions:

def _remove_newlines(file_list: List[str]) -> List[str]:
    return list(map(lambda x: x.rstrip('\n'), file_list))

def _get_all_duplicates(file_list: List[str]) -> List[str]:
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


#& MIGHT REMOVE - currently unused - also from the old project
def _remove_duplicate_files_json(out_file_path: str):
    check_file_path(out_file_path, extension='.json')
    out_dict = {}
    with open(out_file_path, 'r') as fptr:
        out_dict = dict(json.load(fptr))
        for key in out_dict.keys():
            out_dict[key] = sorted(list(set(out_dict[key])))
    with open(out_file_path, 'w') as fptr:
        json.dump(out_dict, fptr, indent=4)


#& MIGHT REMOVE - currently unused - also from the old project
# get a flat list of all sorted files while removing duplicates and finding double sorted files
def get_all_reviewed_files_json(out_file_path: str) -> List[str]:
    check_file_path(out_file_path, extension='.json')
    _remove_duplicate_files_json(out_file_path)
    files_reviewed = []
    with open(out_file_path, 'r') as fptr:
        out_dict = dict(json.load(fptr))
    for key in out_dict.keys():
        file_list = list(out_dict[key].values())
        check_if_double_sorted(files_reviewed, file_list)
        files_reviewed = [*files_reviewed, *file_list]
    return files_reviewed




