import csv

import keras
import matplotlib.pyplot as plt
import numpy as np
from keras import backend as K
from keras.layers import Conv2D, MaxPooling2D
from keras.layers import Dense, Flatten, Dropout
from keras.models import Sequential
from sklearn.metrics import roc_curve, precision_recall_curve, auc
from sklearn.model_selection import train_test_split

import image


def read_samples(file_name):
    """
    Reads samples from a CSV file excluding any rows where the values in the third and fourth column are both 0.
    
    Args:
    file_name (str): The name of the CSV file to read samples from.
    
    Returns:
    list: A list of samples excluding any incomplete rows.
    """
    import csv

    samples = []
    with open(file_name, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)
        for row in reader:
            row[1] = int(row[1])

            if row[2] == 0.0 and row[3] == 0.0:
                next(reader)

            samples.append(row)

    a, b = divmod(len(samples), 50)

    return samples[0:len(samples) - b]


def train_data():
    """
    Reads training samples from a file and returns them.

    This method reads training samples from a CSV file containing bad samples for the current model.
    
    Returns:
    List: A list of bad samples read from the file.
    """
    bad_samples_file = "samples/current_model/train_samples.csv"
    bad_samples = read_samples(bad_samples_file)

    return bad_samples


def test_data():
    """
    Reads the test samples from the specified CSV file and returns them.

    Returns:
    list: A list of test samples read from the CSV file.
    """
    valid_samples_file = "samples/current_model/test_samples.csv"
    samples = read_samples(valid_samples_file)

    return samples


def split_data(samples, test_size):
    """
    Splits the given samples into training and testing sets based on the specified test size.
    
    Parameters:
    samples (array-like): The samples to be split into training and testing sets.
    test_size (float): The proportion of samples to include in the testing set.
    
    Returns:
    tuple: A tuple containing the training set and testing set.
    """
    train, test = train_test_split(samples, test_size=test_size)

    return train, test


def data_generator(samples, batch_size):
    """
    Generator function that yields batches of data for training a neural network.

    Args:
    samples (list): List of tuples where each tuple contains the file name and label of an image.
    batch_size (int): Number of samples per batch.

    Yields:
    tuple: A tuple containing a batch of input data (x) and corresponding labels (y).
    """
    while 1:
        for sample_index in range(0, len(samples), batch_size):
            x = np.zeros((batch_size, 100, 100, 1), dtype=np.float32)
            y = np.zeros((batch_size,))
            for index in range(sample_index, sample_index + batch_size):
                file_name = samples[index][0]
                square = image.load_square_from_file(file_name)
                expanded = np.expand_dims(square, axis=2)
                x[index - sample_index] = expanded
                y[index - sample_index] = samples[index][1]
            yield (x, y)


def init_model():
    """
    Initializes and compiles a convolutional neural network model for binary classification.

    Returns:
    model: Initialized and compiled convolutional neural network model.

    """
    input_shape = (100, 100, 1)
    model = Sequential()
    model.add(Conv2D(32, kernel_size=(5, 5), strides=(1, 1),
                     activation='relu',
                     input_shape=input_shape))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
    model.add(Conv2D(64, (5, 5), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Flatten())
    model.add(Dense(1000, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(1, activation='sigmoid'))

    model.compile(loss='binary_crossentropy',
                  optimizer=keras.optimizers.Adam(),
                  metrics=['accuracy'])

    return model


class AccuracyHistory(keras.callbacks.Callback):
        def on_train_begin(self, logs={}):
        """
        Method called at the beginning of training.
    
        This method initializes an empty list to store the accuracy values during training.
    
        Parameters:
        logs (dict): Dictionary containing the training metrics.
    
        Returns:
        None
        """
        self.acc = []

        def on_epoch_end(self, batch, logs={}):
        """
        This method is called at the end of each epoch during training. It appends the accuracy metric 
        value from the 'logs' dictionary to the 'acc' list in the class instance.
        
        Parameters:
        batch (int): The batch number of the current epoch.
        logs (dict): A dictionary containing the training metrics at the end of the epoch.
        
        Returns:
        None
        """
        self.acc.append(logs.get('acc'))


def generate_results(y_test, y_score):
    """
    Generate and plot ROC and Precision-Recall curves to evaluate classification results on the test set.
    
    Parameters:
    y_test (array-like): True labels of the test set.
    y_score (array-like): Predicted scores for the test set.
    
    Returns:
    roc_auc (float): Area under the ROC curve.
    pr_auc (float): Area under the Precision-Recall curve.
    """
    fpr, tpr, _ = roc_curve(y_test, y_score)
    roc_auc = auc(fpr, tpr)

    plt.figure()
    plt.plot(fpr, tpr)
    plt.plot([0, 1], [0, 1], 'k--', label='test')
    plt.xlim([0.0, 1.05])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Classification results on train set, AUC = (%0.2f)' % roc_auc)
    print('AUC: %f' % roc_auc)

    plt.show()

    pr, rc, _ = precision_recall_curve(y_test, y_score)
    pr_auc = auc(rc, pr)

    print('AUC: %f' % pr_auc)

    # plt.show()

    return roc_auc, pr_auc


def calc_batch_size(batch_len, min_size, max_size):
    """
    Calculates the optimal batch size for a given batch length within a specified range of minimum and maximum sizes.
    
    Parameters:
    batch_len (int): The length of the batch
    min_size (int): The minimum batch size to consider
    max_size (int): The maximum batch size to consider
    
    Returns:
    int: The optimal batch size that evenly divides the batch length within the specified range
    """
    for size in range(min_size, max_size):
        a, b = divmod(batch_len, size)
        if b == 0:
            return size


"""
This method runs a metrics experiment using a dataset from a CSV file. It splits the data into training and testing sets, trains a model, evaluates the model on the testing set, and calculates ROC and precision-recall metrics over different test set sizes. It then plots the results using matplotlib.

Returns:
    None
"""
def run_metrics_experiment():
    r = read_samples("samples/rest_bad_samples.csv")
    roc = np.zeros((19, 3), dtype=np.float32)
    pr = np.zeros((19, 3), dtype=np.float32)
    t_size = []
    idx = 0
    for test_size in np.arange(0.05, 1, 0.05):
        size = round(test_size, 2)
        train, test = split_data(r, size)
        print("test_part: " + str(size) + " train_size: " + str(len(train)) + " test_size: " + str(len(test)))

        history = AccuracyHistory()
        train_middle = int(len(train) / 50)
        test_middle = int(len(test) / 25)
        train_batch_size = calc_batch_size(len(train), int(train_middle - 0.5 * train_middle),
                                           int(train_middle + 0.5 * train_middle))
        test_batch_size = calc_batch_size(len(test), int(test_middle - 0.5 * test_middle),
                                          int(test_middle + 0.5 * test_middle))
        epochs = 5
        print(train_batch_size)
        print(test_batch_size)
        roc_tmp = []
        pr_tmp = []
        for _ in range(5):
            K.clear_session()
            model = init_model()
            model.fit_generator(data_generator(train, train_batch_size),
                                steps_per_epoch=train_batch_size,
                                callbacks=[history],
                                epochs=epochs)

            scores = model.predict_generator(data_generator(test, test_batch_size),
                                             steps=int(len(test) / test_batch_size))
            print(scores)
            real = np.zeros((len(test),), dtype=np.float32)
            for i in range(0, len(test)):
                real[i] = test[i][1]

            roc_auc, pr_auc = generate_results(real, scores)
            roc_tmp.append(roc_auc)
            pr_tmp.append(pr_auc)

        roc[idx][0] = np.average(roc_tmp)
        roc[idx][1] = np.min(roc_tmp)
        roc[idx][2] = np.max(roc_tmp)
        pr[idx][0] = np.average(pr_tmp)
        pr[idx][1] = np.min(pr_tmp)
        pr[idx][2] = np.max(pr_tmp)

        t_size.append(test_size)
        idx += 1

    plt.plot(t_size, roc[:, 0])
    plt.fill_between(t_size, roc[:, 1], roc[:, 2], alpha=0.3)
    plt.plot(t_size, pr[:, 0])
    plt.fill_between(t_size, pr[:, 1], pr[:, 2], alpha=0.5)
    plt.xlim([0.0, 1.05])
    plt.ylim([0.0, 1.05])
    plt.xlabel("test_part_size")
    plt.ylabel("AUC")
    plt.show()


def run_default_model():
    """
    Runs a default model training process using train and test data, generating predictions and evaluating results.

    The method initializes train and test data, creates an AccuracyHistory callback, sets batch sizes,
    initializes a model, fits the model, saves the model, generates predictions on test data,
    extracts true labels from the test data, and finally generates and prints the results.

    Parameters:
    None

    Returns:
    None
    """
    train = train_data()
    test = test_data()
    history = AccuracyHistory()
    train_batch_size = int(len(train) / 50)
    test_batch_size = int(len(test) / 25)

    print(train_batch_size)
    print(test_batch_size)
    epochs = 10

    model = init_model()

    model.fit_generator(data_generator(train, train_batch_size),
                        steps_per_epoch=train_batch_size,
                        callbacks=[history],
                        epochs=3)

    model.save("samples/current_model/model.h5")

    # model = load_model("samples/model.h5")
    scores = model.predict_generator(data_generator(test, test_batch_size), steps=25)
    print(scores)
    real = np.zeros((len(test),), dtype=np.float32)
    for i in range(0, len(test)):
        real[i] = test[i][1]

    print(scores)

    generate_results(real, scores)


# run_metrics_experiment()
# run_default_model()
# import pydot
# print (pydot.find_graphviz())

from keras.utils import plot_model

model = init_model()
plot_model(model, to_file='model_arch.png', show_shapes=True)
