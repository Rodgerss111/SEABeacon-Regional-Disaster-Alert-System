# key_file stores the name of the dataset package as a dictionary.
key_file = {
    'train_img':'train-images-idx3-ubyte.gz',
    'train_label':'train-labels-idx1-ubyte.gz',
    'test_img':'t10k-images-idx3-ubyte.gz',
    'test_label':'t10k-labels-idx1-ubyte.gz'
}

# The dataset_dir variable is used to obtain the absolute path of the folder where the current code file is located.
dataset_dir = os.path.dirname(os.path.abspath(__file__))

# save_file declares the path of the .pkl file through character string concatenation.
save_file = dataset_dir + "/mnist.pkl"

def load_mnist(normalize=True, flatten=True, one_hot_label=False):
    """Read the MNIST dataset.
    Parameters
    ----------
    normalize: normalizes the pixel value of the image to a value within the range from 0.0 to 1.0.
    one_hot_label : 
        When one_hot_label is set to True, the label is returned as a one-hot array.
        A one-hot array is similar to [0,0,1,0,0,0,0,0,0,0].
    flatten: indicates whether to expand the image into a one-dimensional array.
    
    Returns
    -------
    (training image, training label), (test image, test label)
"""
# Check whether the pickle file for storing the dataset exists. If the file does not exist, use the compressed dataset to create the file.
    if not os.path.exists(save_file):   
        init_mnist()
    # Use the pickle file to load the dataset. 
    with open(save_file, 'rb') as f:
        dataset = pickle.load(f)

    """Preprocess the dataset"""
    if normalize:
        for key in ('train_img', 'test_img'):
            dataset[key] = dataset[key].astype(np.float32) # Convert to the np.float32 data type.
            dataset[key] /= 255.0 # Convert the pixel value to a value within the range of 0 to 1.
            
    if one_hot_label:   # Convert the label to a one-hot array.
        dataset['train_label'] = _change_one_hot_label(dataset['train_label'])
        dataset['test_label'] = _change_one_hot_label(dataset['test_label'])
    
    if not flatten:   # Check whether the data needs to be flattened. If the data needs to be flattened, the (784,) format is retained. Otherwise, the data is converted into (28, 28).
         for key in ('train_img', 'test_img'):
            dataset[key] = dataset[key].reshape(-1, 1, 28, 28)

    return (dataset['train_img'], dataset['train_label']), (dataset['test_img'], dataset['test_label'])

def init_mnist():
    dataset = _convert_numpy () # Convert the dataset into the NumPy format.
    print("Creating pickle file ...") 
    with open(save_file, 'wb') as f:    # Open the .pkl file in binary writeable mode.
        pickle.dump (dataset, f, -1) # Write the dataset into the .pkl file. After the operation is complete, the file is automatically closed.
print("Done!")

def _convert_numpy():
    dataset = {} # Create an empty dictionary.
# Save the dataset in the dictionary by name.
    dataset['train_img'] =  _load_img(key_file['train_img'])
    dataset['train_label'] = _load_label(key_file['train_label'])    
    dataset['test_img'] = _load_img(key_file['test_img'])
dataset['test_label'] = _load_label(key_file['test_label'])

    return dataset

