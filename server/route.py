import asyncio
import logging

from sanic import Sanic, text

from entity import RoomConfig, LiveInfo
from utils.TimeUtils import fromIso

app = Sanic.get_app()
logger = logging.getLogger('bililive-uploader')


@app.route('/')
def index(_):
    return text('This is a test page.')


@app.post('/process')
async def process(request):
    logger.debug('Received request: %s', request.json)

    request_body = request.json
    event_type, event_data = request_body['EventType'], request_body['EventData']
    event_time = fromIso(request_body['EventTimestamp'])
    room_id, short_id = int(event_data['RoomId']), int(event_data['ShortId'])

    if event_type == 'SessionStarted':
        await _dispatch(f'session.start.{room_id}', start_time=event_time)
    elif event_type == 'FileOpening':
        await _dispatch(f'file.open.{room_id}', file_path=event_data['RelativePath'])
    elif event_type == 'SessionEnded':
        work_dir = app.ctx.global_config.work_dir
        room_config = RoomConfig.init(work_dir, room_id, short_id)
        app.ctx.process_pool.submit(asyncio.run,
                                    _dispatch(f'session.end.{room_id}', event_data=event_data, room_config=room_config))

    logger.debug('Request processed.')
    return text('done')


@app.route('/upload')
async def upload(_):
    logger.info('Starting uploading...')

    upload_list = []
    while not app.ctx.upload_queue.empty():
        upload_list.append(app.ctx.upload_queue.get())

    for item in upload_list:
        live_info: LiveInfo = item['live_info']
        asyncio.create_task(
            _dispatch(f'record.upload.{live_info.room_id}',
                      credential=app.ctx.global_config.credential,
                      info=item,
                      room_config=RoomConfig.init(app.ctx.global_config.work_dir, live_info.room_id)
                      ))

    logger.debug('Got %d videos to upload.\n Details:\n %s', len(upload_list), upload_list)
    return text(str(upload_list))


async def _dispatch(route: str, **kwargs):
    await app.dispatch(route, context=kwargs)
