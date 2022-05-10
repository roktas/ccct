#!/usr/bin/env python3

import functools
import json
import math
import os
import sys

import colour
import numpy as np

import logging

from contextlib import contextmanager,redirect_stderr
from os import devnull

@contextmanager
def suppress_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(devnull, 'w') as fnull:
        with redirect_stderr(fnull) as err:
            yield (err)

T_START = 2500    # Kelvin
T_FINISH = 10000  # Kelvin

# See colour-develop/colour/plotting/temperature.py#90-100
def uv_to_xy(uv):
    """
Converts given *uv* chromaticity coordinates to xy/*ij* chromaticity
coordinates.
"""

    return colour.models.UCS_uv_to_xy(uv)

# See colour-develop/colour/plotting/temperature.py#123-125
def temperature_to_isotemperature_line(T):
    """
T = 2500 # Kelvin

return (x0, y0, x1, y1)
"""
    D_uv = 0.025

    x0, y0 = uv_to_xy(colour.temperature.CCT_to_uv(np.array([T, -D_uv]), 'Robertson 1968'))
    x1, y1 = uv_to_xy(colour.temperature.CCT_to_uv(np.array([T, D_uv]), 'Robertson 1968'))

    return ([x0, y0], [x1, y1])

def is_between_Ts_Tf(xy, Ts=T_START, Tf=T_FINISH):
    p = xy
    b1 = is_below_line_at_T(Ts, p)
    b2 = is_below_line_at_T(Tf, p)
    b = b1 and not(b2)

    # print(b1, b2, b)

    if not(b1):
      b = -2
    elif b2:
      b = -1

    return b

def is_below_line_at_T(T, p):  
    p1, p2 = temperature_to_isotemperature_line(T)

    x1, y1 = p1
    x2, y2 = p2
    xA, yA = p

    v1 = (x2-x1, y2-y1)   # Vector 1
    v2 = (x2-xA, y2-yA)   # Vector 1
    xp = v1[0]*v2[1] - v1[1]*v2[0]  # Cross product

    return xp <= 0

def xy_to_CCT_with_andres99(xy, is_K_greater_50000=False): 
    x, y = xy[0], xy[1]

    # 50.000 - 8x10^5 K
    if is_K_greater_50000:
        xe = 0.3356
        ye = 0.1691

        A0 = 36284.48953
        A1 = 0.00228
        A2 = 5.4535e-36
        A3 = 0
        t1 = 0.07861
        t2 = 0.01543
        t3 = 1
        # 3.000 - 50.000 K
    else:
        xe = 0.3366
        ye = 0.1735

        A0 = -949.86315
        A1 = 6253.80338
        A2 = 28.70599
        A3 = 0.00004
        t1 = 0.92159
        t2 = 0.20039
        t3 = 0.07125

    e = math.exp

    n = (x - xe) / (y - ye)
    CCT = A0 + A1 * e(-n/t1) + A2 * e(-n/t2) + A3 * e(-n/t3)

    return CCT

"""
  RGB = np.array([255.0, 255.0, 255.0])
"""
def RGB_to_CCT(RGB, method="Ohno 2013"):
    # Conversion to tristimulus values.
    XYZ = colour.sRGB_to_XYZ(RGB / 255)

    # Conversion to chromaticity coordinates.
    xy = colour.XYZ_to_xy(XYZ)
    
    t = 0
    
    if method == "McCamy 1992":
        logging.debug('\txy: %s', xy)
        t = is_between_Ts_Tf(xy, Ts=2000, Tf=12500)
    elif method == "Kang 2002":
        t = is_between_Ts_Tf(xy, Ts=1667, Tf=25000)
    elif method == "Hernandez 1999":
        t = is_between_Ts_Tf(xy, Ts=3000, Tf=1000000)
    elif method == "Robertson 1968": #  500 K to 10<sup>6
        t = is_between_Ts_Tf(xy, Ts=500, Tf=1000000)
    elif method == "Ohno 2013": #  1.000 K to 20.000 K
        t = is_between_Ts_Tf(xy, Ts=1000, Tf=20000)
        
    if t != 1:
        if method == "Ohno 2013": #  1.000 K to 20.000 K
            if t == -1:
                CCT = 20000 + 1
            elif t == -2:
                CCT = 1000 - 1
        else:
            CCT = 0
            pass # TODO: diger metodlar icin benzer calisma yapilacak
    else:        
        if method == "andres99_1":
            CCT = xy_to_CCT_with_andres99(xy)
        elif method == "andres99_2":
            CCT = xy_to_CCT_with_andres99(xy, is_K_greater_50000=True)
        elif method == "Robertson 1968":
            uv = colour.UCS_to_uv(colour.XYZ_to_UCS(colour.xy_to_XYZ(xy)))
            CCT, _ = colour.uv_to_CCT(uv, method='Robertson 1968')
        elif method == "Ohno 2013":
            uv = colour.UCS_to_uv(colour.XYZ_to_UCS(colour.xy_to_XYZ(xy)))
            CCT, _ = colour.uv_to_CCT(uv, method="Ohno 2013")
        else:
            # Conversion to correlated colour temperature in K.
            # https://github.com/colour-science/colour#correlated-colour-temperature-computation-methods-colour-temperature
            CCT = colour.xy_to_CCT(xy, method)
    
    logging.debug("\t T: %.1f Kelvin (method: %s)" % (CCT, method))
    return round(CCT, 2)

def hex_to_rgb(string):
    hex = string.lstrip('#')
    return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))

def apply_recursively(obj, key, func):
    if isinstance(obj, dict):
        return {k: apply_recursively(v, k, func) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [apply_recursively(elem, key, func) for elem in obj]
    else:
        return func(key, obj)

@functools.cache
def _hex_to_cct(string):
    return RGB_to_CCT(np.array(hex_to_rgb(string)))

def hex_to_cct(string):
    with suppress_stderr():
        return _hex_to_cct(string)

def _process(data):
    def convert_color_like(key, value):
        if key.endswith('color'):
            return { 'value': value, 'cct': _hex_to_cct(value) }
        return value

    return apply_recursively(data, '.', lambda k, v: convert_color_like(k, v))

def process(data):
    with suppress_stderr():
        return _process(data)
