import csv
import os

import matplotlib

# matplotlib.use('TkAgg')

import matplotlib.animation as animation
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import numpy as np
from keras.models import load_model
from matplotlib.patches import Polygon, Patch
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.basemap import Basemap
from netCDF4 import Dataset as NetCDFFile

import data
import image as img


def draw():
    """
    This method reads ice concentration data from a NetCDF file and plots it on a map using Basemap.
    It then adds coastlines, countries, continent fill, and a colorbar to the plot before displaying it.
    """
    nc = NetCDFFile("for_figures\\bad.nc")
    lat = nc.variables['nav_lat'][:]
    lon = nc.variables['nav_lon'][:]
    ice = nc.variables['iceconc'][:][0]

    lat_left_bottom = lat[-1][-1]
    lon_left_bottom = lon[-1][-1]
    lat_right_top = lat[0][0]
    lon_right_top = lon[0][0]
    lat_center = 90
    lon_center = 110
    m = Basemap(projection='stere', lon_0=lon_center, lat_0=lat_center, resolution='l',
                llcrnrlat=lat_left_bottom, llcrnrlon=lon_left_bottom,
                urcrnrlat=lat_right_top, urcrnrlon=lon_right_top)

    m.pcolormesh(lon, lat, ice, latlon=True, cmap='RdYlBu_r', vmax=1)
    m.drawcoastlines()
    m.drawcountries()
    m.fillcontinents(color='#cc9966', lake_color='#99ffff')

    m.drawcoastlines()
    m.drawcountries()
    m.fillcontinents(color='#cc9966', lake_color='#99ffff')
    ax = plt.gca()
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)

    plt.colorbar(cax=cax, label="Ice concentration")
    plt.show()
    # plt.savefig("bad_ice_08_27.png", dpi=500)


def draw_map(nc_file_name):
    """
    This method reads a NetCDF file containing latitude and longitude data, loads sea current velocity data from
    corresponding files, and plots a map with sea current velocity colored based on the data. It also draws coastlines,
    countries, and continents on the map, as well as adds a colorbar to indicate sea current velocity levels.
    """
    nc = NetCDFFile(nc_file_name, 'r+')
    lat = nc.variables['nav_lat_grid_U'][:]
    lon = nc.variables['nav_lon_grid_U'][:]
    nc_name = nc_file_name.split("/")[4].split(".")[0]
    velocity = np.zeros((400, 1100), dtype=np.float32)
    vel_dir = "samples/bad/vel/"
    for file_name in os.listdir(vel_dir):
        if nc_name in file_name:
            square = img.load_square_from_file(vel_dir + file_name.split(".")[0])
            print(file_name)
            print(str(np.min(square)) + "; " + str(np.max(square)))
            square_index = data.extract_square_index(vel_dir + file_name.split(".")[0])
            x = int(square_index.split("_")[0])
            y = int(square_index.split("_")[1])
            print(str(x) + " " + str(y))
            velocity[y:y + 100, x:x + 100] = square

    nc.close()
    lat_left_bottom = lat[-1][-1]
    lon_left_bottom = lon[-1][-1]
    lat_right_top = lat[0][0]
    lon_right_top = lon[0][0]

    lat_center = 90
    # 110, 119
    lon_center = 110
    m = Basemap(projection='stere', lon_0=lon_center, lat_0=lat_center, resolution='l',
                llcrnrlat=lat_left_bottom, llcrnrlon=lon_left_bottom,
                urcrnrlat=lat_right_top, urcrnrlon=lon_right_top)

    m.pcolormesh(lon, lat, velocity, latlon=True, cmap='RdYlBu_r', vmax=0.6)
    m.drawcoastlines()
    m.drawcountries()
    m.fillcontinents(color='#cc9966', lake_color='#99ffff')

    ax = plt.gca()
    # ax.tick_params(labelsize=10)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)

    plt.colorbar(cax=cax, label="Sea current velocity")
    # ax = plt.gca()
    # divider = make_axes_locatable(ax)
    # cax = divider.append_axes("right", size="5%", pad=0.05)

    # plt.colorbar().set_label(label='Sea current velocity', size=15)
    # with open("samples/valid_samples.csv", 'r', newline='') as csvfile:
    #     samples = []
    #
    #     reader = csv.reader(csvfile, delimiter=',')
    #     for row in reader:
    #         if "samples/bad/vel/" + nc_name in row[0]:
    #             print(row)
    #             samples.append(row)
    #             square_index = data.extract_square_index(row[0])
    #
    #             x = int(square_index.split("_")[0])
    #             y = int(square_index.split("_")[1])
    #
    #             if (x >= 100) and (x < 1000) and (y < 300):
    #
    #                 sample = np.zeros((1, 100, 100, 1), dtype=np.float32)
    #                 square = np.expand_dims(img.load_square_from_file(row[0]), axis=2)
    #                 sample[0] = square
    #                 lat_poly = np.array([lat[y][x], lat[y][x + 99], lat[y + 99][x + 99], lat[y + 99][x])
    #                 lon_poly = np.array([lon[y][x], lon[y][x + 99], lon[y + 99][x + 99], lon[y + 99][x])
    #                 mapx, mapy = m(lon_poly, lat_poly)
    #                 points = np.zeros((4, 2), dtype=np.float32)
    #                 for j in range(0, 4):
    #                     points[j][0] = mapx[j]
    #                     points[j][1] = mapy[j]
    #                 poly = Polygon(points, color='black', fill=False, linewidth=3)
    #                 ax.add_patch(poly)

    # plt.savefig("levels" + "_!!!.png", dpi=500)
    plt.show()


def draw_velocity_map(nc_file_name):
    """
    Draws a velocity map based on the data from a NetCDF file. Retrieves the sea current velocity data from
    specific image files, plots the data on a basemap, and uses a trained model to detect anomalies in the
    velocity data. Anomalies are marked on the map with polygons colored based on the model prediction.
    
    Args:
    nc_file_name (str): Name of the NetCDF file containing the sea current velocity data.
    
    Returns:
    None
    """
    nc = NetCDFFile(nc_file_name, 'r+')
    lat = nc.variables['nav_lat_grid_U'][:]
    lon = nc.variables['nav_lon_grid_U'][:]
    vel_dir = "samples/bad/vel/"
    nc_name = nc_file_name.split("/")[4].split(".")[0]
    velocity = np.zeros((400, 1100), dtype=np.float32)
    for file_name in os.listdir(vel_dir):
        if nc_name in file_name:
            square = img.load_square_from_file(vel_dir + file_name.split(".")[0])
            print(file_name)
            print(str(np.min(square)) + "; " + str(np.max(square)))
            square_index = data.extract_square_index(vel_dir + file_name.split(".")[0])
            x = int(square_index.split("_")[0])
            y = int(square_index.split("_")[1])
            print(str(x) + " " + str(y))
            velocity[y:y + 100, x:x + 100] = square

    nc.close()
    lat_left_bottom = lat[-1][-1]
    lon_left_bottom = lon[-1][-1]
    lat_right_top = lat[0][0]
    lon_right_top = lon[0][0]

    lat_center = 90
    # 110, 119
    lon_center = 110
    m = Basemap(projection='stere', lon_0=lon_center, lat_0=lat_center, resolution='l',
                llcrnrlat=lat_left_bottom, llcrnrlon=lon_left_bottom,
                urcrnrlat=lat_right_top, urcrnrlon=lon_right_top)

    m.pcolormesh(lon, lat, velocity, latlon=True, cmap='RdYlBu_r', vmax=0.6)
    m.drawcoastlines()
    m.drawcountries()
    m.fillcontinents(color='#cc9966', lake_color='#99ffff')
    # plt.rcParams.update({'font.size': 22})
    ax = plt.gca()
    # ax.tick_params(labelsize=10)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)

    plt.colorbar(cax=cax, label="Sea current velocity")
    # plt.title("Anomalies detection results for: " + "20 March, 2013")
    model = load_model("samples/current_model/model.h5")
    valid_squares = [[*list(range(1, 10))]]
    with open("samples/valid_samples.csv", 'r', newline='') as csvfile:
        samples = []

        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            if "samples/bad/vel/" + nc_name in row[0]:
                print(row)
                samples.append(row)
                square_index = data.extract_square_index(row[0])

                x = int(square_index.split("_")[0])
                y = int(square_index.split("_")[1])

                if (x >= 100) and (x < 1000) and (y < 300):

                    sample = np.zeros((1, 100, 100, 1), dtype=np.float32)
                    square = np.expand_dims(img.load_square_from_file(row[0]), axis=2)
                    sample[0] = square
                    result = model.predict(sample)
                    result_x, result_y = m(lon[y + 50][x + 50], lat[y + 50][x + 50])
                    ax.text(result_x, result_y, "%0.3f" % result[0][0], ha='center', size=7, color="yellow",
                            path_effects=[PathEffects.withStroke(linewidth=3, foreground='black')])
                    if row[1] == "1":
                        print("outlier!")
                        lat_poly = np.array([lat[y][x], lat[y][x + 99], lat[y + 99][x + 99], lat[y + 99][x])
                        lon_poly = np.array([lon[y][x], lon[y][x + 99], lon[y + 99][x + 99], lon[y + 99][x])
                        mapx, mapy = m(lon_poly, lat_poly)
                        points = np.zeros((4, 2), dtype=np.float32)
                        for j in range(0, 4):
                            points[j][0] = mapx[j]
                            points[j][1] = mapy[j]

                        if result[0][0] > 0.5:
                            poly = Polygon(points, color='green', fill=False, linewidth=3)
                            ax.add_patch(poly)
                        else:
                            poly = Polygon(points, color='red', fill=False, linewidth=3)
                            ax.add_patch(poly)
                    else:
                        if result[0][0] > 0.5:
                            lat_poly = np.array([lat[y][x], lat[y][x + 99], lat[y + 99][x + 99], lat[y + 99][x])
                            lon_poly = np.array([lon[y][x], lon[y][x + 99], lon[y + 99][x + 99], lon[y + 99][x])
                            mapx, mapy = m(lon_poly, lat_poly)
                            points = np.zeros((4, 2), dtype=np.float32)
                            for j in range(0, 4):
                                points[j][0] = mapx[j]
                                points[j][1] = mapy[j]
                            poly = Polygon(points, color='red', fill=False, linewidth=3)
                            ax.add_patch(poly)

                    print(result)

    # plt.show()
    red = Patch(color='red', label='Error')
    green = Patch(color='green', label='Correct')
    plt.legend(loc='lower right', fontsize='medium', bbox_to_anchor=(1, 1), handles=[green, red])
    plt.savefig("test" + "_bad_result.png", dpi=500)


def draw_velocity_map_with_level(nc_file_name, level):
    """
    Draws a velocity map based on the specified NetCDF file and level.
    The method reads the velocity data from the NetCDF file, calculates the magnitude of the velocity,
    and visualizes it on a map using Basemap. It also loads a pre-trained model to predict certain areas
    where the velocity might exceed a certain threshold and highlights those areas on the map.
    
    Args:
    nc_file_name (str): The name of the NetCDF file containing velocity data.
    level (int): The level at which to extract the velocity data.
    
    Returns:
    None
    """
    nc = NetCDFFile(nc_file_name, 'r+')
    lat = nc.variables['nav_lat_grid_U'][:]
    lon = nc.variables['nav_lon_grid_U'][:]

    velocity = np.zeros((400, 1100), dtype=np.float32)

    time = 0

    x_vel = nc.variables['vozocrtx'][:][time][level]
    y_vel = nc.variables['vomecrty'][:][time][level]

    velocity = data.calculate_velocity_magnitude_matrix(x_vel, y_vel)

    lat_left_bottom = lat[-1][-1]
    lon_left_bottom = lon[-1][-1]
    lat_right_top = lat[0][0]
    lon_right_top = lon[0][0]

    lat_center = 90
    # 110, 119
    lon_center = 110
    m = Basemap(projection='stere', lon_0=lon_center, lat_0=lat_center, resolution='l',
                llcrnrlat=lat_left_bottom, llcrnrlon=lon_left_bottom,
                urcrnrlat=lat_right_top, urcrnrlon=lon_right_top)

    m.pcolormesh(lon, lat, velocity, latlon=True, cmap='jet', vmax=0.6)
    m.drawcoastlines()
    m.drawcountries()
    m.fillcontinents(color='#cc9966', lake_color='#99ffff')

    plt.colorbar()
    plt.title(nc_file_name)

    model = load_model("samples/model.h5")

    for y in range(0, 400, 100):
        for x in range(0, 1100, 100):
            sample = np.zeros((1, 100, 100, 1), dtype=np.float32)
            sample[0] = np.expand_dims(velocity[y:y + 100, x:x + 100], axis=2)
            # print(sample)
            result = model.predict(sample)
            result_x, result_y = m(lon[y + 50][x + 50], lat[y + 50][x + 50])
            max_x, max_y = m(lon[y + 70][x + 50], lat[y + 70, x + 50])
            plt.text(result_x, result_y, str(result[0][0]), ha='center', size=10, color="yellow",
                     bbox=dict(facecolor='black', alpha=0.5, edgecolor='black'))
            plt.text(max_x, max_y, np.max(sample[0]), ha='center', size=10, color="yellow")
            if result[0][0] > 0.5:
                lat_poly = np.array([lat[y][x], lat[y][x + 99], lat[y + 99][x + 99], lat[y + 99][x]])
                lon_poly = np.array([lon[y][x], lon[y][x + 99], lon[y + 99][x + 99], lon[y + 99][x]])
                mapx, mapy = m(lon_poly, lat_poly)
                points = np.zeros((4, 2), dtype=np.float32)
                for j in range(0, 4):
                    points[j][0] = mapx[j]
                    points[j][1] = mapy[j]
                poly = Polygon(points, facecolor='green', alpha=0.4)
                plt.gca().add_patch(poly)

    plt.show()


def init_velocity_field(nc_file_name):
    """
    Initializes and plots the sea current velocity field based on the NetCDF file provided.
    
    Parameters:
    nc_file_name (str): The name of the NetCDF file containing the latitude and longitude data.
    
    Returns:
    ax (matplotlib.axes.Axes): The plot axes.
    lat (numpy.ndarray): Array of latitude values.
    lon (numpy.ndarray): Array of longitude values.
    m (mpl_toolkits.basemap.Basemap): Basemap object used for plotting.
    """
    nc = NetCDFFile(nc_file_name, 'r+')
    lat = nc.variables['nav_lat_grid_U'][:]
    lon = nc.variables['nav_lon_grid_U'][:]
    nc_name = nc_file_name.split("/")[4].split(".")[0]
    velocity = np.zeros((400, 1100), dtype=np.float32)
    vel_dir = "samples/bad/vel/"
    for file_name in os.listdir(vel_dir):
        if nc_name in file_name:
            square = img.load_square_from_file(vel_dir + file_name.split(".")[0])
            square_index = data.extract_square_index(vel_dir + file_name.split(".")[0])
            x = int(square_index.split("_")[0])
            y = int(square_index.split("_")[1])
            velocity[y:y + 100, x:x + 100] = square

    nc.close()
    lat_left_bottom = lat[-1][-1]
    lon_left_bottom = lon[-1][-1]
    lat_right_top = lat[0][0]
    lon_right_top = lon[0][0]

    lat_center = 90
    # 110, 119
    lon_center = 110
    m = Basemap(projection='stere', lon_0=lon_center, lat_0=lat_center, resolution='l',
                llcrnrlat=lat_left_bottom, llcrnrlon=lon_left_bottom,
                urcrnrlat=lat_right_top, urcrnrlon=lon_right_top)

    m.pcolormesh(lon, lat, velocity, latlon=True, cmap='RdYlBu_r', vmax=0.6)
    m.drawcoastlines()
    m.drawcountries()
    m.fillcontinents(color='#cc9966', lake_color='#99ffff')

    ax = plt.gca()
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    plt.colorbar(cax=cax, label="Sea current velocity")

    return ax, lat, lon, m


class CoordsIterator:
        def __init__(self):
        """
        Initializes an instance of the class by setting the 'coords' attribute to a new instance of the 'coords' class
        and initializing the '_idx' attribute to -1.
        """
        self.coords = coords()
        self._idx = -1

        def next(self):
        """
        Increments the index by 1 and returns the next coordinate along with its index. 
        If there are no more coordinates left, it returns (-1, -1).
        
        Returns:
        Tuple: (coordinate, index) if there are more coordinates available, else (-1, -1)
        """
        self._idx += 1
        if self._idx < len(self.coords):
            return self.coords[self._idx], self._idx
        else:
            return -1, -1


def coords():
    """
    Generates a list of coordinates representing a grid where x ranges from 0 to 1000 and y ranges from 0 to 200
    Returns:
        c (list): A list of tuples representing coordinates in the grid
    """
    c = []
    idx = 0
    for y in range(0, 400, 100):
        for x in range(0, 1100, 100):
            if (x >= 100) and (x < 1000) and (y < 300):
                c.append((x, y))
                idx += 1

    return c


def label_square(i, it, ax, lat, lon, m):
    """
    Labels a square on a map with a specific color based on the index value.
    
    Parameters:
    i (int): The index value.
    it (iterator): An iterator object.
    ax (object): The axes object of the plot.
    lat (numpy.array): 2D array of latitude values.
    lon (numpy.array): 2D array of longitude values.
    m (object): Basemap object for mapping coordinates.
    
    Returns:
    ax (object): The updated axes object.
    """
    coord, idx = it.next()
    if coord != -1:
        x, y = coord
        lat_poly = np.array([lat[y][x], lat[y][x + 99], lat[y + 99][x + 99], lat[y + 99][x]])
        lon_poly = np.array([lon[y][x], lon[y][x + 99], lon[y + 99][x + 99], lon[y + 99][x]])
        mapx, mapy = m(lon_poly, lat_poly)
        points = np.zeros((4, 2), dtype=np.float32)
        for j in range(0, 4):
            points[j][0] = mapx[j]
            points[j][1] = mapy[j]
        if idx in [0, 1, 3, 4, 5, 6, 7]:
            poly = Polygon(points, color='red', fill=False, linewidth=3)
            ax.add_patch(poly)
        else:
            poly = Polygon(points, color='black', fill=False, linewidth=3)
            ax.add_patch(poly)

        return ax,


def labeling_anim(nc_file_name):
    """
    Creates an animation of labeling squares on a velocity field using data from a netCDF file.
    
    Parameters:
    nc_file_name (str): The name of the netCDF file containing the velocity field data.
    
    Returns:
    None
    """
    ax, lat, lon, m = init_velocity_field(nc_file_name)
    it = CoordsIterator()
    ani = animation.FuncAnimation(ax.figure, label_square, fargs=(it, ax, lat, lon, m,),
                                  frames=44, interval=100, repeat=True)
    save_anim_as_gif('Labeling.gif', ani)

    # plt.show()


def save_anim_as_gif(name, anim, path_to_imagemagick='C:\Program Files\ImageMagick-7.0.8-Q16\magick.exe'):
    """
    Save the provided animation as a GIF file using ImageMagick.

    Parameters:
    name (str): The name of the GIF file to be saved.
    anim (matplotlib.animation.Animation): The animation object to be saved as a GIF.
    path_to_imagemagick (str): The path to the ImageMagick executable.

    Returns:
    None
    """
    
    matplotlib.rcParams['animation.convert_path'] = path_to_imagemagick
    anim.save(name, writer='imagemagick', fps=5)




# draw_velocity_map_with_level("samples/valid!/samples/arctic/ARCTIC_1h_UV_grid_UV_20130320-20130320.nc", 15)
# draw_velocity_map("samples/valid!/samples/arctic/ARCTIC_1h_UV_grid_UV_20130320-20130320.nc")
draw_map("samples/valid!/samples/arctic/ARCTIC_1h_UV_grid_UV_20130119-20130119.nc")
# labeling_anim("samples/valid!/samples/arctic/ARCTIC_1h_UV_grid_UV_20130204-20130204.nc")
# draw()
