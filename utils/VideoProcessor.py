from utils import FileUtils
from config import Room

cache_path = '../cache/cache.json'


class Processor:
    room_id: int
    videos: list[str]
    session_id: str
    config: Room

    def __init__(self, room: int, session: str, config: Room):
        self.room_id = room
        self.videos = []
        self.session_id = session
        self.config = config

    @staticmethod
    def file_open(room_id: int, file_path: str):
        room_id = str(room_id)  # 防止取出json时房间号为string而导致不匹配
        file_path = file_path.replace('.flv', '')  # 去掉文件格式
        rooms = FileUtils.ReadJson(cache_path)
        room = rooms.get(room_id)
        if room is None:
            rooms[room_id] = []
            room = rooms[room_id]
        room.append(file_path)
        FileUtils.WriteDict(path=cache_path, obj=rooms)

    def live_end(self):
        rooms = FileUtils.ReadJson(cache_path)
        self.videos = rooms[str(self.room_id)]
        rooms[str(self.room_id)] = []
        FileUtils.WriteDict(path=cache_path, obj=rooms)


if __name__ == '__main__':
    Processor(3).live_end()
