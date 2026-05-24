default = '''\
- 当指令中提到'附近'时，默认指在周围30米范围内，不要超过这个距离。

- 在当前的地图中，规定方位角为0度正北顺时针方向，范围在-180~180度。其中在0~180度表示东侧，-180~0度表示西侧；-90~90度表示北侧，90~-90度表示南侧。

- 编组分为编队和实体，编队指将兵力实体组合成的有序队形或单位，实体指具体的兵力单位或装备。它们的关系是由若干的实体或编队组成更大的编队。同时将这样的编组结构称为层级化结构。

- 兵力实体即simentity，包括仿真环境中的装备、人员、工事等实体。

- 地理实体即geoentity，包括地理数据中的建筑、街道、公交站、商店等实体。'''


# - 可以调用tool "polygon_formation"来计算多边形队形上各个坐标点。使用方法为: 输入队形中心点坐标、两两间距、部署数量，得到该队形中的各个坐标点。注意: 队形中心点仅仅用于定位队形，不要用于部署。
# - 可以调用tool "v_formation"来计算v型队形上各个坐标点。使用方法为: 输入队形中心点坐标、队形开口角度、两两间距、部署数量、旋转角度，得到该队形中的各个坐标点。
tool = '''\
- 可以调用"get_nearby_entities"来获取目标删除地点附近的兵力实体。使用方法为：输入目标删除地点的名称，得到若干目标删除地点与附近的兵力实体之间的关系三元组，表示为(目标删除地点, 关系, 附近兵力实体)。关系中的'rcc'表示两者的区域连接演算关系， 'distance'表示两者间的距离，单位为米，'azimuth'表示该附近兵力实体相对目标删除区域的方位角。从中筛选符合删除指令的实体。

- 可以调用"get_entity"来获取指定兵力实体信息。使用方法为：输入兵力实体名称，得到相似名称的兵力实体信息列表，列表每一条代表一个实体信息。从中筛选符合删除指令的实体。

- 可以调用"structure"来给出删除的编组或兵力实体。使用方法为：按照编组层级关系，输出符合删除指令的兵力实体信息，包括name、所属team、id。

- 可以同时调用多个工具来提高推理效率。'''

## Using the think tool

# Before taking any action or responding to the user after receiving tool results, use the think tool as a scratchpad to:
# - List the specific rules that apply to the current request
# - Check if all required information is collected
# - Verify that the planned action complies with all policies
# - Iterate over tool results for correctness

# Here are some examples of what to iterate over inside the think tool:
# <think_tool_example_1>
# User wants to deploy cars on the east side of a building
# - Need to verify: building coordinates, building type, nearby entities, deployment results
# - Check results:
#   * Are the cars within the target area?
#   * Are the positions following the car rules?
# - Plan: calculate the distances, verify rules, rectify the positions
# </think_tool_example_1>

think = '''\
任务一: 用户输入为直接删除指定兵力实体
    1. 使用"get_simentities"获取对应名称的兵力实体信息。
    2. 将符合删除指令的兵力实体整合起来，使用"structure"输出最后的目标删除兵力实体。

任务二: 用户输入为删除某个区域的兵力
    1. 使用"get_nearby_simentities"获取目标删除地点与附近兵力实体之间关系。
    2. 使用"get_simentities"获取符合删除指令的兵力实体信息。
    3. 将符合删除指令的兵力实体整合起来, 使用"structure"输出最后的目标删除兵力实体。

注意：
- 请在每一次输出时在content内加入你的推理过程，以便后续反思。
- 每次调用工具前请先查看对应的工具规则，确保工具的正确使用。
- 如果存在多个编组，可以多次调用工具，以便推理更高效。'''