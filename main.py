# -*- coding: utf-8 -*-
import asyncio
import threading

from config import GlobalConfig, RoomConfig
from quart import Quart, request, Response
from MainThread import ProcessThread
import logging
import nest_asyncio
import getopt
import sys
import queue
from MainThread import video_upload

from utils.BilibiliUploader import Uploader

nest_asyncio.apply()
app = Quart(__name__)

logging.basicConfig(level=logging.DEBUG)
upload_queue = queue.Queue()


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
    thread = ProcessThread(name=str(room_id), event_type=event_type, data=data, upload_queue=upload_queue)
    thread.run()
    return Response(response='<h3>request received, now processing videos</h3>', status=200)


@app.route('/video-upload', methods=['GET'])
async def uploader():
    access_key = {
        'sessdata': request.args.get('sessdata'),
        'bili_jct': request.args.get('bili_jct'),
        'buvid3': request.args.get('buvid3')
    }
    while not upload_queue.empty():
        video_info = upload_queue.get()
        thread = threading.Thread(target=video_upload, args=(global_config, video_info, access_key))
        thread.start()
    return Response(response='<h3>request received, now uploading videos</h3>', status=200)


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
