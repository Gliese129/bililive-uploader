# -*- coding: utf-8 -*-
from config import GlobalConfig, RoomConfig
from quart import Quart, request, Response
from MainThread import ProcessThread
import logging
import nest_asyncio
import getopt
import sys
nest_asyncio.apply()
app = Quart(__name__)

logging.basicConfig(level=logging.DEBUG)


@app.route('/video-process', methods=['POST'])
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
    return Response(response='<h3>if you are able to see this page, it means you have run it successfully</h3>'
                    , status=200)


@app.route('/test', methods=['GET', 'POST'])
async def test():
    return Response(response='<h1>This is a network test page</h1>', status=200)


if __name__ == '__main__':
    config_path = ''
    try:
        options, args = getopt.getopt(sys.argv[1:], 'c:', ['config='])
    except Exception as e:
        logging.error(e)
        sys.exit(2)
    for option, value in options:
        if option in ("-c", "--config"):
            config_path = value
            logging.info('set config path: %s' % config_path)
    room_config = RoomConfig(config_path)
    global_config = GlobalConfig(config_path)
    logging.info('application run at port: %d' % global_config.port)
    app.run(host='0.0.0.0', port=global_config.port)
