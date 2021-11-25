# -*- coding: utf-8 -*-
import urllib

from config import GlobalConfig, RoomConfig, LiveInfo
from quart import Quart, request, Response
from MainThread import ProcessThread
import logging
import nest_asyncio
import getopt
import sys
import queue
from MainThread import video_upload
from urllib.parse import urlencode
from flask_executor import Executor

logging.basicConfig(level=logging.DEBUG)

nest_asyncio.apply()
app = Quart(__name__)
executor = Executor(app)
upload_queue = queue.Queue()


@app.route('/video-process', methods=['POST'])
async def processor():
    room_config = RoomConfig(config_path)
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
            'file_path': event_data['RelativePath']
        }
    elif event_type == 'SessionEnded':
        data = {
            'event_data': event_data,
            'global_config': global_config,
            'room_config': room_config,
            'room_id': room_id
        }
    thread = ProcessThread(name=str(f'process {room_id}'), event_type=event_type, data=data, upload_queue=upload_queue)
    executor.submit(thread.run())
    return Response(response='<h3>request received, now processing videos</h3>', status=200)


@app.route('/video-upload', methods=['GET'])
async def uploader():
    sessdata = request.args.get('sessdata')
    access_key = {
        'sessdata': urllib.parse.quote(sessdata),
        'bili_jct': request.args.get('bili_jct'),
        'buvid3': request.args.get('buvid3')
    }
    # copy upload_queue to video_queue
    video_queue = queue.Queue()
    while not upload_queue.empty():
        video_queue.put(upload_queue.get())
    # upload videos in video_queue
    while not video_queue.empty():
        video_info = video_queue.get()
        data = {
            'access_key': access_key,
            'video_info': video_info,
            'global_config': global_config
        }
        await video_upload(upload_queue=upload_queue, **data)
    return Response(response='<h3>request received, now uploading videos</h3>', status=200)


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
    global_config = GlobalConfig(config_path)
    logging.info('application run at port: %d' % global_config.port)
    app.run(host='0.0.0.0', port=global_config.port)
