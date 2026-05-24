from pydantic import BaseModel, Field
from typing import Optional
from typing_extensions import Annotated
from scripts.map_search import searcher
from langchain.tools import tool
from langgraph.errors import NodeInterrupt
from shapely import get_coordinates

equip_infos = [
    {
        'ID': 'FTK_HJ10_BP_C__534CE6B74C0C438792B828A9F4CB6ACA', 
        'Name': '红箭10反坦克导弹发射车',  # 东北侧
        'TableID': 11691, 
        'TeamID': 0, 
        'Location': {'X': 121.149043, 'Y': 24.904791, 'Z': 6998.17683602868}
    },
    {
        'ID': 'M1A2_BP_C__11A97C0346A77C166E467BA4FA88D1F5', 
        'Name': 'M1A2主战坦克（美）',  # ×
        'TableID': 11960, 
        'TeamID': 1, 
        'Location': {'X': 121.14091565669362, 'Y': 24.905224493934433, 'Z': 6997.89433266236}
    },
    {
        'ID': 'M1A2_BP_C__11A97C0346A77C166E467BA4FA88D1F5', 
        'Name': 'M1A1主战坦克（美）', # 西北侧
        'TableID': 11960, 
        'TeamID': 0, 
        'Location': {'X': 121.148904, 'Y': 24.904839, 'Z': 6997.89433266236}
    },
    {
        'ID': 'M1A2_BP_C__11A97C0346A77C166E467BA4FA88D1F5', 
        'Name': 'M1A1主战坦克（美）', # 西北侧
        'TableID': 11960, 
        'TeamID': 0, 
        'Location': {'X': 121.148905, 'Y': 24.904839, 'Z': 6997.89433266236}
    },
    {
        'ID': 'M1A2_BP_C__11A97C0346A77C166E467BA4FA88D1F5', 
        'Name': '99A主战坦克__1', # 西南侧
        'TableID': 11960, 
        'TeamID': 0, 
        'Location': {'X': 121.148891, 'Y': 24.904611, 'Z': 6997.89433266236}
    },
    {
        'ID': 'M1A2_BP_C__11A97C0346A77C166E467BA4FA88D1F5', 
        'Name': '99A主战坦克__2', # 西南侧
        'TableID': 11960, 
        'TeamID': 1, 
        'Location': {'X': 121.148891, 'Y': 24.904612, 'Z': 6997.89433266236}
    },
    {
        'ID': 'M1A2_BP_C__11A97C0346A77C166E467BA4FA88D1F5', 
        'Name': '99A主战坦克__3', # 西南侧
        'TableID': 11960, 
        'TeamID': 0, 
        'Location': {'X': 121.148891, 'Y': 24.904613, 'Z': 6997.89433266236}
    },
    {
        'ID': 'M1A2_BP_C__11A97C0346A77C166E467BA4FA88D1F5', 
        'Name': '59式中型坦克', # 东南侧
        'TableID': 11960, 
        'TeamID': 0, 
        'Location': {'X': 121.149035, 'Y': 24.904669, 'Z': 6997.89433266236}
    }
]
scale = 30
word_limit = 50000
class nearby_entities_input(BaseModel):
    loc_name: Annotated[str, Field(description="Name of the location")]
@tool(args_schema=nearby_entities_input)
def get_nearby_entities(loc_name: str) -> list:
    '''Tool to obtain the nearby entities using the location name'''

    class Area(BaseModel):
        name: Optional[str]
        tag: str
        geometry: str
    class Equip(BaseModel):
        name: str
        team: str
        id: Optional[str]
        pos: str
    class Relation(BaseModel):
        distance: float
        azimuth: float
        rcc: str
    class Nearby(BaseModel):
        relationship: Relation
        nearby_entity: Equip
    class GeoInfo(BaseModel):
        target_area: Area
        nearby: Optional[list[Nearby]]=[]

    location_feature = searcher.similar_match_geoentities(loc_name)
    if len(location_feature)==0: 
        raise NodeInterrupt(f'未找到{loc_name}。请重新输入')
    nearby = []
    triplets = []
    geo_pair = []
    for location_feature in location_feature:
        location_name = location_feature[0]
        location_tag = location_feature[1]
        location_geo = location_feature[2]
        nearby_features = searcher.get_nearby_equipment(location_geo, scale, equip_infos)
        nearby.append(GeoInfo(target_area=Area(name=location_name, tag=location_tag, geometry=str(location_geo))))
        for _, nearby_feature in nearby_features.iterrows():
            nearby_feature = nearby_feature.to_list()
            nearby_id = nearby_feature[0]
            nearby_name = nearby_feature[1]
            nearby_team = '红军' if nearby_feature[3]==0 else '蓝军'
            nearby_geo = nearby_feature[4]
            if {location_geo, nearby_geo} in geo_pair or len({nearby_geo, location_geo})==1: continue
            geo_pair.append({location_geo, nearby_geo})
            relationship = Relation(rcc=searcher.get_rcc(location_geo, nearby_geo), distance=searcher.distance(location_geo, nearby_geo), azimuth=searcher.calculate_azimuth(location_geo, nearby_geo))
            nearby_equip = Equip(id=nearby_id, name=nearby_name, team=nearby_team, pos=str(get_coordinates(nearby_geo).tolist()[0]))
            nearby[-1].nearby.append(Nearby(relationship=relationship, nearby_entity=nearby_equip))
            # triplets.append(f"({nearby[-1].target_area}, {nearby[-1].nearby[-1].relationship}, {nearby[-1].nearby[-1].nearby_entity})")
            triplets.append(f"(<{nearby[-1].target_area.name}, {nearby[-1].target_area.tag}>, {nearby[-1].nearby[-1].relationship}, <{nearby[-1].nearby[-1].nearby_entity.name}, {nearby[-1].nearby[-1].nearby_entity.team}>)")
    if len(str(triplets))>word_limit: raise NodeInterrupt(f'{loc_name}附近的地理实体太多。请重新输入指令')
    result = f"\n=== 找到{loc_name}附近兵力实体 ===\n"+"\n".join(triplets)
    return result

class entity_input(BaseModel):
    name: Annotated[str, Field(description="Name of the location")]
@tool(args_schema=entity_input)
def get_entity(name: str) -> str:
    '''Tool to get the info of target entity using name'''
    similar_entities = searcher.similar_match_simentities(name, equip_infos)
    lines = []
    for row in similar_entities:
        team = '红军' if row['TeamID']==0 else '蓝军'
        line = f"{row['Name']}，隶属{team}，坐标{get_coordinates(row['geometry']).tolist()[0]}，ID: {row['ID']}，TableID: {row['TableID']}。"
        lines.append(line)
    result = "\n=== 找到如下兵力实体 ===\n"+"\n".join(lines)
    return result