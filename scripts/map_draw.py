import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from IPython.display import display, clear_output

def draw_geojson(file_names: list[str]):
    gpds = []
    for file_name in file_names:
        gpds.append(gpd.read_file(file_name))
    gdf = pd.concat(gpds, ignore_index=True)
    gdf.explore(color='red')

def draw_points(coors: list[list[float, float]]):
    marker_kwds = {'radius':10, 'draggable':True, 'fill':True}
    geo = {'geometry':[Point(entity) for entity in coors]}
    names = {'name':[i for i in range(len(coors))]}
    d={**geo, **names}
    gdf = gpd.GeoDataFrame(d, crs="EPSG:4326")
    gdf.to_crs(32619)
    clear_output()
    display(gdf.explore(col='name', color="red", marker_type='circle_marker', marker_kwds = marker_kwds))
