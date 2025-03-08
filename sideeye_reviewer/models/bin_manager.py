import os
import json
from collections import deque
from typing import Dict, List, Deque, Optional, Union


# might rename to something like "SorterModel" later
class BinManager:
    """ A unified bin manager that can handle both single-label and multi-label reviewing.
        Each time a file is sorted (or undone), we record that in sort_history so that 'undo' works the same way for single or multiple labels.
    """
    def __init__(self, labels: List[str], out_dir: str, outfile_name: str):
        """
            :param labels: list of possible label/bin names
            :param out_dir: where to write the output JSON
            :param outfile_name: name of the output JSON
        """
        self.out_dir = out_dir
        self.json_out_path = os.path.join(out_dir, outfile_name)
        os.makedirs(self.out_dir, exist_ok=True)
        # could just use self.sorting_dict.keys(), but this is more explicit
        self.labels = labels
        self.current_image = None
        # for each label in the dict, keep a deque of filenames
        self.sorting_dict: Dict[str, Deque[str]] = {}
        for lbl in labels:
            self.sorting_dict[lbl] = deque()
        # each history entry is {filename: [labels]} so undo ops are straightforward
        self.sort_history: Deque[Dict[str, List[str]]] = deque()
        self.json_contents: Dict[str, List[str]] = {}

    def update_bin(self, labels, remove=False):
        """ For single-label usage, 'labels' will be a string. For multi-label usage, 'labels' will typically be a list of strings.
            We unify them internally in BinManager.
        """
        if remove:
            self.undo_sort()
        else:
            self.add_filename(labels, self.current_image)

    def set_current_image(self, img_name: str):
        # might want to add this to the reviewer classes instead
        self.current_image = img_name

    def add_filename(self, labels: Union[str, List[str]], filename: str):
        """ Adds a filename to one or more bins
            :param labels: either a single string label or a list of labels
            :param filename: the image filename
        """
        if isinstance(labels, str):
            labels = [labels]
        # put the filename into each of the requested bins
        for lbl in labels:
            if lbl not in self.sorting_dict:
                raise ValueError(f"No bin with label '{lbl}' found.")
            if filename not in self.sorting_dict[lbl]:
                self.sorting_dict[lbl].append(filename)
        self.sort_history.append({filename: labels})
        print(f"[SORTER] Added {filename} to bins {labels}")

    def undo_sort(self):
        """ Undo the last sort action by removing the file from the relevant bins """
        # TODO: might want to make this a warning animation just like clicking "NEXT" without checks in the multilabel view
        if not self.sort_history:
            print("sort_history is empty; cannot undo.")
            return
        last_entry = self.sort_history.pop()
        # last_entry should be a dict like {"my_image.jpg": ["disagree", "misaligned"]}
        for filename, label_list in last_entry.items():
            for lbl in label_list:
                if filename in self.sorting_dict[lbl]:
                    self.sorting_dict[lbl].remove(filename)
            print(f"[SORTER] Removed {filename} from bins {label_list}")

    def get_num_sorted(self) -> int:
        """ Returns how many unique filenames have been sorted so far, based on merging contents of self.json_out_path and contents added in this session """
        if not os.path.exists(self.json_out_path):
            return 0
        with open(self.json_out_path, 'r') as f:
            self.json_contents = dict(json.load(f))
        # make one set of all filenames that appear in any bin
        all_fnames = set()
        for fn_list in self.json_contents.values():
            all_fnames.update(fn_list)
        return len(all_fnames)

    def write_to_outfiles(self):
        """ Writes the final results to JSON. Preserves any old results from self.json_out_path and merges them with the newly sorted results """
        # convert our current sorting_dict to a normal dict of lists
        output_dict = {lbl: list(deq) for lbl, deq in self.sorting_dict.items()}
        # merge anything we already had in self.json_contents
        for lbl, fn_list in self.json_contents.items():
            if lbl not in output_dict:
                output_dict[lbl] = []
            output_dict[lbl].extend(fn_list)
            output_dict[lbl] = sorted(set(output_dict[lbl]))
        with open(self.json_out_path, 'w') as f:
            json.dump(output_dict, f, indent=4)
        print(f"[SORTER] Wrote updated bins to {self.json_out_path}")
