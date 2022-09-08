import asyncio

from sanic import Sanic, text

from entity import RoomConfig
from utils.TimeUtils import fromIso

app = Sanic.get_app()


@app.route('/')
def index(_):
    return text('This is a test page.')


@app.post('/process')
async def process(request):
    request_body = request.json
    event_type, event_data = request_body['EventType'], request_body['EventData']
    event_time = fromIso(request_body['EventTimestamp'])
    room_id, short_id = int(event_data['RoomId']), int(event_data['ShortId'])

    if event_type == 'SessionStarted':
        await _dispatch(f'session.start.{room_id}', start_time=event_time)
    elif event_type == 'FileOpening':
        await _dispatch(f'file.open.{room_id}', file_path=event_data['RelativePath'])
    elif event_type == 'SessionEnded':
        room_config = RoomConfig.init(app.ctx.global_config, room_id, short_id)
        app.ctx.process_pool.submit(asyncio.run,
                                    _dispatch(f'session.end.{room_id}', event_data=event_data, room_config=room_config))
    return text('done')


async def _dispatch(route: str, **kwargs):
    await app.dispatch(route, context=kwargs)
