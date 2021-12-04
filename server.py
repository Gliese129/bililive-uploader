# -*- coding : utf-8 -*-
# coding: utf-8
from entity import GlobalConfig, RoomConfig
import logging
import getopt
import sys
import queue
from urllib.parse import quote
from sanic import Sanic
from sanic.response import text

logging.basicConfig(level=logging.DEBUG)

app = Sanic('auto-record-upload')
app.ctx.upload_queue = queue.Queue()


@app.post('/video-process')
async def processor(request):
    from tasks import dispatch_task

    room_config = RoomConfig(config_path)
    request_body = request.json
    event_type = request_body['EventType']
    event_data = request_body['EventData']
    room_id = event_data['RoomId']
    if event_type == 'SessionStarted':
        logging.info(f'({room_id}) received webhook: session started')
        app.add_task(dispatch_task('session-start', data={
            'room_id': room_id,
        }))
    elif event_type == 'FileOpening':
        logging.info(f'({room_id}) received webhook: file opening')
        app.add_task(dispatch_task('file-open', data={
            'room_id': room_id,
            'file_path': event_data['RelativePath'],
        }))
    elif event_type == 'SessionEnded':
        logging.info(f'({room_id}) received webhook: session ended')
        app.add_task(dispatch_task('session-end', data={
            'event_data': event_data,
            'global_config': global_config,
            'room_config': room_config
        }))
    return text('done')


@app.get('/video-upload')
async def uploader(request):
    from tasks import dispatch_task

    sessdata = request.args.get('sessdata')
    access_key = {
        'sessdata': quote(sessdata),
        'bili_jct': request.args.get('bili_jct'),
        'buvid3': request.args.get('buvid3')
    }
    # copy upload_queue to video_queue
    upload_queue = app.ctx.upload_queue
    video_queue = queue.Queue()
    while not upload_queue.empty():
        video_queue.put(upload_queue.get())
    # upload videos in video_queue
    while not video_queue.empty():
        video_info = video_queue.get()
        logging.info('received request: record upload')
        app.add_task(dispatch_task('video-upload', data={
            'access_key': access_key,
            'video_info': video_info,
            'global_config': global_config
        }))
    return text('done')


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
    global_config = GlobalConfig(config_path)
    logging.info('application run at port: %d' % global_config.port)
    app.run(host='0.0.0.0', port=global_config.port, workers=global_config.workers, debug=False, access_log=False)
