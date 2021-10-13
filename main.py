# -*- coding: utf-8 -*-
from config import GlobalConfig, RoomConfig
from quart import Quart, request, Response
import datetime
from MainThread import ProcessThread
from utils.VideoProcessor import Processor
import logging
import nest_asyncio
nest_asyncio.apply()
app = Quart(__name__)
logging.basicConfig(level=logging.DEBUG)


async def session_started(room_id: int):
    logging.info('received webhook: session started')
    start_time = datetime.datetime.now()
    logging.debug('room: %d  live start at %s' % (room_id, start_time.strftime('%Y-%m-%d %H:%M:%S')))
    Processor.live_start(room_id=room_id, start_time=start_time)


@app.route('/video-process/v2', methods=['POST'])
async def processor():
    json_request = await request.json
    event_type = json_request['EventType']
    event_data = json_request['EventData']
    room_id = event_data['RoomId']
    data = {}
    if event_type == 'SessionStarted':
        data = {
            'room_id': room_id
        }
    elif event_type == 'FileOpening':
        data = {
            'room_id': room_id,
            'event_data': event_data
        }
    elif event_type == 'SessionEnded':
        data = {
            'json_request': json_request,
            'global_config': global_config,
            'room_config': room_config,
            'room_id': room_id
        }
    thread = ProcessThread(name=str(room_id), event_type=event_type, data=data)
    thread.run()
    return Response(response='', status=200)


if __name__ == '__main__':
    config_path = '.\\config-example'
    room_config = RoomConfig(config_path)
    global_config = GlobalConfig(config_path)
    logging.info('application run at port: %d' % global_config.port)
    app.run(port=global_config.port)
