from pathlib import Path
current_dir = Path.cwd()
import sys, os
sys.path.append(os.getcwd())
from app.models import DeploymentEquipment, DeploymentRule
from tortoise import Tortoise, fields, run_async
from app.models import DeploymentEquipment, DeploymentRule

async def run():
    await Tortoise.init(db_url='sqlite://EquipRules.sqlite3', modules={'models': ['app.models']})
    await Tortoise.generate_schemas()
    
    equipment = await DeploymentEquipment.filter(name='雷达设备A').prefetch_related('deployment_rules').first()
    
    if equipment:
        rules = equipment.deployment_rules
        for rule in rules:
            print(rule)
    else:
        print('未找到指定的装备')
    
    await Tortoise.close_connections()

run_async(run())