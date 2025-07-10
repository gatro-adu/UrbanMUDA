from tortoise import fields, models
from tortoise.models import Model

class DeploymentEquipment(Model):
    """
    部署装备模型
    """
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, description="装备名称")
    type = fields.CharField(max_length=50, description="装备类型")
    status = fields.CharField(max_length=20, description="装备状态")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 多对多关系：一个装备可以关联多个部署规则
    deployment_rules: fields.ManyToManyRelation["DeploymentRule"] = fields.ManyToManyField(
        "models.DeploymentRule",
        related_name="equipments",
        through="deployment_equipment_rules",
        description="关联的部署规则"
    )

    class Meta:
        table = "deployment_equipments"
        table_description = "部署装备表"

    def __str__(self):
        return f"{self.name} ({self.type})"


class DeploymentRule(Model):
    """
    部署规则模型
    """
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, description="规则名称")
    description = fields.TextField(description="规则描述")
    priority = fields.IntField(default=0, description="规则优先级")
    is_active = fields.BooleanField(default=True, description="是否激活")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 多对多关系：一个规则可以关联多个装备
    equipments: fields.ManyToManyRelation[DeploymentEquipment]

    class Meta:
        table = "deployment_rules"
        table_description = "部署规则表"

    def __str__(self):
        return f"{self.name} (Priority: {self.priority})"


model_definition = '''\
class DeploymentEquipment(Model):
    """
    部署装备模型
    """
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, description="装备名称")
    type = fields.CharField(max_length=50, description="装备类型")
    status = fields.CharField(max_length=20, description="装备状态")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 多对多关系：一个装备可以关联多个部署规则
    deployment_rules: fields.ManyToManyRelation["DeploymentRule"] = fields.ManyToManyField(
        "models.DeploymentRule",
        related_name="equipments",
        through="deployment_equipment_rules",
        description="关联的部署规则"
    )

    class Meta:
        table = "deployment_equipments"
        table_description = "部署装备表"

    def __str__(self):
        return f"{{self.name}} ({{self.type}})"


class DeploymentRule(Model):
    """
    部署规则模型
    """
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, description="规则名称")
    description = fields.TextField(description="规则描述")
    priority = fields.IntField(default=0, description="规则优先级")
    is_active = fields.BooleanField(default=True, description="是否激活")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 多对多关系：一个规则可以关联多个装备
    equipments: fields.ManyToManyRelation[DeploymentEquipment]

    class Meta:
        table = "deployment_rules"
        table_description = "部署规则表"

    def __str__(self):
        return f"{{self.name}} (Priority: {{self.priority}})"'''