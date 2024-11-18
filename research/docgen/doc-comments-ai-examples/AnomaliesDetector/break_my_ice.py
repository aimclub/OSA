# -*- coding: utf-8 -*-
"""
Created on Fri May 11 11:16:33 2018

@author: user
"""

import netCDF4 as nc
import numpy as np
import scipy.ndimage.filters

par_x = 1100
par_y = 400

name = 'ARCTIC_1h_ice_grid_TUV_20130102-20130102.nc'


# name=sys.argv[1]

def generate_circle(R):
    """
    Generate a binary circular image represented as a numpy array with size R x R.
    
    Parameters:
    R (int): The radius of the circle.
    
    Returns:
    numpy array: A binary circle image with radius R.
    """
    circle = np.zeros((R, R))
    half_rad = int(np.floor(R / 2))
    circle[:, half_rad] = 1
    for i in range(0, R - half_rad):
        circle[i:-i, half_rad - i] = 1
        circle[i:-i, half_rad + i] = 1
    circle = (circle - 1) * (circle - 1)
    return circle


def hole_mask(n, par_x, par_y):
    """
    Generates a mask with randomly placed circular holes of random sizes within specified dimensions.

    Args:
    n (int): Number of holes to generate
    par_x (int): Width of the mask
    par_y (int): Height of the mask

    Returns:
    np.array: 2D array representing the mask with holes
    """
    h_mask = np.ones((par_y, par_x))
    for i in range(n):
        random_x = np.random.randint(par_x)
        random_y = np.random.randint(par_y)
        random_R = np.random.randint(50) + 1
        if random_x + random_R + 2 > par_x: random_x = random_x - random_R - 2
        if random_y + random_R + 2 > par_y: random_y = random_y - random_R - 2
        h_mask[random_y:random_y + random_R, random_x:random_x + random_R] = generate_circle(random_R)
    return h_mask


def break_my_ice(name, par_x, par_y, mode):
    """
    Modify ice concentration data in a netCDF file based on the specified mode.
    
    Parameters:
    name (str): Name of the netCDF file containing ice concentration data.
    par_x (int): Number of grid points in the x-direction.
    par_y (int): Number of grid points in the y-direction.
    mode (str): Specifies the type of modification to be applied to the ice concentration data.
    
    Returns:
    None
    """
    nc_break = nc.Dataset(name, 'r+')

    mask = (nc_break['ice_conc'][:].filled(0))[0, :, :] / 100.0
    conc = (nc_break['ice_conc'][:].filled(0))[0, :, :] / 100.0

    if mode == 'full_ice':
        conc_avg = 0.5
        for time in range(len(nc_break['iceconc'][:, :, :]):
            ncbath = nc.Dataset('bathy_meter_mask.nc')
            bath_msk = ncbath['Bathymetry'][:, :]
            nc_break['iceconc'][time,:,:]=bath_msk*conc_avg

    for x in range(par_x):
        for y in range(par_y):
            if mask[y, x] > 0: mask[y, x] = 1

    if mode == 'noise':
        white_noise = np.random.rand(par_y, par_x)
        mask *= white_noise

    if 'hole' in mode:
        pos = mode.index('_')
        hole_number = int(mode[(pos + 1):])
        h_mask = hole_mask(hole_number, par_x, par_y)
        mask *= h_mask

    if mode == 'spots':
        min_conc = 0.2
        white_noise = (1 - min_conc) * np.random.rand(par_y, par_x) + (min_conc)
        white_noise = scipy.ndimage.uniform_filter(white_noise, size=10, mode='constant')
        mask = white_noise

    if mode == 'no_ice': mask = 0

    for time in range(len(nc_break['ice_conc'][:, :, :]):
        if mode == 'spots':
            nc_break['ice_conc'][time, :, :] = conc * mask / np.max(conc * mask)
        elif mode == 'full_ice':
            nc_break['iceconc'][time, :, :] = bath_msk * conc_avg
        else:
            nc_break['ice_conc'][time, :, :] = conc * mask
    nc_break.close()

# break_my_ice(name, par_x, par_y, 'full_ice')
