from tortoise import Tortoise, run_async
from app.models import Tournament, Event, Team

async def main():
    await Tortoise.init(
        db_url='postgres://root:1234@localhost:5432/root',
        # db_url='sqlite://db.sqlite3',
        modules={'models': ['app.models']}
    )
    await Tortoise.generate_schemas()

    # Creating an instance with .save()
    tournament = Tournament(name='New Tournament')
    await tournament.save()

    # Or with .create()
    await Event.create(name='Without participants', tournament=tournament)  # 创建没有参赛者的比赛
    event = await Event.create(name='Test', tournament=tournament)  # 创建有参赛者的比赛
    participants = []
    for i in range(2):
        team = await Team.create(name='Team {}'.format(i + 1))
        participants.append(team)

    # Many to Many Relationship management is quite straightforward
    # (there are .remove(...) and .clear() too)
    await event.participants.add(*participants)

    # Iterate over related entities with the async context manager
    async for team in event.participants:
        print(team.name)

    # The related entities are cached and can be iterated in the synchronous way afterwards
    for team in event.participants:
        pass

    # Use prefetch_related to fetch related objects
    selected_events = await Event.filter(
        participants=participants[0].id
    ).prefetch_related('participants', 'tournament')
    for event in selected_events:
        print(event.tournament.name)
        print([t.name for t in event.participants])

    # Prefetch multiple levels of related entities
    teams = await Team.all().prefetch_related('events__tournament')
    print(teams)
    # Filter and order by related models too
    await Tournament.filter(
        events__name__in=['Test', 'Prod']
    ).order_by('-events__participants__name')  # 注意postgres不要没有values的时候在用distinct，否则会报错。一般distinct要结合values使用，意思是基于xx这个键去重

run_async(main())
