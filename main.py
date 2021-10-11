# coding=utf-8
from config import GlobalConfig, RoomConfig
from quart import Quart, request, Response
from utils.VideoProcessor import Processor
import logging

app = Quart(__name__)
logging.basicConfig(level=logging.INFO)


@app.route('/video-process/v2', methods=['POST'])
async def processor():
    json_request = await request.json
    event_type = json_request['EventType']
    event_data = json_request['EventData']
    room_id = event_data['RoomId']
    if event_type == 'FileOpening':
        logging.info('received webhook: file opening')
        file_path = event_data['RelativePath']
        logging.debug('room: %d  file: %s' % (room_id, file_path))
        Processor.file_open(room_id=room_id, file_path=file_path)
        return Response(response='', status=200)
    if event_type == 'SessionEnded':
        logging.info('received webhook: session ended')
        process = Processor(event_data=json_request['EventData'], global_config=global_config)
        process.live_end()
        if process.check_if_need_process(configs=room_config.rooms):  # 需要处理上传
            logging.info('starting processing...')
            process.prepare()
            logging.info('starting converting danmaku files...')
            process.make_damaku()

    return Response(response='', status=200)


if __name__ == '__main__':
    config_path = '.\\config-example'
    room_config = RoomConfig(config_path)
    global_config = GlobalConfig(config_path)
    app.run(port=global_config.port)
