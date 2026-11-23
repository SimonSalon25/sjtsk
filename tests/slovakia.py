"""Test points: a regular grid of ETRS89 points inside an approximate outline of Slovakia (3,978 points)."""
import numpy as np

#: approximate outline of Slovakia (lon, lat) — for selecting statistics points only, not the state border
OUTLINE = [(16.84, 48.38), (16.95, 48.60), (17.20, 48.87), (17.55, 48.80), (17.88, 48.93), (18.10, 49.05),
           (18.40, 49.31), (18.85, 49.52), (19.25, 49.52), (19.47, 49.60), (19.80, 49.20), (20.10, 49.30),
           (20.60, 49.40), (21.10, 49.40), (21.60, 49.45), (22.10, 49.20), (22.56, 49.08), (22.15, 48.41),
           (21.70, 48.38), (21.20, 48.52), (20.80, 48.57), (20.30, 48.26), (19.65, 48.23), (19.00, 48.07),
           (18.80, 47.83), (18.20, 47.75), (17.70, 47.77), (17.17, 48.01), (16.95, 48.12)]


def points(step_lon=0.05, step_lat=0.03):
    from shapely import contains_xy
    from shapely.geometry import Polygon
    lon, lat = np.meshgrid(np.arange(16.8, 22.6, step_lon), np.arange(47.7, 49.65, step_lat))
    m = contains_xy(Polygon(OUTLINE), lon, lat)
    return lon[m], lat[m]
