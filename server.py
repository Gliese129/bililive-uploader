# -*- coding : utf-8 -*-
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from models import GlobalConfig, RoomConfig, LiveInfo
import logging
import getopt
import sys
import queue
from sanic import Sanic
from sanic.response import text

from utils.FileUtils import CopyFile

logging.basicConfig(level=logging.DEBUG)

app = Sanic('auto-record-upload')
app.ctx.upload_queue = queue.Queue()


@app.post('/video-process')
async def processor(request):
    app.ctx.global_config = GlobalConfig(work_dir)
    request_body = request.json
    event_type = request_body['EventType']
    event_data = request_body['EventData']
    room_id = int(event_data['RoomId'])

    if event_type == 'SessionStarted':
        logging.info(f'[{room_id}] receive webhook: session started')
        app.add_task(app.dispatch(f'session.start.{room_id}'))
    elif event_type == 'FileOpening':
        logging.info(f'[{room_id}] receive webhook: file opening')
        app.add_task(app.dispatch(f'file.open.{room_id}', context={
            'file_path': event_data['RelativePath'],
        }))
    elif event_type == 'SessionEnded':
        logging.info(f'[{room_id}] receive webhook: session ended')
        app.ctx.process_pool.submit(asyncio.run, app.dispatch(f'session.end.{room_id}', context={
            'event_data': event_data,
            'room_config': RoomConfig.get_config(config_path, room_id)
        }))
    return text('done')


@app.get('/video-upload')
async def uploader(request):
    app.ctx.global_config = GlobalConfig(work_dir)
    logging.info('received request: record upload')
    # copy upload_queue to video_queue
    upload_queue = app.ctx.upload_queue
    video_queue = queue.Queue()
    while not upload_queue.empty():
        video_queue.put(upload_queue.get())
    # upload videos in video_queue
    while not video_queue.empty():
        video_info = video_queue.get()
        live_info: LiveInfo = video_info['live_info']
        credential = app.ctx.global_config.credential
        app.add_task(app.dispatch(f'record.upload.{live_info.room_id}', context={
            'credential': credential,
            'video_info': video_info,
            'room_config': RoomConfig.get_config(config_path, live_info.room_id)
        }))
    return text('done')


if __name__ == '__main__':
    import tasks
    work_dir = ''
    try:
        options, args = getopt.getopt(sys.argv[1:], 'w:', ['work-dir='])
    except Exception as e:
        logging.error(e)
        sys.exit(2)
    for option, value in options:
        if option in ("-w", "--work-dir"):
            work_dir = value
    config_path = os.path.join(work_dir, 'config')
    global_config = GlobalConfig(work_dir)
    CopyFile('./resources/live2video.json', os.path.join(global_config.process_dir, 'config'))
    cpu_count = multiprocessing.cpu_count()
    app.ctx.process_pool = ThreadPoolExecutor(max_workers=min(cpu_count, global_config.workers))
    app.run(host='0.0.0.0', port=global_config.port, debug=False, access_log=False, auto_reload=True)
