# -*- coding: utf-8 -*-
import datetime
import os
import subprocess
from sanic import Sanic
from utils import FileUtils
from entity import RoomConfig, LiveInfo
import logging

video_cache = './cache/videos.json'
time_cache = './cache/times.json'
app = Sanic.get_app()


class Processor:
    origin_videos: list[str]
    process_videos: list[str]
    live_info: LiveInfo
    config: RoomConfig
    recorder_path: str
    process_path: str
    isDocker: bool

    def __init__(self, event_data: dict, room_config: RoomConfig):
        global_config = app.ctx.global_config
        self.live_info = LiveInfo(event_data=event_data)
        self.origin_videos = []
        self.process_videos = []
        self.recorder_path = global_config.recorder_dir
        self.process_path = global_config.process_dir
        self.isDocker = global_config.isDocker
        rooms = FileUtils.ReadJson(time_cache)
        self.live_info.start_time = datetime.datetime.fromtimestamp(rooms[str(self.live_info.room_id)])
        self.config = room_config

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

    @staticmethod
    async def run_shell(command: str, prefix: str) -> (str, str):
        """ 执行shell命令

        :param command: 命令
        :param prefix: 前缀(用于表示是调用哪个的命令)
        :return: stdoutdata或者stderrdata
        """
        logging.debug(f'{prefix} command: {command}')
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdoutdata, stderrdata = process.communicate(input=b'N')
        try:
            stdoutdata = stdoutdata.decode('utf-8')
            stderrdata = stderrdata.decode('utf-8')
        except UnicodeError:
            stdoutdata = stdoutdata.decode()
            stderrdata = stderrdata.decode()
        finally:
            return stdoutdata, stderrdata

    def live_end(self) -> None:
        """ 直播结束

        :return:
        """
        rooms = FileUtils.ReadJson(video_cache)
        self.origin_videos = rooms[str(self.live_info.room_id)]
        # 清空
        rooms[str(self.live_info.room_id)] = []
        FileUtils.WriteDict(path=video_cache, obj=rooms)
        # 将录播文件的相对目录转为绝对目录, 并且过滤不存在的视频
        self.origin_videos = [os.path.join(self.recorder_path, video) for video in self.origin_videos if
                              os.path.exists(os.path.join(self.recorder_path, video + '.flv'))]

    def check_if_need_process(self) -> bool:
        """ 检查是否需要处理

        :return: 是否需要处理
        """
        # 视频列表为空，不需要处理
        if len(self.origin_videos) == 0:
            logging.info(f'room {self.live_info.room_id} does not need processing because it has no videos')
            return False
        # 长号短号均需要匹配
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

    async def prepare(self, multipart: bool = False) -> None:
        """ 准备工作

        :param multipart: 是否多part
        :return:
        """
        # copy files to process dir
        target_dir = os.path.join(self.process_path, self.live_info.session_id)
        if os.path.exists(target_dir):
            raise FileExistsError(f'{target_dir} already exists')
        logging.info(f'[{self.live_info.room_id}] moving files to dictionary {target_dir}')
        self.process_videos = FileUtils.CopyFiles(files=self.origin_videos, target=target_dir, types=['flv', 'xml'])
        if not multipart:
            # not allow multipart -> combine all videos to record.flv
            files = ''
            for video in self.process_videos:
                files += f"file '{video}.flv'\n"
            with open(os.path.join(target_dir, 'files.txt'), 'w') as f:
                if self.isDocker:
                    exe_path = 'ffmpeg'
                else:
                    exe_path = 'resources\\ffmpeg'
                f.write(files)
                command = f'{exe_path} -f concat -i files.txt -c copy record.flv'
                await self.run_shell(command=command, prefix='ffmpeg')
            # remove files.txt
            os.remove(os.path.join(target_dir, 'files.txt'))

        logging.info(f'[{self.live_info.room_id}] converting danmaku files...')
        await self.make_damaku(multipart=multipart)
        if not multipart:
            # make process_videos only contains record
            self.process_videos = [os.path.join(target_dir, 'record')]

    async def make_damaku(self, multipart: bool = False) -> None:
        """ 处理弹幕文件

        :return:
        """
        if self.isDocker:
            exe_path = '/DanmakuFactory/DanmakuFactory'
        else:
            exe_path = 'resources\\DanmakuFactory.exe'
        # set shell command
        command = ''
        if multipart:
            # allow multipart -> convert separately
            for record in self.process_videos:
                command += f'{exe_path} -o "{record}.ass" -i "{record}.xml" -d 50 -S 55 --ignore-warnings\n'
        else:
            # not allow multipart -> convert together
            command = f'{exe_path} -o "record.ass" -i '
            for record in self.process_videos:
                command += f'"{record}.xml" '
            command += f'-d 50 -S 55 --ignore-warnings'
        # run shell command
        await self.run_shell(command=command, prefix='danmaku factory')
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
                ass_file = record.replace("\\", "/").replace(":", "\\:") + '.ass'
                command += f'{exe_path} -i "{record}.flv" -vf "subtitles=\'{ass_file}\'" "{output}"\n'
            else:
                # ass file does not exist -> use copy command
                command += f'{exe_path} -i "{record}.flv" -c copy "{output}"\n'
        # run shell command
        await self.run_shell(command=command, prefix='ffmpeg')
        logging.info(f'[{self.live_info.room_id}] processed {len(results)} videos')
        return results
