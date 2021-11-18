# -*- coding: utf-8 -*-
import datetime
import os
import subprocess
from utils import FileUtils
from config import Room, GlobalConfig, RoomConfig, LiveInfo
import logging

video_cache = './cache/videos.json'
time_cache = './cache/times.json'


class Processor:
    origin_videos: list[str]
    process_videos: list[str]
    live_info: LiveInfo
    config: Room
    recorder_path: str
    process_path: str
    isDocker: bool

    def __init__(self, event_data: dict, global_config: GlobalConfig):
        self.live_info = LiveInfo(event_data=event_data)
        self.origin_videos = []
        self.process_videos = []
        self.recorder_path = global_config.recorder_dir
        self.process_path = global_config.process_dir
        self.isDocker = global_config.isDocker
        rooms = FileUtils.ReadJson(time_cache)
        self.live_info.start_time = datetime.datetime.fromtimestamp(rooms[str(self.live_info.room_id)])

    @staticmethod
    def live_start(room_id: int, start_time: datetime) -> None:
        """ 直播开始

        :param room_id: 直播间号
        :param start_time: 直播开始时间
        :return:
        """
        rooms = FileUtils.ReadJson(time_cache)
        room_id = str(room_id)
        rooms[room_id] = start_time.timestamp()
        FileUtils.WriteDict(obj=rooms, path=time_cache)

    @staticmethod
    def file_open(room_id: int, file_path: str) -> None:
        """ 录播文件写入

        :param room_id: 直播间号
        :param file_path: 录播文件路径(录播姬提供)
        :return:
        """
        rooms = FileUtils.ReadJson(video_cache)
        room_id = str(room_id)  # 防止取出json时房间号为string而导致不匹配
        file_path = file_path.replace('.flv', '')  # 去掉文件格式
        room = rooms.get(room_id)
        if room is None:
            rooms[room_id] = []
            room = rooms[room_id]
        room.append(file_path)
        FileUtils.WriteDict(path=video_cache, obj=rooms)

    def live_end(self) -> None:
        """ 直播结束

        :return:
        """
        rooms = FileUtils.ReadJson(video_cache)
        self.origin_videos = rooms[str(self.live_info.room_id)]
        # 清空
        rooms[str(self.live_info.room_id)] = []
        FileUtils.WriteDict(path=video_cache, obj=rooms)
        # 将录播文件的相对目录转为绝对目录
        for i in range(len(self.origin_videos)):
            self.origin_videos[i] = os.path.join(self.process_path, self.origin_videos[i])

    def check_if_need_process(self, configs: RoomConfig) -> bool:
        """ 检查是否需要处理

        :param configs: room-config.yml数据
        :return: 是否需要处理
        """
        # 长号短号均需要匹配
        self.config = configs.get_room_by_id(room_id=self.live_info.room_id, short_id=self.live_info.short_id)
        if self.config is None:  # 直播间号码不匹配
            logging.info(f'room {self.live_info.room_id} does not need processing because it\'s not in the room list')
            return False
        # 匹配额外条件
        conditions = self.config.list_proper_conditions(live_info=self.live_info)
        for condition in conditions:
            if not condition.process:
                logging.info(f'room {self.live_info.room_id} does not need processing because of the room config')
                logging.debug(f'details:  item: {condition.item}, regexp: {condition.regexp}')
                return False
        return True

    def prepare(self) -> None:
        """ 准备工作

        :return:
        """
        # copy files to process dir
        target_dir = os.path.join(self.process_path, self.live_info.session_id)
        logging.info(f'moving files to dictionary {target_dir}')
        self.process_videos = FileUtils.CopyFiles(files=self.origin_videos, target=target_dir, types=['flv', 'xml'])

    async def make_damaku(self) -> None:
        """ 处理弹幕文件

        :return:
        """
        if self.isDocker:
            exe_path = '/DanmakuFactory/DanmakuFactory'
        else:
            exe_path = 'resources\\DanmakuFactory.exe'
        # set shell command
        command = ''
        for record in self.process_videos:
            command += f'{exe_path} -o "{record}.ass" -i "{record}.xml" -d 50 -S 55 --ignore-warnings\n'
        logging.debug('(danmaku factory) command: %s' % command)
        # run shell command
        thread = subprocess.Popen(args=command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdoutdata, stderrdata = thread.communicate(input=None)
        logging.debug('std out data: %s\nstd err data: %s' % (stdoutdata, stderrdata))
        # check if there are xml files without appropriate ass files
        for record in self.process_videos:
            if not os.path.exists(f'{record}.ass'):
                logging.warning(f'file {record}.xml does not have appropriate ass file')

    async def composite(self) -> list[str]:
        """ 合成弹幕和源视频

        :return: 处理后的视频文件
        """
        if self.isDocker:
            exe_path = 'ffmpeg'
        else:
            exe_path = 'resources\\ffmpeg'
        # set shell command
        command = ''
        index = 0
        results = []
        for record in self.process_videos:
            index += 1
            output = os.path.join(self.process_path, self.live_info.session_id, f'out{index}.flv')
            results.append(output)
            if os.path.exists(f'{record}.ass'):
                # ass file exists -> use combine command
                command += f'{exe_path} -i "{record}.flv" -vf subtitles="{record}.ass" -vcodec libx264 "{output}"\n'
            else:
                # ass file does not exist -> use copy command
                command += f'{exe_path} -i "{record}.flv" -c copy "{output}"\n'
        logging.debug('(ffmpeg) command: %s' % command)
        # run shell command
        thread = subprocess.Popen(args=command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdoutdata, stderrdata = thread.communicate(input=None)
        logging.debug('std out data: %s\nstd err data: %s' % (stdoutdata, stderrdata))
        return results
