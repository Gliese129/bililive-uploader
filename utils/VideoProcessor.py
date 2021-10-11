import os
import subprocess
from utils import FileUtils
from config import Room, GlobalConfig
import re
import logging

cache_path = './cache/cache.json'


class Processor:
    room_id: int
    short_id: int
    origin_videos: list[str]
    process_videos: list[str]
    session_id: str
    title: str
    name: str
    parent_area: str
    child_area: str
    config: Room
    recorder_path: str
    process_path: str

    def __init__(self, event_data: dict, global_config: GlobalConfig):
        self.room_id = event_data['RoomId']
        self.short_id = event_data['ShortId']
        self.session_id = event_data['SessionId']
        self.parent_area = event_data['AreaNameParent']
        self.child_area = event_data['AreaNameChild']
        self.title = event_data['Title']
        self.name = event_data['Name']
        self.origin_videos = []
        self.process_videos = []
        self.recorder_path = global_config.recorder_dir
        self.process_path = global_config.process_dir

    @staticmethod
    def file_open(room_id: int, file_path: str):
        rooms = FileUtils.ReadJson(cache_path)
        room_id = str(room_id)  # 防止取出json时房间号为string而导致不匹配
        file_path = file_path.replace('.flv', '')  # 去掉文件格式
        room = rooms.get(room_id)
        if room is None:
            rooms[room_id] = []
            room = rooms[room_id]
        room.append(file_path)
        FileUtils.WriteDict(path=cache_path, obj=rooms)

    def live_end(self):
        rooms = FileUtils.ReadJson(cache_path)
        self.origin_videos = rooms[str(self.room_id)]
        # 清空
        rooms[str(self.room_id)] = []
        FileUtils.WriteDict(path=cache_path, obj=rooms)
        # video相对目录转为绝对目录
        absolute_videos = []
        for video in self.origin_videos:
            absolute_videos.append(os.path.join(self.recorder_path, video))
        self.origin_videos = absolute_videos

    def check_if_need_process(self, configs: list[Room]) -> bool:
        logging.info('checking if need process...')
        # 长号短号均需要匹配
        flag = False
        for config in configs:
            if self.room_id == config.id or self.short_id == config.id:  # 只要匹配到一个，就返回true
                self.config = config
                flag = True
                break
        if not flag:  # 直播间号码不匹配
            logging.info('room %d does not need processing, reason: not in room list' % self.room_id)
            return False
        # 匹配额外条件
        flag = True
        for condition in self.config.conditions:
            item: str = self.__getattribute__(condition.item)
            if item is None:
                continue
            if re.search(pattern=condition.regexp, string=item) is not None:  # 匹配上正则条件
                self.config.tags.extend(condition.tags)
                flag = flag & condition.process
                if not condition.process:
                    logging.info('room %d does not need processing, reason: forbidden by config' % self.room_id)
                    logging.debug('config details:  item: %s, regexp: %s' % (condition.item, condition.regexp))
        return flag

    def prepare(self):
        #  将文件转移到处理目录
        target_dir = os.path.join(self.process_path, self.session_id)
        self.process_videos = FileUtils.CopyFiles(files=self.origin_videos, target=target_dir, types=['flv', 'xml'])

    def make_damaku(self):
        exe_path = 'resources\\DanmakuFactory.exe'
        command = ''
        for record in self.process_videos:
            command += '%s -o "%s.ass" -i "%s.xml" -d 50 -S 55\n' % (exe_path, record, record)
        print(command)
        thread = subprocess.Popen(args=command, encoding='utf-8', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        thread.wait()
        print(thread.returncode)
