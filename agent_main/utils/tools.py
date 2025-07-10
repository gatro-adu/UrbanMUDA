
from langchain_core.tools import tool
from geopy.distance import geodesic, distance, lonlat, great_circle
from geographiclib.geodesic import Geodesic
from pydantic import BaseModel, Field
from typing import Tuple, Optional, Annotated
from shapely.geometry import Polygon, Point, LineString, MultiLineString
from shapely.ops import nearest_points
import numpy as np
from langgraph.errors import NodeInterrupt
import geopandas as gpd
from scripts.map_search import searcher

# ============================================================================



def distance_tool(
        coord1: Annotated[list[float], Field(description="Coordinate of the first point")], 
        coord2: Annotated[list[float], Field(description="Coordinate of the first point")]
    ) -> float:
    """A tool that calculates the geodesic distance between two points"""

    distance_meter = distance(lonlat(*coord1), lonlat(*coord2)).m
    return distance_meter

class azimuth_input(BaseModel):
    x1: float = Field(description="the x location of the first point")
    x2: float = Field(description="the x location of the second point")
    y1: float = Field(description="the y location of the first point")
    y2: float = Field(description="the y location of the second point")
@tool(args_schema=azimuth_input)
def azimuth_tool(x1: float, x2: float, y1: float, y2: float) -> float:
    """A tool that calculates the azimuth of the second point from the first point"""
    geodict = Geodesic.WGS84.Inverse(y1, x1, y2, x2)
    azimuth = geodict["azi1"]
    return azimuth

class point_input(BaseModel):
    x: float = Field(description="the x location of the current point, longitude")
    y: float = Field(description="the y location of the current point, latitude")
    azimuth: float = Field(description="the azimuth of the point, from north, clockwise, in degrees")
    d: float = Field(description="the distance to the new point, in meters")
@tool(args_schema=point_input)
def point_tool(x: float, y: float, azimuth: float, d: float) -> list[float]:
    """A tool that calculates the new point based on the current point"""
    py, px, _ = distance(meters=d).destination(lonlat(x, y), bearing=azimuth)
    return [px, py]

# ============================================================================
class polygon_formation_input(BaseModel):
    x: float = Field(description="the x location of the centroid point, longitude")
    y: float = Field(description="the y location of the centroid point, latitude")
    n: int = Field(description="the number of points of the formation")
    d: float = Field(description="the distance between two points, in meters")
import math
@tool(args_schema=polygon_formation_input)
def polygon_formation_tool(x: float, y: float, n: int, d: float) -> list[list[float]]:
    """A tool that calculates the polygon formation based on the centroid point"""
    formation = []
    angle_in_degrees = 360 / n  # 计算张角
    angle_in_radians = math.radians(angle_in_degrees)
    l = d/2/math.sin(angle_in_radians/2)  # 计算腰长
    for i in range(n):
        azimuth = angle_in_degrees * i  # 计算方位角
        py, px, _ = distance(meters=l).destination(lonlat(x, y), bearing=azimuth)
        formation.append([px, py])
    return formation

class line_formation_input(BaseModel):
    x: float = Field(description="the x location of the centroid point, longitude")
    y: float = Field(description="the y location of the centroid point, latitude")
    n: int = Field(description="the number of points of the formation")
    d: float = Field(description="the distance between two points, in meters")
    azimuth: float = Field(description="the azimuth of the straight formation, from north, clockwise, in degrees")
@tool(args_schema=line_formation_input)
def line_formation_tool(x: float, y: float, n: float, d: float, azimuth: float) -> list[list[float]]:
    """A tool that calculates the straight formation based on the centroid point"""
    formation = []
    new_point1 = [x,y]
    new_point2 = [x,y]
    if n%2==0:
        for i in range(n//2):
            dd = d/2 if i==0 else d
            new_point1 = point_tool.invoke({"x": new_point1[0], "y": new_point1[1], "azimuth": azimuth, "d": dd})
            new_point2 = point_tool.invoke({"x": new_point2[0], "y": new_point2[1], "azimuth": azimuth+180, "d": dd})
            formation.extend([new_point1, new_point2])
    else:
        formation.append([x, y])
        for i in range(n//2):
            new_point1 = point_tool.invoke({"x": new_point1[0], "y": new_point1[1], "azimuth": azimuth, "d": d})
            new_point2 = point_tool.invoke({"x": new_point2[0], "y": new_point2[1], "azimuth": azimuth+180, "d": d})
            formation.extend([new_point1, new_point2])
    return formation




class circle_formation_input(BaseModel):
    center: list[float] = Field(description="the center of the circular formation")
    radius: float = Field(description="the radius of the circular formation")
    n: int = Field(description="the number of points of the formation")
    rotation: float = Field(description="the rotation of the circular formation")
@tool(args_schema=circle_formation_input)
def circle_formation_tool(center: list[float], radius: float, n: int, rotation: float) -> list[list[float]]:
    '''A tool that calculates the circular formation based on the centroid point'''
    positions = []
    angle_step = 360 / n
    for i in range(n):
        bearing = i * angle_step + rotation
        py, px, _ = distance(meters=radius).destination(lonlat(center[0], center[1]), bearing=bearing)
        positions.append((px, py))
    return positions


class v_formation_input(BaseModel):
    leader_pos: list[float] = Field(description="the position of the leader")
    angle: float = Field(description="the angle of the v formation")
    spacing: float = Field(description="the spacing of the v formation")
    n_left: int = Field(description="the number of points of the left side of the v formation")
    n_right: int = Field(description="the number of points of the right side of the v formation")
    rotation: float = Field(description="the rotation of the v formation")
@tool(args_schema=v_formation_input)
def v_formation_tool(leader_pos: list[float], angle: float, spacing: float, n_left: int, n_right: int, rotation: float) -> list[list[float]]:
    '''A tool that calculates the v formation based on the leader position'''
    positions = [leader_pos]  # 头部坐标
    # 计算侧翼位置
    lateral_step = np.radians(angle/2)
    for i in range(1, n_left+1):
        d = i * spacing
        py, px, _ = distance(meters=d).destination(lonlat(leader_pos[0], leader_pos[1]), bearing=lateral_step+rotation)
        positions.append((px, py))
    for i in range(1, n_right+1):
        d = i * spacing
        py, px, _ = distance(meters=d).destination(lonlat(leader_pos[0], leader_pos[1]), bearing=-lateral_step+rotation)
        positions.append((px, py))
    return positions

# 多层嵌套编队（暂时不用）
# def layered_formation_tool(
#     base_formation: List[list[float]],
#     layers: int = 3,
#     layer_spacing: float = 1000  # 米
# ) -> List[list[float]]:
#     """多层嵌套编队生成器"""
#     full_formation = []
    
#     for layer in range(1, layers+1):
#         scale = layer * layer_spacing
#         for point in base_formation:
#             # 计算中心到基点的方向
#             line = geod.Inverse(center[1], center[0], point[1], point[0])
#             bearing = line['azi1']
#             new_point = distance(scale)(center, bearing)
#             full_formation.append((new_point[0], new_point[1]))
    
#     return full_formation

# # 示例：三层三角形编队
# base_triangle = lambda: equilateral_triangle(3)
# print(layered_formation(base_triangle, layers=3, layer_spacing=4))

# ============================================================================
class midpoint_input(BaseModel):
    x1: float = Field(description="the x location of the first point, longitude")
    x2: float = Field(description="the x location of the second point, longitude")
    y1: float = Field(description="the y location of the first point, latitude")
    y2: float = Field(description="the y location of the second point, latitude")

@tool(args_schema=midpoint_input)
def midpoint_tool(x1: float, x2: float, y1: float, y2: float) -> list[float]:
    """A tool that calculates the central point between two points"""
    geodict = Geodesic.WGS84.Inverse(y1, x1, y2, x2)
    azimuth = geodict["azi1"]
    d = geodict['s12']/2
    y, x, _ = distance(meters=d).destination(lonlat(x1, y1), bearing=azimuth)
    return x, y


# ============================================================================

scale = 30
word_num = 50000

class location_input(BaseModel):
    location: str = Field(description="Name of the location")
@tool(args_schema=location_input)
def location_tool(location: str) -> str:
    '''A tool that obtains the similar-name location'''
    location_feature = searcher.similar_match(location)
    return f'与{location}名称相似的地理实体有：{location_feature}。请从中进行选择'

class name_nearby_input(BaseModel):
    name: str = Field(description="the name of the location")
@tool(args_schema=name_nearby_input)
def name_nearby_tool(name: str) -> str:
    '''A tool that obtains the nearby geometries from the name'''
    class Area(BaseModel):
        name: Optional[str]
        tag: str
        geometry: str
    class Relation(BaseModel):
        rcc: str
        distance: float
        azimuth: float
    class Nearby(BaseModel):
        relationship: Relation
        nearby_area: Area
    class Geo_info(BaseModel):
        target_area: Area
        nearby: Optional[list[Nearby]]=[]
    location_feature = searcher.similar_match(name)
    if len(location_feature)==0: 
        raise NodeInterrupt(f'未找到{name}。请重新输入')
    
    nearby = []
    triplets = []
    geo_pair = []
    for location_feature in location_feature:
        location_name = location_feature[0]
        location_tag = location_feature[1]
        location_geo = location_feature[2]
        nearby_features = searcher.get_nearby_feature(location_geo, scale)
        nearby.append(Geo_info(target_area=Area(name=location_name, tag=location_tag, geometry=str(location_geo))))
        for _, nearby_feature in nearby_features.iterrows():
            nearby_feature = nearby_feature.to_list()
            nearby_name = nearby_feature[0]
            nearby_tag = nearby_feature[1]
            nearby_geo = nearby_feature[2]
            if {location_geo, nearby_geo} in geo_pair or len({nearby_geo, location_geo})==1: continue
            geo_pair.append({location_geo, nearby_geo})
            relationship = Relation(rcc=searcher.get_rcc(location_geo, nearby_geo), distance=searcher.distance(location_geo, nearby_geo), azimuth=searcher.calculate_azimuth(location_geo, nearby_geo))
            nearby_area = Area(name=nearby_name, tag=nearby_tag, geometry=str(nearby_geo))
            nearby[-1].nearby.append(Nearby(relationship=relationship, nearby_area=nearby_area))
            triplets.append(f"<<{nearby[-1].target_area}>——<{nearby[-1].nearby[-1].relationship}>——<{nearby[-1].nearby[-1].nearby_area}>>")
    if len(str(triplets))>word_num: raise NodeInterrupt(f'{name}附近的地理实体太多。请重新输入指令')
    return triplets

class pos_nearby_input(BaseModel):
    pos: list[float] = Field(description="Position of the location")
@tool(args_schema=pos_nearby_input)
def pos_nearby_tool(pos: list[float]) -> str:
    '''A tool that obtains the nearby geometries from the position'''
    class Area(BaseModel):
        name: Optional[str]
        tag: str
        geometry: str
    class Relation(BaseModel):
        rcc: str
        distance: float
        azimuth: float
    class Nearby(BaseModel):
        relationship: Relation
        nearby_area: Area
    location_geo = Point(pos)
    nearby_features = searcher.get_nearby_feature(location_geo, scale)
    if len(nearby_features)==0:
        raise NodeInterrupt(f'未找到{pos}附近的地理实体。请重新输入')
    nearby = []
    triplets = []
    geo_pair = []
    for _, nearby_feature in nearby_features.iterrows():
        nearby_feature = nearby_feature.to_list()
        nearby_name = nearby_feature[0]
        nearby_tag = nearby_feature[1]
        nearby_geo = nearby_feature[2]

        if {location_geo, nearby_geo} in geo_pair: continue
        geo_pair.append({location_geo, nearby_geo})

        relationship = Relation(rcc=searcher.get_rcc(location_geo, nearby_geo), distance=searcher.distance(location_geo, nearby_geo), azimuth=searcher.calculate_azimuth(location_geo, nearby_geo))
        nearby_area = Area(name=nearby_name, tag=nearby_tag, geometry=str(nearby_geo))
        nearby.append(Nearby(relationship=relationship, nearby_area=nearby_area))
        triplets.append(f"<<{location_geo}>——<{nearby[-1].relationship}>——<{nearby[-1].nearby_area}>>")
    if len(str(triplets))>word_num: raise NodeInterrupt(f'{pos}附近的地理实体太多。请重新输入指令')
    return triplets






class triplets_input(BaseModel):
    # gdf: gpd.GeoDataFrame = Field(description="Set of some geometries")  # 不能有gpd类型
    gdf: str = Field(description="Set of some geometries")  # 不能有gpd类型
@tool(args_schema=triplets_input)
def triplets_tool(gdf: str) -> Tuple[str, str, str]:
    '''A tool that calculates the relationship between any pair of geometries within a set'''
    return 


# ============================================================================


class get_polygon_centroid_input(BaseModel):
    polygon: list = Field(description="Outline of the polygon, list of points")
@tool(args_schema=get_polygon_centroid_input)
def polygon_centroid_tool(polygon: list) -> str:
    '''A tool that calculates the centroid of the polygon'''
    try: 
        polygon = Polygon(polygon[0])
    except:
        polygon = Polygon(polygon)
    return str(polygon.centroid)

class get_linestring_centroid_input(BaseModel):
    linestring: list[list[float]] = Field(description="Outline of the linestring, list of points")
@tool(args_schema=get_linestring_centroid_input)
def linestring_centroid_tool(linestring: list[list[float]]) -> str:
    '''A tool that calculates the centroid of the linestring'''
    linestring = LineString(linestring)
    return str(linestring.centroid)



class find_intersection_input(BaseModel):
    azimuth: float = Field(description="the azimuth of target direction, from north, clockwise, in degrees")
    polygon: list = Field(description="the vertices of the polygon")
@tool(args_schema=find_intersection_input)
def find_intersection_tool(azimuth: float, polygon: list) -> list[float]:
    '''A tool that finds the intersection of the line from the centroid with a side of the polygon in a certain azimuth'''
    if type(polygon[0])==tuple or type(polygon[0])==list:
        polygon = Polygon(polygon)
    else:
        polygon = Polygon(polygon[0])
    theta = np.radians((90-azimuth)%360)
    centroid = polygon.centroid
    
    # 从质心出发，沿指定方向创建一条射线
    # 选择一个足够远的距离，确保射线与多边形相交
    d = 1000  # 假设射线长度足够远
    end_point = (centroid.x + d * np.cos(theta), centroid.y + d * np.sin(theta))
    ray = LineString([centroid, end_point])
    
    # 计算射线与多边形的交点
    intersection = ray.intersection(polygon)
    
    # 如果没有交点，返回 None
    if intersection.is_empty:
        return None
    
    # 如果交点是 MultiPoint，选择距离质心最近的点
    if intersection.boundary.geom_type == 'MultiPoint':
        max_distance = 0
        farthest_point = None
        for p in intersection.boundary.geoms:  # 遍历 MultiPoint 中的每个点
            d = distance(lonlat(centroid.x, centroid.y), lonlat(p.x, p.y)).m
            if d > max_distance:
                max_distance = d
                farthest_point = p
        farthest_point = farthest_point
    else:
        farthest_point = intersection
    
    return farthest_point.x, farthest_point.y


# ============================================================================
class think_input(BaseModel):
    thought: str = Field(description="A thought to think about.")

@tool(args_schema=think_input)
def think_tool(thought: str) -> str:
    '''Tool to think about something. It will not obtain new information or change the database, but just append the thought to the log. Use it when complex reasoning or some cache memory is needed.'''
    return thought










# 总结当前模块中的变量
# import sys
# module_dict = vars(sys.modules[__name__])
# name_and_function = {name: obj for name, obj in module_dict.items() if callable(obj) and name.startswith("tool_")}
# toolNames = list(name_and_function.keys())
# tools = list(name_and_function.values())
