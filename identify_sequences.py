# Code adapted from https://towardsdatascience.com/how-to-cluster-images-based-on-visual-similarity-cd6e7209fe34

import os, sys, json
# uncomment this later if I add these scripts to subfolders again
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# for loading/processing the images
from skimage.io import imread
import torch
import torchvision.models as models
import torchvision.io as IO
# clustering and dimension reduction
from sklearn.cluster import KMeans, DBSCAN, HDBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
# for everything else
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from tqdm import tqdm
from typing import Dict, Union, List



# TODO: decide whether I want to keep any of this to still sort similar images into clusters to simplify annotation


SOILED_TRAIN_DIR = os.path.join('data', 'soiling_dataset', 'train')
SOILED_TEST_DIR = os.path.join('data', 'soiling_dataset', 'test')
SOILED_PATH_DICT = {
    'train': {
        'img': os.path.join(SOILED_TRAIN_DIR, 'rgbImages'),
        # NOTE: don't actually need to save any new masks - so I'm passing the gtLabels for faster computation of inpainting
        'label': os.path.join(SOILED_TRAIN_DIR, 'gtLabels'),
        'mask': os.path.join(SOILED_TRAIN_DIR, 'rgbLabels'),
        'overlay': os.path.join(SOILED_TRAIN_DIR, 'rgbOverlays')},
    'test': {
        'img': os.path.join(SOILED_TEST_DIR, 'rgbImages'),
        'label': os.path.join(SOILED_TEST_DIR, 'gtLabels'),
        'mask': os.path.join(SOILED_TEST_DIR, 'rgbLabels'),
        'overlay': os.path.join(SOILED_TEST_DIR, 'rgbOverlays')}}


def extract_features(file_path: str, model: models.vgg16) -> torch.tensor:
    # load the image as a 224x224 array
    img_tensor = IO.read_image(file_path, IO.ImageReadMode.RGB).unsqueeze(0).to(dtype=torch.float32, device='cuda:0')
    #print(img_tensor.shape)
    #img = imread(file_path)
    #img_tensor = img_util.ndarray_to_tensor(img).unsqueeze(0).to(dtype=torch.float32)
    '''img_tensor /= 255
    resize_func = transforms.Resize((224,224), interpolation=transforms.InterpolationMode.BILINEAR, antialias=True)
    img_tensor = resize_func(img_tensor)
    #img_tensor = img_tensor.reshape((1,3,224,224))
    #print(f"img_tensor shape: {img_tensor.shape}")
    normalize_func = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    #print(f"initial img details: \n\tshape: {img.shape}\n\tdtype: {img.dtype}\n\tvalues: {np.unique(img)}\n")
    img_tensor = normalize_func(img_tensor)'''
    #print(f"processed img details: \n\tshape: {img_tensor.shape}\n\tdtype: {img_tensor.dtype}\n\tvalues: {torch.unique(img_tensor)}\n")
    with torch.no_grad():
        features = model(img_tensor)
        #print(f"features extracted: \n{features}")
    return features.squeeze(0)

def save_all_features(data: Dict[str, torch.tensor], model: models.vgg16, pkl_path: str):
    # loop through each image in the dataset
    data["features"] = {}
    with tqdm(total=len(data["files"]), desc="Extracting features from all files...") as tracker:
        for mask_path in data["files"]:
            # try to extract the features and update the dictionary
            #try:
            data["features"][os.path.basename(mask_path)] = extract_features(mask_path, model).to(device="cpu")
            #print(f"Successfully saved features for {mask_path}")
            # if something fails, save the extracted features as a pickle file (optional)
            '''except:
                #print(f"WARNING: failed to save features for {mask_path}")
                with open(pkl_path,'wb') as file:
                    pickle.dump(data, file)'''
            tracker.update()

def get_feature_vectors(data: Dict[str, torch.tensor]):
    # get a list of the filenames
    filenames: np.ndarray = np.array(list(data.keys()))
    #print(data.values())
    # get a list of just the features
    feature_values = list(data["features"].values())
    #print(f"TEST feature_values SHAPE: {len(feature_values), feature_values[0].shape}")
    num_samples: int = len(feature_values)
    num_features: int = len(feature_values[0])
    feat: torch.tensor = torch.zeros((num_samples, *feature_values[0].shape))
    #print(f"TEST FEATURE VECTORS SHAPE: {feat.shape}")
    for i in range(num_samples):
        feat[i] = feature_values[i]
    # reshape so that there are 210 samples of 4096 vectors
    # SHOULD STILL WORK AS IT DID WITH ndarray
    feat = feat.reshape(-1,num_features)
    '''# get the unique labels (from the flower_labels.csv)
    df = pd.read_csv('flower_labels.csv')
    label = df['label'].tolist()
    unique_labels = list(set(label))'''
    # reduce the amount of dimensions in the feature vector
    pca = PCA(n_components=100, random_state=22)
    feat_np = feat.numpy()
    pca.fit(feat_np)
    x = pca.transform(feat_np)
    data["reduced_features"] = {}
    for idx, filename in enumerate(data["files"]):
        data["reduced_features"][os.path.basename(filename)] = x[idx]
    return x

def cluster_feature_vectors(X, filenames):
    #kmeans = KMeans(n_clusters=len(unique_labels),n_jobs=-1, random_state=22)
    #kmeans = KMeans(n_clusters=15, random_state=22)
    #kmeans.fit(X)
    dbscan_obj = HDBSCAN(min_cluster_size=6, max_cluster_size=13, n_jobs=-1)
    dbscan_obj.fit(X)
    # holds the cluster id and the images { id: [images] }
    groups = {int(cluster): [] for cluster in dbscan_obj.labels_}
    for file, cluster in zip(filenames, dbscan_obj.labels_):
        if cluster not in groups.keys():
            groups[cluster] = []
        groups[cluster].append(os.path.basename(file))
    return groups

# function that lets you view a cluster (based on identifier)
def view_cluster(cluster, groups):
    plt.figure(figsize = (25,25));
    # gets the list of filenames for a cluster
    files = groups[cluster]
    # only allow up to 30 images to be shown at a time
    if len(files) > 30:
        print(f"Clipping cluster size from {len(files)} to 30")
        files = files[:30]
    # plot each image in the cluster
    for index, file in enumerate(files):
        plt.subplot(10,10,index+1)
        img = imread(file)
        img = np.array(img)
        plt.imshow(img)
        plt.axis('off')


# this is just incase you want to see which value for k might be the best
def get_best_k(X):
    # pretty sure I have a better function for this in some old code from Dr. Kim's class
    sse = []
    list_k = list(range(3, 50))
    for k in list_k:
        km = KMeans(n_clusters=k, random_state=22, n_jobs=-1)
        km.fit(X)
        sse.append(km.inertia_)
    # Plot sse against k
    plt.figure(figsize=(6, 6))
    plt.plot(list_k, sse)
    plt.xlabel(r'Number of clusters *k*')
    plt.ylabel('Sum of squared distance');


def sort_remaining_files(clusters, data):
    with tqdm(total = len(clusters[-1]), desc="sorting remaining unclustered files") as pbar:
        for idx, unclustered in enumerate(clusters[-1]):
            mean_distance = np.zeros(len(clusters) - 1)
            for label, file_list in clusters.items():
                if label == -1:
                    continue
                feature_norms = np.zeros(len(file_list), dtype=np.double)
                for i, file in enumerate(file_list):
                    feature_norms[i] = np.linalg.norm(data["reduced_features"][file] - data["reduced_features"][unclustered], ord=2)
                mean_distance[label] = np.mean(feature_norms)
            min_label = np.argmin(mean_distance)
            clusters[min_label].append(unclustered)
            pbar.update()

def ensure_adjacent_filenames_in_cluster(clusters: Dict[int, List[str]], feature_vectors: Dict[str, np.ndarray]) -> Dict[int, List[str]]:
    def get_mean_vector(cluster: List[str]) -> np.ndarray:
        vectors = [feature_vectors[filename] for filename in cluster]
        return np.mean(vectors, axis=0)
    new_clusters = {}
    orphan_files = deque()
    cluster_label = 0
    for label, filenames in clusters.items():
        if label == -1:  # skip the unclustered group
            continue
        filenames = sorted(filenames, key=lambda x: int(x.split('_')[0]))
        to_add = [filenames[0]]
        for idx in range(1, len(filenames)):
            if int(filenames[idx].split('_')[0]) - int(filenames[idx-1].split('_')[0]) == 1 and len(to_add) <= 13:
                to_add.append(filenames[idx])
            else:
                if len(to_add) >= 6:
                    new_clusters[cluster_label] = to_add
                    cluster_label += 1
                else:
                    orphan_files.extend(to_add)
                to_add = [filenames[idx]]
        if to_add:
            if len(to_add) >= 6:
                new_clusters[cluster_label] = to_add
                cluster_label += 1
            else:
                orphan_files.extend(to_add)
    # Handle orphan_files using cosine similarity to feature vectors
    with tqdm(total=len(orphan_files), desc="handling orphaned files") as pbar:
        while orphan_files:
            orphan = orphan_files.popleft()
            best_cluster = None
            best_similarity = -1
            orphan_vector = feature_vectors[orphan]
            for key, value in new_clusters.items():
                if 6 <= len(value) <= 13:
                    mean_vector = get_mean_vector(value)
                    similarity = cosine_similarity([orphan_vector], [mean_vector])[0][0]
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_cluster = key
            if best_cluster is not None:
                new_clusters[best_cluster].append(orphan)
            else:
                # If no appropriate cluster found, form a new one
                new_clusters[cluster_label] = [orphan]
                cluster_label += 1
            pbar.update()
    return new_clusters

if __name__ == "__main__":
    # this list holds all the image file paths
    mask_paths = []
    for mode, dir_dict in SOILED_PATH_DICT.items():
        # creates a ScandirIterator aliased as files
        with os.scandir(dir_dict['mask']) as files:
        # loops through each file in the directory
            mask_paths.extend([os.path.join(dir_dict['mask'], file.name) for file in files])
    model = models.vgg16(weights="DEFAULT").to(device='cuda:0')
    model.eval()  # Set the model to evaluation mode
    '''
    For VGG16 trained on ImageNet, the mean and standard deviation values are commonly:
        mean = [0.485, 0.456, 0.406]
        std = [0.229, 0.224, 0.225]
    '''
    mask_paths = sorted(mask_paths, key=os.path.basename)
    data: Dict[str, torch.tensor] = {"files": mask_paths}
    p = os.path.join(os.path.join(SOILED_TRAIN_DIR, '..'), 'feature_vectors.pkl')
    save_all_features(data, model, p)
    X = get_feature_vectors(data)
    #print(data)
    print(f"SHAPE OF X: {X.shape}")
    #clusters = cluster_feature_vectors(X, np.array(list(data.values())))
    clusters = cluster_feature_vectors(X, mask_paths)
    sort_remaining_files(clusters, data)
    clusters[-1] = []
    clusters = dict(sorted(clusters.items()))
    with open(os.path.join(SOILED_TRAIN_DIR, '..', 'cluster_membership1.json'), 'w') as fptr:
        json.dump(clusters, fptr, indent=4)
    clusters = ensure_adjacent_filenames_in_cluster(clusters, data["reduced_features"])
    clusters = dict(sorted(clusters.items()))
    #print(clusters)
    with open(os.path.join(SOILED_TRAIN_DIR, '..', 'cluster_membership2.json'), 'w') as fptr:
        json.dump(clusters, fptr, indent=4)