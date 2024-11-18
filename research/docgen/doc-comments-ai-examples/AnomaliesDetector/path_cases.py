import os
import random

import keras.backend as K
import matplotlib
import tensorflow as tf

from break_my_ice import break_my_ice
from ice_data import IceDetector

matplotlib.use('agg')
import matplotlib.pyplot as plt


def init_session():
    """
    Initializes a TensorFlow session with GPU device 1.
    
    This method sets up a TensorFlow configuration with GPU device 1 as the visible device, 
    and then creates a TensorFlow session with this configuration using Keras backend.
    """
    config = tf.ConfigProto()
    config.gpu_options.visible_device_list = "1"
    K.set_session(tf.Session(config=config))


def full_ice(file_name):
    """
    This method takes in a file name as input and goes through each month of the year to detect ice using an IceDetector object.
    For each month, it initializes a session, creates an IceDetector object with the appropriate month value, and then uses the detector to detect ice in the input file.
    The method appends the percentage of ice detected for each month to a list called 'good' and prints the month and the corresponding ice detection value.
    Finally, it returns the list 'good' containing the percentage of ice detected for each month.

    Parameters:
    file_name (str): The name of the file to analyze for ice detection.

    Returns:
    list: A list of percentages representing the amount of ice detected for each month.
    """
    good = []
    for month in range(1, 13):
        init_session()
        detector = IceDetector(0.5, str(month)) if month >= 10 else IceDetector(0.5, "0" + str(month))
        pred, val = detector.detect(file_name)
        good.append(val * 100.0)
        print(month, val)

    return good


Generates holes in satellite images for pathological cases based on the specified size. Copies a random file from the 'samples/conc_satellite/2013/' directory for each month, renames it with '_break.nc' suffix, and moves it to the 'samples/pathological_cases/holes/{size}/' directory. Finally, calls the 'break_my_ice' function with the copied file, specified width and height, and a label based on the size of the hole.


def generate_spots():
    """
    Generates spots by copying a random file from each month in the specified directory to a separate directory with a '_break.nc' suffix. 
    Then calls the method 'break_my_ice' on each copied file with specified parameters.
    """
    dir = "samples/conc_satellite/2013/"
    holes_dir = "samples/pathological_cases/spots/"
    for month in range(1, 13):
        month_str = str(month) if month >= 10 else "0" + str(month)
        file = random.choice(os.listdir(dir + month_str + "/"))
        from_dir = dir + month_str + "/" + file
        to_dir = holes_dir + file + '_break.nc'
        os.system('cp ' + from_dir + ' ' + to_dir)
        print(to_dir)
        break_my_ice(to_dir, 1100, 400, 'spots')


def generate_noise():
    """
    This method generates noise by randomly selecting a file from a directory for each month in a year,
    then copies the selected file to another directory with '_break.nc' appended to its name. It also prints
    the path of the copied file and calls the function break_my_ice to add noise to the copied file.

    Parameters:
    None

    Returns:
    None
    """
    dir = "samples/conc_satellite/2013/"
    holes_dir = "samples/pathological_cases/noise/"
    for month in range(1, 13):
        month_str = str(month) if month >= 10 else "0" + str(month)
        file = random.choice(os.listdir(dir + month_str + "/"))
        from_dir = dir + month_str + "/" + file
        to_dir = holes_dir + file + '_break.nc'
        os.system('cp ' + from_dir + ' ' + to_dir)
        print(to_dir)
        break_my_ice(to_dir, 1100, 400, 'noise')


def detect_holes(size):
    """
    Returns a list of confidence values for detecting ice in holes of a specified size.
    
    Parameters:
    size (int): The size of the holes to be detected.
    
    Returns:
    list: A list of confidence values (in percentage) for each hole detected.
    """
    holes_dir = "samples/pathological_cases/holes/" + str(size) + "/"
    files = []
    for file in os.listdir(holes_dir):
        files.append(holes_dir + file)

    files = sorted(files)

    good = []

    idx = 1
    for file in files:
        init_session()
        detector = IceDetector(0.5, str(idx)) if idx >= 10 else IceDetector(0.5, "0" + str(idx))
        pred, val = detector.detect(file)
        good.append(val * 100.0)
        print(idx, val)
        idx += 1

    return good


def detect_spots():
    """
    This method detects spots in the images located in the 'samples/pathological_cases/spots/' directory.
    It initializes a session, creates an IceDetector object for each image, detects spots in the image, 
    calculates the percentage of good spots, and prints the index of the image along with the calculated value.
    
    Returns:
    - A list containing the percentage of good spots detected in each image.
    """
    holes_dir = "samples/pathological_cases/spots/"
    files = []
    for file in os.listdir(holes_dir):
        files.append(holes_dir + file)

    files = sorted(files)

    good = []

    idx = 1
    for file in files:
        init_session()
        detector = IceDetector(0.5, str(idx)) if idx >= 10 else IceDetector(0.5, "0" + str(idx))
        pred, val = detector.detect(file)
        good.append(val * 100.0)
        print(idx, val)
        idx += 1

    return good


def detect_noise():
    """
    Detects noise in a set of files located in a specific directory by using an IceDetector.
    
    Returns:
    List of percentages representing the amount of noise detected in each file.
    """
    holes_dir = "samples/pathological_cases/noise/"
    files = []
    for file in os.listdir(holes_dir):
        files.append(holes_dir + file)

    files = sorted(files)

    good = []

    idx = 1
    for file in files:
        init_session()
        detector = IceDetector(0.5, str(idx)) if idx >= 10 else IceDetector(0.5, "0" + str(idx))
        pred, val = detector.detect(file)
        good.append(val * 100.0)
        print(idx, val)
        idx += 1

    return good


def plot_holes():
    """
    Plots the prediction results for ice with holes based on different hole amounts detected.
    
    The method creates a figure with a specified font size, adds a subplot, and plots the detection results for ice with holes
    for 3 different hole amounts. The x-axis represents the months of the year, while the y-axis represents the percentage of 
    squares recognized as correct. The plot includes data for hole amounts of 50, 100, and 200. The resulting plot is saved 
    as an image file.
    """
    plt.rcParams.update({'font.size': 22})
    fig = plt.figure(figsize=(20, 10))
    ax = fig.add_subplot(111)

    months = [i for i in range(1, 13)]
    good = detect_holes(50)
    plt.plot(months, good, marker='o', c="c")

    good = detect_holes(100)
    plt.plot(months, good, marker='o', c="y")

    good = detect_holes(200)
    plt.plot(months, good, marker='o', c="r")

    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    ax.set_xticks(months)
    ax.set_xticklabels(labels)

    plt.xlabel('Month')
    plt.ylabel('Squares recognized as correct, %')
    plt.title('Prediction results for ice with holes')
    legend = plt.legend(['holes amount = 50', 'holes amount = 100', 'holes amount = 200'],
                        bbox_to_anchor=(1.05, 1), loc=2,
                        borderaxespad=0.)

    plt.savefig("samples/pathological_cases/holes_results.png", bbox_extra_artists=(legend,), bbox_inches='tight',
                dpi=500)


def plot_spots():
    """
    Plots the prediction results for ice with spots by month, showing the percentage of squares recognized as correct.
    
    Parameters:
    - None
    
    Returns:
    - None
    """
    plt.rcParams.update({'font.size': 22})
    fig = plt.figure(figsize=(20, 10))
    ax = fig.add_subplot(111)

    months = [i for i in range(1, 13)]
    good = detect_spots()
    plt.plot(months, good, marker='o', c="c")

    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    ax.set_xticks(months)
    ax.set_xticklabels(labels)

    plt.xlabel('Month')
    plt.ylabel('Squares recognized as correct, %')
    plt.title('Prediction results for ice with spots')
    # legend = plt.legend(['holes amount = 50', 'holes amount = 100', 'holes amount = 200'],
    #                     bbox_to_anchor=(1.05, 1), loc=2,
    #                     borderaxespad=0.)

    plt.savefig("samples/pathological_cases/spots_results.png", dpi=500)


def plot_noise():
    """
    Plot the prediction results for ice with noise. 
    The method generates a plot showing the percentage of squares recognized as correct for each month. 
    It uses the detect_noise() function to get the data, plots it with markers, sets the appropriate labels,
    and saves the plot as a PNG file.
    """
    plt.rcParams.update({'font.size': 22})
    fig = plt.figure(figsize=(20, 10))
    ax = fig.add_subplot(111)

    months = [i for i in range(1, 13)]
    good = detect_noise()
    plt.plot(months, good, marker='o', c="c")

    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    ax.set_xticks(months)
    ax.set_xticklabels(labels)

    plt.xlabel('Month')
    plt.ylabel('Squares recognized as correct, %')
    plt.title('Prediction results for ice with noise')

    plt.savefig("samples/pathological_cases/noise_results.png", dpi=500)


def plot_full_ice():
    """
    Plots the prediction results for the full ice case by reading data from multiple netCDF files and generating a line plot for each file. Each line plot represents the percentage of sub-areas recognized as correct for a specific concentration level of ice. The x-axis represents the month, while the y-axis represents the percentage of correct sub-areas.
    
    The method saves the plot as a PNG image with the filename 'full_ice_results.png' in the 'samples/pathological_cases' directory. A legend is included in the plot to distinguish between different concentration levels of ice.

    Parameters:
    None

    Returns:
    None
    """
    plt.rcParams.update({'font.size': 22})
    fig = plt.figure(figsize=(20, 10))
    ax = fig.add_subplot(111)

    months = [i for i in range(1, 13)]

    good = full_ice("samples/pathological_cases/no_ice.nc")
    plt.plot(months, good, marker='o', c="c")

    good = full_ice("samples/pathological_cases/full_ice_02.nc")
    plt.plot(months, good, marker='o', c="m")

    good = full_ice("samples/pathological_cases/full_ice_05.nc")
    plt.plot(months, good, marker='o', c="g")

    good = full_ice("samples/pathological_cases/full_ice_08.nc")
    plt.plot(months, good, marker='o', c="y")

    good = full_ice("samples/pathological_cases/full_ice_10.nc")
    plt.plot(months, good, marker='o', c='r')

    m = [i for i in range(1, 13)]
    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    ax.set_xticks(m)
    ax.set_xticklabels(labels)

    plt.xlabel('Month')
    plt.ylabel('Sub-areas recognized as correct, %')
    plt.title('Prediction results for full ice case')
    legend = plt.legend(['conc = 0.0', 'conc = 0.2', 'conc = 0.5', 'conc = 0.8', 'conc = 1.0'],
                        bbox_to_anchor=(1.05, 1), loc=2,
                        borderaxespad=0.)
    plt.savefig("samples/pathological_cases/full_ice_results.png", bbox_extra_artists=(legend,), bbox_inches='tight',
                dpi=500)


def plot_path_cases():
    """
    Plots the prediction results for pathological cases, showing sub-areas recognized as correct for each month.
    The plot includes noise, holes with amounts of 50, 100, and 200, as well as spots detected per month.
    The x-axis represents each month, while the y-axis represents the percentage of correct sub-areas.
    The plot is saved as 'path_results.png' in the 'samples/pathological_cases' directory.
    """
    plt.rcParams.update({'font.size': 22})
    fig = plt.figure(figsize=(20, 10))
    ax = fig.add_subplot(111)

    months = [i for i in range(1, 13)]
    noise = detect_noise()
    plt.plot(months, noise, marker='o', c="c", label='Noise')

    holes50 = detect_holes(50)
    plt.plot(months, holes50, marker='o', c="g", label='Holes with amount = 50')

    holes100 = detect_holes(100)
    plt.plot(months, holes100, marker='o', c="r", label='Holes with amount = 100')

    holes100 = detect_holes(200)
    plt.plot(months, holes100, marker='o', c="b", label='Holes with amount = 200')

    spots = detect_spots()
    plt.plot(months, spots, marker='o', c="y", label='Spots')

    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    ax.set_xticks(months)
    ax.set_xticklabels(labels)

    plt.xlabel('Month')
    plt.ylabel('Sub-areas recognized as correct, %')
    plt.title('Prediction results for pathological cases')
    plt.legend(loc='lower right', fontsize='medium')

    plt.savefig("samples/pathological_cases/path_results.png", dpi=500)


# plot_full_ice()

# for size in [50, 100, 200]:
#     generate_holes(size)

# plot_holes()
# generate_spots()
# plot_spots()
# generate_noise()
# plot_noise()
# plot_path_cases()
plot_full_ice()

