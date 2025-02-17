import os, sys, json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import core.show_sort_results as Viewer


def show_new_masks(seg_dirs, title):
    # reading intended files to review from the json
    img_list = os.listdir(seg_dirs[1])
    sort_viewer = Viewer.SortResultsViewer(img_list, seg_dirs, title)

def show_sorted_results(seg_dirs, title):
    # reading intended files to review from the json
    json_path = os.path.join('..', 'other_sorting', 'early_sorting_results.json')
    with open(json_path, 'r') as fptr:
        sorted_dict = dict(json.load(fptr))
    sort_viewer = Viewer.SortResultsViewer(sorted(sorted_dict['disagree']), seg_dirs, title)


if __name__ == "__main__":
    # reading intended files to review from the json
    #output_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'disputed_labels', 'sorting_output.json')
    new_mask_dir = os.path.join("..", "soiling_dataset_new", "train", "rgbLabels")
    img_dirs = [os.path.join('data', 'soiling_dataset', 'train', 'rgbImages'),
                os.path.join('data', 'soiling_dataset', 'train', 'rgbLabels')]
    new_img_dirs = [img_dirs[0], new_mask_dir]
    show_sorted_results(img_dirs, "Disagreed Upon Masks")
    #show_new_masks(new_img_dirs, "Updated Masks with 5th Class")