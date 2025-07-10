from tortoise.models import Model
from tortoise import fields

class Tournament(Model):
    # Defining `id` field is optional, it will be defined automatically
    # if you haven't done it yourself
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)


class Event(Model):
    id = fields.IntField(primary_key=True)  # 主键：普通字段 value_list的关系参数必须以普通字段结尾
    name = fields.CharField(max_length=255)
    # References to other models are defined in format
    # "{app_name}.{model_name}" - where {app_name} is defined in the tortoise config
    tournament = fields.ForeignKeyField('models.Tournament', related_name='events')  
    # 外键：
        # 关系字段 prefetch_related的关系参数必须以关系字段结尾
        # 本质是多对一，多的一方加外键，每一个都指向一的一方
    # events为Tournament能看到的反向关联名称
    participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team') 
    # events为Team能看到的反向关联名称
    # through为中间表，可以直接查询中间表，避免额外的join语句


class Team(Model):  # 底层模型不需要定义关联名称，一对多、多对一都是靠其他模型的外键定义
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
