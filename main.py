# -*- coding : utf-8 -*-
# coding: utf-8
import asyncio
import urllib

from config import GlobalConfig, RoomConfig
from quart import Quart, request, Response
from MainThread import ProcessThread
import logging
import nest_asyncio
import getopt
import sys
import queue
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.DEBUG)

nest_asyncio.apply()
app = Quart(__name__)
process_executor = ThreadPoolExecutor(thread_name_prefix='process')
upload_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix='upload')
upload_queue = queue.Queue()
upload_loop = asyncio.new_event_loop()


@app.route('/video-process', methods=['POST'])
async def processor():
    room_config = RoomConfig(config_path)
    json_request = await request.get_json()
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
    process_executor.submit(thread.run())
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
        thread = ProcessThread(name=str(f'upload {video_info["live_info"].room_id}'), event_type='RecordUploading',
                               data=data, upload_queue=upload_queue, client_loop=upload_loop)
        upload_executor.submit(thread.run())
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
