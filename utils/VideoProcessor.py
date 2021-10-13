# -*- coding: utf-8 -*-
import datetime
import os
import subprocess
from utils import FileUtils
from config import Room, GlobalConfig
import re
import logging

video_cache = './cache/videos.json'
time_cache = './cache/times.json'


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
    start_time: datetime

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
        rooms = FileUtils.ReadJson(time_cache)
        self.start_time = datetime.datetime.fromtimestamp(rooms[str(self.room_id)])

    @staticmethod
    def live_start(room_id: int, start_time: datetime):
        rooms = FileUtils.ReadJson(time_cache)
        room_id = str(room_id)
        rooms[room_id] = start_time.timestamp()
        FileUtils.WriteDict(obj=rooms, path=time_cache)

    @staticmethod
    def file_open(room_id: int, file_path: str):
        rooms = FileUtils.ReadJson(video_cache)
        room_id = str(room_id)  # 防止取出json时房间号为string而导致不匹配
        file_path = file_path.replace('.flv', '')  # 去掉文件格式
        room = rooms.get(room_id)
        if room is None:
            rooms[room_id] = []
            room = rooms[room_id]
        room.append(file_path)
        FileUtils.WriteDict(path=video_cache, obj=rooms)

    def live_end(self):
        rooms = FileUtils.ReadJson(video_cache)
        self.origin_videos = rooms[str(self.room_id)]
        # 清空
        rooms[str(self.room_id)] = []
        FileUtils.WriteDict(path=video_cache, obj=rooms)
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

    def prepare(self) -> Room:
        #  将文件转移到处理目录
        target_dir = os.path.join(self.process_path, self.session_id)
        logging.info('moving files to dictionary %s' % target_dir)
        self.process_videos = FileUtils.CopyFiles(files=self.origin_videos, target=target_dir, types=['flv', 'xml'])
        return self.config

    async def make_damaku(self):
        exe_path = 'resources\\DanmakuFactory.exe'
        command = ''
        for record in self.process_videos:
            command += '%s -o "%s.ass" -i "%s.xml" -d 50 -S 55 --ignore-warnings\n' % (exe_path, record, record)
        logging.debug('(danmaku factory) command: %s' % command)
        thread = subprocess\
            .Popen(args=command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdoutdata, stderrdata = thread.communicate(input=None)
        logging.debug('std out data: %s\nstd err data: %s' % (stdoutdata, stderrdata))
        # 检查是否有flv对应的ass，没有则警告
        for record in self.process_videos:
            if not os.path.exists('%s.ass' % record):
                logging.warning('file %s.xml does not have appropriate ass file' % record)

    async def composite(self) -> list[str]:
        exe_path = 'resources\\ffmpeg.exe'
        command = ''
        index = 0
        results = []
        for record in self.process_videos:
            index += 1
            output = os.path.join(self.process_path, self.session_id, 'out%d.flv' % index)
            results.append(output)
            if os.path.exists('%s.ass' % record):
                # 存在，则合并ass和flv
                command += '%s -i "%s.flv" -vf subtitles="%s.ass" -vcodec libx264 "%s"\n' \
                        % (exe_path, record, record, output)
            else:
                # 不存在，则单纯拷贝（保证out文件存在）
                command += '%s -i "%s.flv" -c copy "%s"\n' \
                        % (exe_path, record, output)
        logging.debug('(ffmpeg) command: %s' % command)
        thread = subprocess \
            .Popen(args=command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdoutdata, stderrdata = thread.communicate(input=None)
        logging.debug('std out data: %s\nstd err data: %s' % (stdoutdata, stderrdata))
        return results
