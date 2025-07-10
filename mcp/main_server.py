import sys
path = '/home/root/coorGen'  # 导入问题都是sys.path不对的问题
sys.path.append(path)
import math
import uuid

from pydantic import BaseModel, Field
from typing import Optional, Annotated
from scripts.map_search import searcher
from scripts.llm_load import llm_gpt4omini, llm_deepseek
from scripts.workflow_react_no_struct_async import react_agent
# from scripts.workflow_react_async import react_agent
from langgraph.errors import NodeInterrupt
from mcp.server.fastmcp import FastMCP
from geopy.distance import distance, lonlat, geodesic
from pydantic import BaseModel, Field
from typing import Optional, Annotated
from langchain.tools import tool
from scripts.map_search import searcher
from agent_retrieve.agent import make_graph as make_graph_retrieve

mcp = FastMCP("Main")

scale = 30
word_limit = 50000

@mcp.tool()
def get_nearby_geoentities(loc_name: Annotated[str, Field(description="Name of the location")]) -> list:
    '''Tool to obtain nearby geoentities using location name'''

    # (修改点)
    class GeoEntity(BaseModel):
        name: Optional[str]
        tag: str
        geometry: str
    class Relation(BaseModel):
        rcc: str
        distance: float
        azimuth: float
    class Nearby(BaseModel):
        relationship: Relation
        nearby_geoentity: GeoEntity
    class Info(BaseModel):
        target_geoentity: GeoEntity
        nearby: Optional[list[Nearby]]=[]
    # (/修改点)
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
        nearby.append(Info(target_geoentity=GeoEntity(name=location_name, tag=location_tag, geometry=str(location_geo))))
        # (修改点)
        nearby_features = searcher.get_nearby_geoentities(location_geo, scale)
        # (/修改点)
        for _, nearby_feature in nearby_features.iterrows():
            nearby_feature = nearby_feature.to_list()
            # (修改点)
            nearby_name = nearby_feature[0]
            nearby_tag = nearby_feature[1]
            nearby_geo = nearby_feature[2]
            # (/修改点)
            if {location_geo, nearby_geo} in geo_pair or len({nearby_geo, location_geo})==1: continue
            geo_pair.append({location_geo, nearby_geo})
            relationship = Relation(rcc=searcher.get_rcc(location_geo, nearby_geo), distance=searcher.distance(location_geo, nearby_geo), azimuth=searcher.calculate_azimuth(location_geo, nearby_geo))
            # (修改点)
            nearby_equip = GeoEntity(name=nearby_name, tag=nearby_tag, geometry=str(nearby_geo))
            nearby[-1].nearby.append(Nearby(relationship=relationship, nearby_geoentity=nearby_equip))
            # (/修改点)
            # (修改点)
            triplets.append(f"({nearby[-1].target_geoentity}, {nearby[-1].nearby[-1].relationship}, {nearby[-1].nearby[-1].nearby_geoentity})")
            # (/修改点)
    if len(str(triplets))>word_limit: raise NodeInterrupt(f'{loc_name}附近的地理实体太多。请重新输入指令')
    result = f"=== 找到{loc_name}附近地理实体 ===\n"+"\n".join(triplets)
    return result

@mcp.tool()
async def get_deploy_rules(name: Annotated[str, Field(description="Name of the simentity")]) -> str:
    '''Tool to get deployment rules of simentity using its name'''

    rules = await llm_gpt4omini.ainvoke(f"请基于下列兵力实体帮我生成3条部署规则: {name}")
    result = f"=== {name}有如下部署规则 ===\n"+rules.content
    # retrieve_graph = await make_graph_retrieve(False)
    # graph_input = {"messages": [('user', f"请帮我从数据库查找下列兵力实体的部署规则: {name}")]}
    # rules = await retrieve_graph.ainvoke(graph_input)
    # result = f"=== {name}有如下部署规则 ===\n"+str(rules.get('final_response'))
    return result

# @mcp.tool()
def get_geoentity(name: Annotated[str, Field(description="Name of the geoentity")]) -> str:
    '''Tool to get the info of target geoentity using name'''

    similar_entities = searcher.similar_match_geoentities(name)
    lines = []
    for row in similar_entities:
        line = f"{row['name']}，tag: {row['tags']}，几何信息{str(row['geometry'])}。"
        lines.append(line)
    result = "=== 找到如下地理实体 ===\n"+"\n".join(lines)
    return result

# # @mcp.tool()
# def formation_polygon(
#     coord: Annotated[list[float], Field(description="Coordinates of central point of formation")], 
#     n: Annotated[int, Field(description="Number of formation")], 
#     d: Annotated[float, Field(description="Distance of two vertexes")]
#     ) -> list[list[float]]:
#     """Tool to calculate the regular polygon formation based on the centroid point"""

#     formation = []
#     angle_in_degrees = 360 / n  # 计算张角
#     angle_in_radians = math.radians(angle_in_degrees)
#     l = d/2/math.sin(angle_in_radians/2)  # 计算腰长
#     for i in range(n):
#         azimuth = angle_in_degrees * i  # 计算方位角
#         py, px, _ = distance(meters=l).destination(lonlat(coord[0], coord[1]), bearing=azimuth)
#         formation.append([px, py])
#     if n==3:
#         f_name = '三角形'
#     elif n==4:
#         f_name = '方形'
#     else:
#         f_name = f'{n}边形'
#     result = f"\n=== 获取{f_name}下各兵力实体坐标 ===\n"+"\n".join(formation)
#     return result

# # @mcp.tool()
# def formation_line(
#     coord: Annotated[list[float], Field(description="Coordinates of central point of formation")], 
#     n: Annotated[int, Field(description="Number of formation")], 
#     d: Annotated[float, Field(description="Distance of two ajacent vertexes")],
#     angle: Annotated[float, Field(description="Angle from true north, clockwise (-180~180)")]
#     ) -> list[list[float]]:
#     """Tool that calculates the line formation based on the central point"""

#     formation = []
#     new_point1 = coord
#     new_point2 = coord
#     if n%2==0:
#         for i in range(n//2):
#             dd = d/2 if i==0 else d
#             new_point1 = distance(meters=dd).destination(lonlat(new_point1[0], new_point1[1]), bearing=angle)
#             new_point2 = distance(meters=dd).destination(lonlat(new_point2[0], new_point2[1]), bearing=angle+180)
#             formation.extend([new_point1, new_point2])
#     else:
#         formation.append(coord)
#         for i in range(n//2):
#             new_point1 = distance(meters=d).destination(lonlat(new_point1[0], new_point1[1]), bearing=angle)
#             new_point2 = distance(meters=d).destination(lonlat(new_point2[0], new_point2[1]), bearing=angle+180)
#             formation.extend([new_point1, new_point2])
#     return formation


# Args:
#     coord: Coordinates of current point
#     azimuth: Azimuth to current point, in degree
#     d: Distance to current point, in meters

# @tool(args_schema=GetNewPoint)
@mcp.tool(
    annotations={
        "idempotentHint": True,
    }
)
def get_new_point(
    coord: Annotated[list[float], Field(description="Coordinates of current point", examples=[[[114.31, 30.57], [114.32, 30.57]]])],
    azimuth: Annotated[float|int, Field(description="Azimuth to current point, in degree", examples=[90, 180])],
    d: Annotated[float|int, Field(description="Distance to current point, in meters", examples=[10, 20])]
) -> str:
    """Tool that calculates the new point based on the current point"""

    py, px, _ = geodesic(meters=d).destination(lonlat(coord[0], coord[1]), bearing=azimuth)
    return f"从{coord}出发的方位角{azimuth}方向距离{d}米处的坐标为: "+str([px, py])

@mcp.tool()
async def get_formation(
    name: Annotated[str, Field(description="Name of the formation")],
    n: Annotated[int, Field(description="Number of formation")],
    d: Annotated[float, Field(description="Distance of every two vertexes, in meters")],
    desc: Annotated[str, Field('空', description="Other description of the formation")],
    coord: Annotated[list[float], Field(description="Coordinates of central point of formation")],
    ) -> str:
    """Tool to get coordinates of simentities in formation based on the formation name"""

    prompt = f"请基于用户给出的队形描述，选择合适的队形工具计算队形中各兵力实体坐标，使用structure输出结果。"
    user_input = f'{name}，中心点在{coord}，部署数量{n}，两两间距{d}米，其他要求为{desc}'
    graph_input = {"messages": [('user', user_input)]}
    # config = {
    #     "configurable": {
    #         "thread_id": uuid.uuid4(),
    #     }
    # }
    graph = react_agent(
        tools=[searcher.formation_polygon.__func__, searcher.formation_line.__func__],
        prompt=prompt,
        memory=False
    )
    values_output = await graph.ainvoke(graph_input)
    # values_output = await stream_output_graph(graph, graph_input, config, 'get_formation')
    return f'符合"{user_input}"的队形为: {values_output.get("final_response")}'

    # async for event in react_agent(
    #     tools=[searcher.formation_polygon.__func__, searcher.formation_line.__func__],
    #     prompt=prompt,
    # ).astream({'messages': [('user', user_input)]}, stream_mode='values'):
        
    #     turn += 1
    #     messages = event.get('messages')
    #     for message in messages[old_len:]:
    #         message.pretty_print()
    #     print("----")
    #     old_len = len(messages)
    #     print(f'\n==={user_input}=== 第{turn}次运行')

    # return f'符合"{user_input}"的队形为: {event.get('final_response')}'

if __name__ == "__main__":
    mcp.run(transport="stdio")
    # mcp.run(transport="streamable-http")