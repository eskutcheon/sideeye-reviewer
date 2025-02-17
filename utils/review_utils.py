import os, sys
import json
import matplotlib.pyplot as plt
from collections import Counter
from typing import Dict, List, Union, Tuple
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# project files
import core.image_reviewer as IR


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


def repeat_uncertain_labels_txt(img_source_dir: str, out_dir: str, sorter_labels: List[str]):
    with open(os.path.join(out_dir, f'uncertain_labels.txt'), 'r') as fptr:
        file_list = remove_newlines(fptr.readlines())
    if len(file_list) != 0:
        partial_repeat_review(img_source_dir, out_dir, sorter_labels, file_list)

def repeat_uncertain_labels_json(img_source_dir: str, out_file_path: str):
    check_file_path(out_file_path, extension='.json')
    out_dir = os.path.dirname(out_file_path)
    with open(out_file_path, 'r') as fptr:
        file_dict = dict(json.load(fptr))
    if len(file_dict['uncertain']) != 0:
        partial_repeat_review(img_source_dir, out_dir, list(file_dict.keys()), file_dict['uncertain'])


def repeat_skipped_labels(img_source_dir: str, out_dir: str, sorter_labels: List[str], file_sets: Dict[str, List[str]]):
    skipped_files = list(set(file_sets['superset']).difference(set(remove_newlines(file_sets['subset']))))
    if len(skipped_files) != 0:
        partial_repeat_review(img_source_dir, out_dir, sorter_labels, skipped_files)


def partial_repeat_review(img_source_dir: str, out_dir: str, sorter_labels: List[str], file_list: List[str]):
    # needs to be the abstracted method called early in post_processing
    run_reviewer(img_source_dir, out_dir, sorter_labels, file_list, False)
    post_review_cleanup(img_source_dir, out_dir, sorter_labels, file_list)


def run_reviewer(img_source_dir: str, out_dir: str, sorter_labels: List[str], example_dict: Dict[str, str], image_files=None, checkpoint=True):
    disputed_sorter = IR.ImageSorter([img_source_dir], out_dir, sorter_labels, image_files)
    # create dictionary of sorter labels as keys and full file paths as values for the example buttons
    Reviewer = IR.ImageReviewer(disputed_sorter, example_dict)
    Reviewer.begin_review(checkpoint)


def post_review_cleanup(img_source_dir: str, out_dir: str, sorter_labels: List[str]):
    # get a list of all files found between all the .txt files, delete duplicates and check for mistakes
    file_sets = {
        'superset': sorted(os.listdir(img_source_dir)),
        'subset': get_all_reviewed_files_txt(out_dir, sorter_labels)}
    repeat_skipped_labels(img_source_dir, out_dir, sorter_labels, file_sets)
    repeat_uncertain_labels_txt(img_source_dir, out_dir, sorter_labels)


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