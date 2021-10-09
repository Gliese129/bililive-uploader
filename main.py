# coding=utf-8
from config import GlobalConfig, RoomConfig
from quart import Quart, request, Response
from utils import VideoProcessor
app = Quart(__name__)
room_config = RoomConfig('./resources')
global_config = GlobalConfig('./resources')


@app.route('/video-process/v2', methods=['POST'])
async def processor():
    json_request = await request.json
    event_type = json_request['EventType']
    room_id = json_request['EventData']['RoomId']
    if event_type == 'FileOpen':
        file_path = json_request['EventData']['RelativePath']
        VideoProcessor.Processor.file_open(room_id=room_id, file_path=file_path)
    elif event_type == 'SessionEnd':
        session_id = json_request['EventData']['SessionId']
        process = VideoProcessor.Processor(room=room_id, session=session_id, config=room_config[room_id])
        process.live_end()
    return Response(response='', status=200)


if __name__ == '__main__':
    app.run(port=global_config.port)

