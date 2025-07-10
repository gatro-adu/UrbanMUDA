import json
import math
import geopandas as gpd
import pandas as pd

from shapely import LineString,Point,Polygon,MultiPolygon, MultiLineString, wkt
from shapely.geometry.base import BaseGeometry
from difflib import SequenceMatcher
from langchain_core.prompts import ChatPromptTemplate
from geopy.distance import geodesic, lonlat
from geographiclib.geodesic import Geodesic
from scripts.f_tree import similarity
from scripts.similarity import exact_word_match_list
from typing import Annotated, Optional
from pydantic import Field


class JsonMapSearcher:
    def __init__(self, file_path, crs):
        """
        初始化类，加载JSON文件中的数据。
        
        Args:
            file_path (str):JSON文件的路径。
        """
        self.crs = crs
        self.file_path = file_path
        self.map_data = self.__load_data()
        self.names = self.map_data.name[self.map_data.name.notna()].to_list()

    def __load_data(self):
        """
        读取JSON文件并返回数据。
        
        Returns:
            dict:加载的JSON数据。
        """
        # point_file = self.file_path + "Manhattan_points.geojson"
        # point = gpd.read_file(point_file)
        # polygon_file = self.file_path + "Manhattan_buildings.geojson"
        # polygon = gpd.read_file(polygon_file)
        # linestring_file = self.file_path + "Manhattan_lines.geojson"
        # linestring = gpd.read_file(linestring_file)
        # multilinestring_file = self.file_path + "Manhattan_multilinestrings.geojson"
        # multilinestring = gpd.read_file(multilinestring_file)
        # return pd.concat([point, polygon, linestring, multilinestring], ignore_index=True)
        
        map_data = gpd.read_file(self.file_path)
        # map_data = gpd.read_file(self.file_path + "TW_yangmei_complete_zh.geojson")
        return map_data
    
    # def similar_match_geoentities(self, keyword:str)->list:
    #     best = []
    #     for _, feature in self.map_data.iterrows():
    #         if feature['name']:
    #             score = similarity(feature['name'], keyword)
    #             if score>0.6:  # 一般认为大于0.6可视作匹配成功
    #                 x = (feature['name'],feature['tags'],feature['geometry'])
    #                 if (not best) or score==best[0][1]:
    #                     best.append((x,score))
    #                 elif score>best[0][1]:
    #                     best = [(x, score)]
    #     return [b[0] for b in best]


    # def similar_match_simentities(self, keyword, equip_infos)->list:
    #     infos_new = {'ID':[], 'Name':[], 'TableID':[], 'TeamID':[], 'geometry':[]}
    #     for info in equip_infos:
    #         infos_new['ID'].append(info['ID'])
    #         infos_new['Name'].append(info['Name'])
    #         infos_new['TableID'].append(info['TableID'])
    #         infos_new['TeamID'].append(info['TeamID'])
    #         infos_new['geometry'].append(Point(info['Location']['X'], info['Location']['Y']))
    #     gdf_equip = gpd.GeoDataFrame(infos_new, crs="EPSG:4326")
    #     best = []
    #     for _,row in gdf_equip.iterrows():
    #         if row['Name']:
    #             score = similarity(row['Name'], keyword)
    #             if score>0.6:  # 一般认为大于0.6可视作匹配成功
    #                 # x = (feature['Name'],feature['tags'],feature['geometry'])
    #                 x = row
    #                 if (not best) or score==best[0][1]:
    #                     best.append((x, score))
    #                 elif score>best[0][1]:
    #                     best = [(x, score)]
    #     return [b[0] for b in best]

    def similar_match_geoentities(self, keyword:str)->list:
        names = exact_word_match_list(keyword, list(set(self.map_data[self.map_data['name'].notna()]['name'].to_list())))
        return list(self.map_data[self.map_data['name']==names].itertuples(index=False, name=None))
    
    def similar_match_simentities(self, keyword, equip_infos)->list:
        infos_new = {'ID':[], 'Name':[], 'TableID':[], 'TeamID':[], 'geometry':[]}
        for info in equip_infos:
            infos_new['ID'].append(info['ID'])
            infos_new['Name'].append(info['Name'])
            infos_new['TableID'].append(info['TableID'])
            infos_new['TeamID'].append(info['TeamID'])
            infos_new['geometry'].append(Point(info['Location']['X'], info['Location']['Y']))
        gdf_equip = gpd.GeoDataFrame(infos_new, crs="EPSG:4326")
        names = exact_word_match_list(keyword, list(set(gdf_equip[gdf_equip['Name'].notna()]['Name'].to_list())), prefix_check=False)  # 兵力实体采取宽松匹配
        return list(gdf_equip[gdf_equip['Name']==names].itertuples(index=False, name=None))

    def get_nearby_geoentities(self, geo, scale):
        # d = self.map_data.to_crs(epsg=self.crs).hausdorff_distance(gpd.GeoSeries(geo, crs='epsg:4326').to_crs(epsg=self.crs)[0])
        buffer = gpd.GeoSeries(geo, crs='epsg:4326').to_crs(epsg=self.crs).buffer(distance=scale).unary_union
        matched_features = gpd.clip(gdf=self.map_data.to_crs(epsg=self.crs), mask=buffer).to_crs(epsg=4326)

        # d = self.map_data.to_crs(epsg=self.crs).distance(gpd.GeoSeries(geo, crs='epsg:4326').to_crs(epsg=self.crs)[0])
        # d1 = self.map_data[d > 0]
        # d2 = self.map_data[d <= scale]
        # matched_features = d1.merge(d2)
        # matched_features = pd.concat([d1, d2]).drop_duplicates(subset='geometry', keep='first').reset_index(drop=True)
        return matched_features
    
    def get_nearby_simentities(self, geo, scale, equip_infos):
        infos_new = {'ID':[], 'Name':[], 'TableID':[], 'TeamID':[], 'geometry':[]}
        for info in equip_infos:
            infos_new['ID'].append(info['ID'])
            infos_new['Name'].append(info['Name'])
            infos_new['TableID'].append(info['TableID'])
            infos_new['TeamID'].append(info['TeamID'])
            infos_new['geometry'].append(Point(info['Location']['X'], info['Location']['Y']))
        
        gdf_equip = gpd.GeoDataFrame(infos_new, crs="EPSG:4326")
        gdf_buffer = gpd.GeoDataFrame(geometry=gpd.GeoSeries(geo, crs='epsg:4326').to_crs(epsg=self.crs).buffer(distance=scale).to_crs(epsg=4326), crs="EPSG:4326")
        # gdf_equip.sindex.valid_query_predicates: {None, 'crosses', 'covered_by', 'contains_properly', 'contains', 'covers', 'overlaps', 'dwithin', 'touches', 'within', 'intersects'}
        gdf_equip_target_raw = gdf_equip.sjoin(gdf_buffer, how='left', predicate='within')
        gdf_equip_target = gdf_equip_target_raw[gdf_equip_target_raw.index_right.notna()]
        return gdf_equip_target
    
    def get_rcc(self, geo1, geo2):
        if geo1.disjoint(geo2):
            relationship = 'Disconnected (DC)'  # disconnected
        elif geo1.touches(geo2) and not geo1.intersects(geo2):
            relationship = 'Externally Connected (EC)'  # externally connected
        elif geo1.equals(geo2):
            relationship = 'Equal (EQ)'  # equal
        elif geo1.intersects(geo2) and not geo1.within(geo2) and not geo1.contains(geo2):
            relationship = 'Partially Overlapping (PO)'  # partially overlapping
        elif geo1.within(geo2) and geo1.touches(geo2):
            relationship = 'Tangential Proper Part (TPP)'  # proper part  # 不单独考虑正切的情况（即内切或内涵都算PP，被内切或被内涵都算PPi
        elif geo2.within(geo1) and geo1.touches(geo2):
            relationship = 'Tangential Proper Part Inverse (TPPi)'  # proper part inverse
        elif geo1.within(geo2) and not geo1.touches(geo2):
            relationship = 'Non-Tangential Proper Part (NTPP)'  # proper part inverse
        elif geo2.within(geo1) and not geo1.touches(geo2):
            relationship = 'Non-Tangential Proper Part Inverse (NTPPi)'  # proper part inverse
        else: return "Unknown"
        return relationship

    def distance(self, coor1, coor2):
        d = gpd.GeoSeries(coor1, crs='epsg:4326').to_crs(epsg=self.crs).distance(gpd.GeoSeries(coor2, crs='epsg:4326').to_crs(epsg=self.crs)[0])
        return d.to_list()[0]

    def feature_2_geo(self,data) -> BaseGeometry:
        """
        将输入的地图Feature转换为几何图形

        Args:
            data ({'type': 'xx', 'coordinates': [x, y]}):单条地图信息数据
            
        Returns:
            geometry(BaseGeometry):返回一个图形包括(Point,Polygon,LineString,MultiPolygon)
        """
        if data.get('type')=="Point": return Point(data.get('coordinates'))
        elif data.get('type')=="Polygon": return Polygon(*data.get('coordinates'))
        elif data.get('type')=="LineString": return LineString(data.get('coordinates'))
        elif data.get('type')=="MultiLineString": return MultiLineString(data.get('coordinates'))
        else: return
        
    def calculate_azimuth(self, coor1, coor2):
        geodict = Geodesic.WGS84.Inverse(coor1.centroid.y, coor1.centroid.x, coor2.centroid.y, coor2.centroid.x)
        bearing = geodict['azi1']
        # azimuth = bearing%360
        return bearing
    
    def formation_line(
        coord: Annotated[list[float], Field(description="Coordinates of central point of formation")], 
        n: Annotated[int, Field(description="Number of formation")], 
        d: Annotated[float, Field(description="Distance of two ajacent vertexes")],
        angle: Annotated[float, Field(description="Angle from true north, clockwise (-180~180)")]
        ) -> str:
        """Tool to calculate the line formation based on the central point"""

        center_lat, center_lon = coord[1], coord[0]
        formation = []
        half = n // 2
        for i in range(-half, half + 1):
            if n % 2 == 0 and i == 0:
                continue  # Skip the center point for even n

            offset = i * d
            bearing = angle
            point = geodesic(meters=abs(offset)).destination((center_lat, center_lon), bearing + (0 if offset >= 0 else 180))
            formation.append([point.longitude, point.latitude])
        result = f"=== 获得直线队形下各兵力实体坐标 ===\n"+"\n".join([str(f) for f in formation])
        return result
    
    def formation_polygon(
        coord: Annotated[list[float], Field(description="Coordinates of central point of formation")], 
        n: Annotated[int, Field(description="Number of formation")], 
        d: Annotated[float, Field(description="Distance of two vertexes")]
        ) -> str:
        """Tool to calculate the regular polygon formation based on the central point"""

        formation = []
        angle_in_degrees = 360 / n  # 计算张角
        angle_in_radians = math.radians(angle_in_degrees)
        l = d/2/math.sin(angle_in_radians/2)  # 计算腰长
        for i in range(n):
            azimuth = angle_in_degrees * i  # 计算方位角
            py, px, _ = geodesic(meters=l).destination(lonlat(coord[0], coord[1]), bearing=azimuth)
            formation.append([px, py])
        if n==3:
            f_name = '三角形'
        elif n==4:
            f_name = '方形'
        else:
            f_name = f'{n}边形'
        result = f"=== 获得正{f_name}下各兵力实体坐标 ===\n"+"\n".join([str(f) for f in formation])
        return result
    

import sys
path = '/home/root/coorGen'
sys.path.append(path)

file_path_tw = 'map/TW_map/TW_yangmei_complete_zh.geojson'
file_path_nyc = 'map/NYC_map/Manhattan_2_map_complete_Empire State Building.geojson'
searcher = JsonMapSearcher(file_path=file_path_tw, crs=32650) # crs=32650: 台湾；crs=32618: 纽约


# 示例使用
if __name__ == "__main__":
    file_path = './'  # 假设JSON文件路径
    searcher = JsonMapSearcher(file_path)
    result = searcher.fuzzy_match("大成路和中山路")  # exact_match  similar_match  get_nearby_map,get_equipment_location
    # print(result)
