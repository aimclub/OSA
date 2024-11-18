import os

import numpy as np
from netCDF4 import Dataset


def save_square_to_file(square, file_name):
    """
    Saves the given square array to a file in NumPy .npy format.

    Parameters:
    square (numpy.ndarray): The square array to be saved.
    file_name (str): The name of the file to save the square to.

    Returns:
    None
    """
    np.save(file_name + '.npy', square)


def load_square_from_file(file_name):
    """
    Loads a square numpy array from a file with the given file name.
    
    Parameters:
    file_name (str): The name of the file containing the square numpy array
    
    Returns:
    numpy.ndarray: The square numpy array loaded from the file
    """
    square = np.load(file_name + '.npy')
    return square


class NCImage:
        def __init__(self, file_name):
        """
        Initializes an instance of the class with the provided file name. 
        Sets the 'file_name' attribute to the input parameter 'file_name' and 
        initializes the 'dataset' attribute with a Dataset object created from 
        the specified file in read mode.
        
        Parameters:
        file_name (str): The name of the file to be used to create the Dataset object.
        """
        self.file_name = file_name
        self.dataset = Dataset(filename=file_name, mode='r')

        def extract_variable(self, var_name):
        """
        Extracts a variable from the dataset based on the variable name provided.
        
        Parameters:
        - var_name: str, the name of the variable to extract
        
        Returns:
        - var: numpy.ndarray, the variable array extracted from the dataset
        """
        var = np.array(self.dataset.variables[var_name])
        var = self.convert_var_if_global(var)
        return var

        def convert_var_if_global(self, var):
            """
            Converts the input variable if the number of depths is 75. It reorganizes the depths 
            based on a predefined depth_per_level list, adjusts the values accordingly, 
            and returns a modified variable.
    
            Args:
                var (numpy.ndarray): The input variable to be converted.
    
            Returns:
                numpy.ndarray: The converted variable if the number of depths is 75, 
                otherwise returns the original variable.
            """
            #TODO: depthv, depth
            depths = self.dataset.dimensions['depthv']
    
            if len(depths) == 75:
                depth_per_level = [6, 5, 4, 5, 5, 5, 6, 4, 4, 4, 3, 4, 2, 3, 3, 3, 2, 7]
                depth_converted = []
                for level in range(0, len(depth_per_level)):
                    depth_converted.extend([level] * depth_per_level[level])
    
                for depth in range(75):
                    var[0, depth_converted[depth], :, :] += 1 / depth_per_level[depth_converted[depth]] * var[0, depth, :, :]
    
                result = var[:, 0:18, :, :]
                return result
            else:
                return var

        def extract_square(self, var_name, x_offset, y_offset, size, depth=0, time=0):
            """
            Extracts a square subset of a variable's data array at a specific depth and time.
    
            Parameters:
            var_name (str): The name of the variable to extract.
            x_offset (int): The starting x-coordinate of the square subset.
            y_offset (int): The starting y-coordinate of the square subset.
            size (int): The size of the square subset.
            depth (int): The depth index to extract data from (default is 0).
            time (int): The time index to extract data from (default is 0).
    
            Returns:
            numpy.ndarray: A square subset of the variable's data array at the specified depth and time.
            """
            return self.extract_variable(var_name)[time, depth, x_offset:x_offset + size, y_offset:y_offset + size]

        def extract_square_from_variable(self, var, x_offset, y_offset, size, depth=0, time=0):
        """
        Extracts a square region from a multi-dimensional variable at a specific time and depth.
    
        Parameters:
        var (array): The multi-dimensional variable to extract from.
        x_offset (int): The starting x-coordinate of the square region.
        y_offset (int): The starting y-coordinate of the square region.
        size (int): The size of the square region.
        depth (int): The depth of the variable to extract from (default is 0).
        time (int): The time index of the variable to extract from (default is 0).
    
        Returns:
        array: The square region extracted from the variable.
        """
        return var[time, depth, x_offset:x_offset + size, y_offset:y_offset + size]


def generate_square_name(file_name, var, x, y):
    """
    Generate a specific name for a square based on the provided file name, variable name, x, and y coordinates.
    
    Args:
    file_name (str): The name of the file.
    var (str): The variable name.
    x (int): The x coordinate of the square.
    y (int): The y coordinate of the square.
    
    Returns:
    str: A string representing the generated square name.
    """
    return '_'.join((file_name.split('.')[0], var, str(x), str(y)))


def slice_uv_squares(input_dir, output_dir, mode="arctic"):
    """
    Slices oceanographic data images stored in the input directory into smaller square images 
    of size 100x100 pixels, extracts U and V components based on the specified mode, and saves 
    the extracted squares into the output directory. The mode can be set to 'arctic' or 'global' 
    to determine the names of the U and V components. Progress is logged during the process.
    
    Args:
    input_dir (str): Path to the directory containing the oceanographic data images.
    output_dir (str): Path to the directory where the extracted U and V component squares will be saved.
    mode (str, optional): The mode to determine the names of the U and V components. Defaults to 'arctic'.
    """
    index = 1
    amount = len(os.listdir(input_dir))

    square_size = 100

    #output_dir = "samples/out/"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    u_name = ""
    v_name = ""
    if mode == "global":
        u_name = 'u'
        v_name = 'v'
    elif mode == "arctic":
        u_name = 'vozocrtx'
        v_name = 'vomecrty'

    for file_name in os.listdir(input_dir):
        image = NCImage(input_dir + file_name)
        square_index = 1
        squares_amount = 44
        for x in range(0, 1100, square_size):
            for y in range(0, 400, square_size):
                square = image.extract_square(v_name, y, x, square_size)
                square_name = generate_square_name(file_name, v_name, x, y)
                save_square_to_file(square, output_dir + square_name)
                square = image.extract_square(u_name, y, x, square_size)
                square_name = generate_square_name(file_name, u_name, x, y)
                save_square_to_file(square, output_dir + square_name)
                print("squares: " + str(square_index) + "/" + str(squares_amount) + " done")
                square_index += 1
        # TODO: improve logging
        print("image: " + str(index) + "/" + str(amount) + " done")
        index += 1
