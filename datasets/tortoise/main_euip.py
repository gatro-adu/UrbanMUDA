from tortoise import Tortoise, run_async
from app.models import DeploymentEquipment, DeploymentRule

async def init_db():
    await Tortoise.init(
        db_url='sqlite://EquipRules.sqlite3',
        modules={'models': ['app.models']}  # 如果在单独文件中，替换为模块名
    )
    await Tortoise.generate_schemas()


async def main():
    await init_db()
    
    # 创建一些装备
    equipment1 = await DeploymentEquipment.create(
        name="雷达设备A", 
        type="雷达", 
        status="可用"
    )
    equipment2 = await DeploymentEquipment.create(
        name="通信设备B", 
        type="通信", 
        status="可用"
    )
    
    # 创建一些规则
    rule1 = await DeploymentRule.create(
        name="高优先级部署规则", 
        description="用于紧急情况", 
        priority=1
    )
    rule2 = await DeploymentRule.create(
        name="常规部署规则", 
        description="日常使用", 
        priority=2
    )
    
    # 建立多对多关系
    await rule1.equipments.add(equipment1)
    await rule1.equipments.add(equipment2)  # 规则1适用于装备1和装备2
    await rule2.equipments.add(equipment1)  # 规则2只适用于装备1
    
    # 查询装备关联的规则
    equipment = await DeploymentEquipment.get(id=1).prefetch_related("deployment_rules")
    print(f"装备 {equipment.name} 的规则:")
    for rule in equipment.deployment_rules:
        print(f"- {rule.name}")
    
    # 查询规则关联的装备
    rule = await DeploymentRule.get(id=1).prefetch_related("equipments")
    print(f"\n规则 {rule.name} 适用的装备:")
    for equip in rule.equipments:
        print(f"- {equip.name}")


if __name__ == "__main__":
    run_async(main())