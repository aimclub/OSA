import csv
import os
import re
from math import pow
from math import sqrt

import matplotlib.pyplot as plt
import numpy as np

import image as img


def magnitude(a, b):
    """
    Calculates the magnitude of a vector with components 'a' and 'b'.

    Args:
    a (float): The x-component of the vector.
    b (float): The y-component of the vector.

    Returns:
    float: The magnitude of the vector.

    Example:
    magnitude(3, 4) => 5.0
    """
    return sqrt(pow(a, 2.0) + pow(b, 2.0))


def calculate_velocity_magnitude_matrix(x, y):
    """
    Calculate the magnitude of velocity vectors from x and y components and store them in a matrix.

    Args:
    x (list of lists): Matrix of x components of velocity vectors
    y (list of lists): Matrix of y components of velocity vectors

    Returns:
    np.ndarray: Matrix containing the magnitude of velocity vectors corresponding to x and y components
    """
    mgn = np.zeros((len(x), len(x[0])), dtype=np.float32)

    for i in range(0, len(x)):
        for j in range(0, len(x[i])):
            mgn[i][j] = magnitude(x[i][j], y[i][j])

    return mgn


def press(event):
    """
    This function is called when a key is pressed during a plot. If the key pressed is 'y', it appends '1' to the bad_samples list and closes the plot. If the key pressed is 'n', it appends '0' to the bad_samples list and closes the plot.
    
    Parameters:
    event (Event): The key press event that triggers the function.
    
    Returns:
    None
    """
    if event.key == 'y':
        bad_samples.append('1')
        plt.close()

    elif event.key == 'n':
        bad_samples.append('0')
        plt.close()


def show_velocity_square(vel):
    """
    Displays a square image of velocity data with a colorbar. 
    Listens for key press events to trigger additional actions through the 'press' function.

    Parameters:
    vel (numpy array): 2D array representing velocity data to be displayed.

    Returns:
    None
    """
    plt.connect('key_press_event', press)
    plt.imshow(vel)
    plt.colorbar()
    plt.show()


def generate_squares_global():
    """
    This method generates squares from an image using the slice_uv_squares function from the Image class.
    
    Parameters:
    None
    
    Returns:
    None
    """
    img.slice_uv_squares("samples/data/")


def label_good_samples():
    """
    This method generates and labels good samples for training data. It creates velocity magnitude matrices for a specific amount of images, 
    splits them into squares, removes any nan-values, calculates the velocity magnitude, saves it to a file, and labels it as '0' in the CSV file.
    The CSV file contains the file name of the velocity magnitude matrix and its corresponding label.
    """
    file_name = "samples/good_samples.csv"
    with open(file_name, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['file, label'])

        images_amount = 30
        vel_dir = "samples/good/"
        if not os.path.exists(vel_dir):
            os.makedirs(vel_dir)

        for image_index in range(0, images_amount):
            square_index = 1
            for x in range(0, 1100, 100):
                for y in range(0, 400, 100):
                    u_file_name = "samples/out/rea" + str(image_index) + "_u_" + str(x) + "_" + str(y)
                    v_file_name = "samples/out/rea" + str(image_index) + "_v_" + str(x) + "_" + str(y)
                    u = img.load_square_from_file(u_file_name)
                    v = img.load_square_from_file(v_file_name)
                    # remove nan-values
                    u[u < -30000.0] = 0.0
                    v[v < -30000.0] = 0.0
                    vel = calculate_velocity_magnitude_matrix(u, v)
                    velocity_file_name = vel_dir + "rea" + str(image_index) + "_" + str(x) + "_" + str(y)
                    img.save_square_to_file(vel, velocity_file_name)

                    writer.writerow([velocity_file_name, '0'])
                    print("squares: " + str(square_index) + "/44 done")
                    square_index += 1
            print("images: " + str(image_index + 1) + "/" + str(images_amount) + " done")


bad_samples = []


def label_bad_samples():
    """
    This method labels the bad samples by calculating the velocity magnitude matrix for each sample, displaying the velocity square, and saving the velocity matrix to a file. The labeled samples are then written to a CSV file with the file name and corresponding label. 
    """
    file_name = "samples/bad_samples.csv"
    with open(file_name, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['file, label'])

        vel_dir = "samples/bad/vel/"
        if not os.path.exists(vel_dir):
            os.makedirs(vel_dir)

        for file_name in os.listdir("samples/bad"):
            arctic_file = file_name.split(".")[0]
            for x in range(0, 1100, 100):
                for y in range(0, 400, 100):
                    u_file_name = "samples/bad/" + arctic_file + "_vozocrtx_" + str(x) + "_" + str(y)
                    v_file_name = "samples/bad/" + arctic_file + "_vomecrty_" + str(x) + "_" + str(y)
                    u = img.load_square_from_file(u_file_name)
                    v = img.load_square_from_file(v_file_name)
                    u[u < -30000.0] = 0.0
                    v[v < -30000.0] = 0.0
                    vel = calculate_velocity_magnitude_matrix(u, v)

                    show_velocity_square(vel)

                    velocity_file_name = vel_dir + arctic_file + "_" + str(x) + "_" + str(y)
                    img.save_square_to_file(vel, velocity_file_name)
                    result = bad_samples[len(bad_samples) - 1]
                    writer.writerow([velocity_file_name, result])


def add_characteristics_of_samples(dataset_file_name):
    """
    Reads a dataset from a CSV file, loads each sample's image square, and appends the minimum, maximum, and average 
    values of the samples to each row. It then writes the updated dataset back to the same CSV file.

    :param dataset_file_name: The name of the CSV file containing the dataset
    """
    rows = []
    with open(dataset_file_name, 'r', newline='') as old_csv_file:
        reader = csv.reader(old_csv_file, delimiter=',')
        for row in reader:
            rows.append(row)

    # Add min && max && average values of samples
    for row in rows:
        square = img.load_square_from_file(row[0])
        row.append(np.min(square))
        row.append(np.max(square))
        row.append(np.average(square))
    with open(dataset_file_name, 'w', newline='') as new_csv_file:
        writer = csv.writer(new_csv_file, delimiter=',')
        for row in rows:
            writer.writerow(row)


This method reads a dataset file containing image paths, loads each image, extracts a square matrix from the image, and then calculates the minimum and maximum values within the square matrix. It returns the minimum and maximum values found in the dataset.

Parameters:
dataset_file_name (str): The name of the dataset file containing image paths.

Returns:
tuple: A tuple containing the minimum and maximum values found in the dataset.


def show_hist_samples_distribution(dataset_file_name):
    """
    This function reads a dataset file containing velocity data, calculates the average velocity
    distribution, and displays it as a histogram using matplotlib. It reads the dataset file,
    extracts the average velocity values, calculates the histogram with 500 bins, and displays
    the distribution plot.

    :param dataset_file_name: The file name of the dataset containing velocity data
    """
    plt.style.use('seaborn-white')

    average_vel = []
    min_vel = []
    max_vel = []
    with open(dataset_file_name, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            min_vel.append(np.float(row[2]))
            max_vel.append(np.float(row[3]))
            average_vel.append(np.float(row[4]))

    bins = np.linspace(min(average_vel), max(average_vel), num=500)
    counts = np.zeros_like(bins)
    i = np.searchsorted(bins, average_vel)
    np.add.at(counts, i, 1)

    plt.title("Average velocity distribution")
    plt.hist(average_vel, bins, histtype='stepfilled', normed=True)
    plt.show()


def extend_datasets():
    """
    This method extends the datasets by adding characteristics of samples from different CSV files:
    - "samples/good_samples.csv"
    - "samples/bad_samples.csv"
    - "samples/rest_bad_samples.csv"
    - "samples/valid_samples.csv"
    """
    add_characteristics_of_samples("samples/good_samples.csv")
    add_characteristics_of_samples("samples/bad_samples.csv")
    add_characteristics_of_samples("samples/rest_bad_samples.csv")
    add_characteristics_of_samples("samples/valid_samples.csv")


def extract_square_index(square_name):
    """
    Extracts the index of a square from its name. The index is defined as digits separated by underscores.
    
    Args:
    square_name (str): The name of the square containing the index.
    
    Returns:
    str: The extracted index of the square.
    """
    try:
        found = re.search('_\d*_\d*', square_name).group(0)[1:]
    except AttributeError:
        found = ''

    return found


def group_squares(reader):
    """
    Groups rows from a reader based on the square index extracted from the first element of each row.
    
    Args:
    reader (list): A list of rows to be grouped
    
    Returns:
    list: A list of grouped rows based on the square index
    """
    groups, dic_name = [], {}
    for row in reader:
        square_index = extract_square_index(row[0])
        if square_index in dic_name:
            groups[dic_name[square_index]].extend([row])
        else:
            groups.append([row])
            dic_name[square_index] = len(dic_name)

    return groups


def show_average_vel_by_squares(dataset_file_name):
    """
    Reads a dataset from a file and calculates the average velocity of squares in each group. 
    Displays the average velocity as an image using matplotlib.

    Parameters:
    dataset_file_name (str): The name of the dataset file to be read.

    Returns:
    None
    """
    with open(dataset_file_name, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        groups = group_squares(reader)
        for index in range(0, len(groups)):
            squares_vel = np.zeros((len(groups[index]), 100, 100), dtype=float)
            for sample_index in range(0, len(groups[index])):
                square = img.load_square_from_file(groups[index][sample_index][0])
                squares_vel[sample_index] = square
            average_vel = np.average(squares_vel, axis=0)
            print(average_vel)
            plt.imshow(average_vel)
            plt.colorbar()
            plt.show()


def show_distribution_by_classes(dataset_file_name):
    """
    Reads a dataset file containing class labels and displays the distribution of instances per class.

    Args:
    dataset_file_name (str): The name of the dataset file to be read.

    Returns:
    None
    """
    with open(dataset_file_name, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        classes = {}
        for row in reader:
            label = int(row[1])
            if label in classes:
                classes[label] += 1
            else:
                classes[label] = 0
        print(classes)


def count_outlier_squares(dataset_file_name):
    """
    Opens a dataset file, reads the data row by row, extracts the square index and checks if it is an outlier square.
    If the square is an outlier square (i.e., row[1] is "1"), it counts the occurrences of the square index and identifies the maximum value of the square "100_0".
    It also displays the outlier square along with some visualization features.
    
    Parameters:
    dataset_file_name (str): The name of the dataset file to be opened and processed.
    """
    with open(dataset_file_name, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        square_by_count = {}
        max_900_0 = 0.0
        for row in reader:
            idx = extract_square_index(row[0])
            if row[1] == "1":
                print(str(idx) + " " + row[3])
                if idx in square_by_count:
                    square_by_count[idx] += 1
                else:
                    square_by_count[idx] = 1
            if idx == "100_0" and row[1] == "1":
                max_900_0 = max(max_900_0, float(row[3]))
                square = img.load_square_from_file(row[0])
                plt.figure(figsize=(10, 8))
                plt.imshow(square.transpose())
                plt.title("Sample: " + row[0] + " with label: " + row[1])
                plt.colorbar()
                plt.show()

        print(square_by_count)
        print(max_900_0)


#count_outlier_squares("samples/valid_samples.csv")
# show_distribution_by_classes("samples/bad_samples.csv")
# show_average_vel_by_squares("samples/bad_samples.csv")
# print(show_average_vel_by_squares("samples/bad_samples.csv"))
# print(extract_square_index("samples/bad/vel/ARCTIC_1h_UV_grid_UV_20130101-20130101_0_0"))
# extend_datasets()
# show_hist_samples_distribution("samples/good_samples.csv")
# show_hist_samples_distribution("samples/bad_samples.csv")
# show_hist_samples_distribution("samples/valid_samples.csv")

# img.slice_uv_squares("samples/data/")
# img.slice_uv_squares("samples/arctic/")

# img.slice_uv_squares("samples/arctic/", "samples/bad/", mode="arctic")

'''
for image_index in range(0, 1):
    for x in range(0, 1100, 100):
        for y in range(0, 400, 100):
            u_file_name = "samples/out/rea0" + "_u_" + str(x) + "_" + str(y)
            v_file_name = "samples/out/rea0" + "_v_" + str(x) + "_" + str(y)
            u = img.load_square_from_file(u_file_name)
            v = img.load_square_from_file(v_file_name)
            u[u < -30000.0] = 0.0
            v[v < -30000.0] = 0.0
            vel = calculate_velocity_magnitude_matrix(u, v)

            show_velocity_square(vel)


'''

# label_bad_samples()
