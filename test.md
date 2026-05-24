```mermaid
sequenceDiagram
    participant UI as 用户界面
    participant Input as 输入接口
    participant Task as 任务接收与分解
    participant Reasoning as 多轮交互式推理
    participant GeoTool as 地理空间工具链
    participant EquipDB as 装备库
    participant RuleDB as 规则库
    participant EnvMapDB as 环境与地图数据
    participant DeployVis as 部署方案输出与可视化

    %% 表示层交互
    UI->>Input: 接收用户输入
    Input->>Task: 作战想定文本
    Task->>Reasoning: 结构化部署信息
    Reasoning->>EquipDB: 获取相应装备信息
    Reasoning->>RuleDB: 依赖规则库推理
    Reasoning->>GeoTool: 获取地图数据
    GeoTool->>EnvMapDB: (内部调用)
    Reasoning->>DeployVis: (处理后结果)
    DeployVis->>UI: 展示部署方案