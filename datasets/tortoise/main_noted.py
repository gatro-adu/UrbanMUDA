from tortoise import Tortoise, run_async
from app.models import Tournament, Event, Team

async def main():
    await Tortoise.init(
        # db_url='postgres://root:1234@localhost:5432/root',  # 默认走tcp/ip，需要密码。而正常psql -U root -d root走peer认证
        db_url='sqlite:///test.db',
        modules={'models': ['app.models']}
    )
    await Tortoise.generate_schemas()
    print("Database schema:")
    # 打印数据库结构
    # for model in Tortoise.apps.get('models').values():
    #     print(f"\nModel: {model.__name__}")
    #     for field_name, field in model._meta.fields_map.items():
    #         print(f"  {field_name}: {field.__class__.__name__}")

    # 打印数据库数据
    for model in Tortoise.apps.get('models').values():
        print(f"\nData in {model.__name__}:")
        for record in await model.all():
            print(record)

    # Creating an instance with .save()
    tournament = Tournament(name='New Tournament')
    await tournament.save()

    # Or with .create()  明显方便很多
    await Event.create(name='Without participants', tournament=tournament)
    event = await Event.create(name='Test', tournament=tournament)  # 可以分步创建模型
    participants = []
    for i in range(2):  # 创建两个team作为参赛队
        team = await Team.create(name='Team {}'.format(i + 1))
        participants.append(team)
    teams = await Team.all()
    print("="*50, "teams", "="*50)
    print(teams)
    tournaments = await Tournament.all().prefetch_related('events__participants')  # 不加flat，则每个元素是以元组形式
    # 预取：并不作为结果返回，而只是预加载

    # participants = [p for t in tournaments for e in t.events for p in e.participants]
    # print("="*50, "participants", "="*50)
    # print([p.name for p in participants])

    # # Many to Many Relationship management is quite straightforward
    # # (there are .remove(...) and .clear() too)
    # await event.participants.add(*participants)  # "many to many"跟集合一样，将多个元素使用add方法添加

    # Iterate over related entities with the async context manager
    # async for team in event.participants:
    #     print(team.name)

    # # The related entities are cached and can be iterated in the synchronous way afterwards
    # for team in event.participants:
    #     pass

    # 本质是从前面的对象中取，后面的语句都是约束条件
    selected_events = await Event.filter(  # 要么是filter，要么是get，要么是all
        participants=getattr(next(iter(participants)), 'id')  # 过滤出participants中id为participants[0].id的event
    ).prefetch_related('participants', 'tournament')  # 没有预取，则每次都要events.participants，获取n次，则查询n次，一共N+1次。而预取可以解决N+1次查询问题（只需一次查询）；预取每个event的participants和tournament
    for event in selected_events:
        print("="*50, "selected_event", "="*50)
        print("tournament: ", event.tournament.name)
        print("participants: ", [t.name for t in event.participants])

    # Prefetch multiple levels of related entities
    l1 = await Team.all().values_list('events__tournament__name', flat=True)  # 两次预取：Team → Event → Tournament
    print("="*50, "l1", "="*50)
    for t in l1:
        print(t)
    # SELECT * FROM team;  -- 获取所有团队
    # SELECT * FROM event WHERE team_id IN (1, 2, 3...); -- 获取所有相关赛事（自动收集所有team_id）
    # SELECT * FROM tournament WHERE id IN (10, 11, 12...);  -- 获取所有相关锦标赛（自动收集所有event的tournament_id）

    # Filter and order by related models too
    l2 = await Tournament.filter(
        events__name__in=['Test', 'Prod']
    ).order_by('-events__participants__name').distinct()  # 本质上就是从events__name__in=['Test', 'Prod']中取tournament
    # distinct：放在最后：基于id去重
    # distinct.values("xx")或者.values("xx").distinct()：基于xx这个键去重
    
    print("="*50, "l2", "="*50)
    print(l2)
    # -表示降序，
    # events__participants__name: 从Tournament→Event→Participant的两级关联
    # distinct: 去重，确保每个tournament只出现一次

    # events__name__in: 关系__关联模型__查询操作符
    # SELECT DISTINCT team.* FROM team
    # INNER JOIN event ON team.id = event.team_id
    # WHERE event.name IN ('Match 1', 'Match 2')

    # 对于关系查询条件，有三种情况
    # 1. 作为filter过滤条件
    # 2. 作为order_by排序条件
    # 3. 作为distinct去重条件

run_async(main())

