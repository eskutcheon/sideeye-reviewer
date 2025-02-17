import os, sys, json
import re
from copy import deepcopy
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


SOILED_TRAIN_DIR = os.path.join('data', 'soiling_dataset', 'train')


def get_num_from_filename(filename):
    return re.findall(r'\d{4}', filename)

def get_digit_list(file_list):
    return [int(''.join(get_num_from_filename(filename))) for filename in file_list]

def get_cam_from_filename(filename):
    return re.search(r'_(.+?)\.png$', filename).group(1)

def check_cam_consistency(file_list, cluster_label):
    cam_labels = [str(get_cam_from_filename(filename)) for filename in file_list]
    if len(set(cam_labels)) != 1:
        print(f"ERROR: found different cam from the rest of the cluster for {cluster_label}:\n\t{cam_labels}")

def check_large_deviation(sorted_digits):
    threshold = 5  # Set this to a value based on what you consider to be "very far"
    for i in range(1, len(sorted_digits)):
        if sorted_digits[i] - sorted_digits[i-1] > threshold:
            return True, (sorted_digits[i-1], sorted_digits[i])
    return False, None

# just trying to find where it might have made mistakes besides just the background class
with open(os.path.join(SOILED_TRAIN_DIR, '..', "cluster_membership.json"), 'r') as fptr:
    cluster_dict = dict(json.load(fptr))
cluster_dict_copy = deepcopy(cluster_dict)

background_list = cluster_dict["-1"]
for label, file_list in cluster_dict.items():
    if label == "-1":
        continue
    check_cam_consistency(file_list, label)
    # get numbers from filenames and see if anything is missing
    digit_list = get_digit_list(file_list)
    digit_list.sort()
    deviation, deviant_pair = check_large_deviation(digit_list)
    if deviation:
        print(f"ERROR: large deviation found in cluster {label} between {deviant_pair[0]} and {deviant_pair[1]}.")
    for i in range(len(digit_list) - 1):
        if digit_list[i + 1] - digit_list[i] > 1:
            missing_num = digit_list[i] + 1
            print(f"MISSING FILE CORRESPONDING TO {missing_num} in cluster {label}.")