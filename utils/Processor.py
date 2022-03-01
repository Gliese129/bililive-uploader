import datetime
import os
import subprocess
from sanic import Sanic

import consts
from utils import FileUtils
from models import RoomConfig, LiveInfo, GlobalConfig
import logging

from utils.FileUtils import DeleteFiles

app = Sanic.get_app()


class Processor:
    """处理
    Fields:
        origin_stems: 原始视频(绝对路径，无文件后缀)
        process_stems: 处理文件(绝对路径，无文件后缀)
        live_info: 直播信息
        config: 房间配置
        recorder_dir: 录制路径
        process_dir: 处理目录
    """
    origin_stems: list[str]
    process_stems: list[str]
    live_info: LiveInfo
    config: RoomConfig
    recorder_dir: str
    process_dir: str

    def __init__(self, event_data: dict, room_config: RoomConfig):
        global_config: GlobalConfig = app.ctx.global_config
        self.live_info = LiveInfo(event_data=event_data)
        self.origin_stems = []
        self.process_stems = []
        self.recorder_dir = global_config.record_dir
        self.process_dir = os.path.join(global_config.work_dir, self.live_info.session_id)
        start_times = FileUtils.ReadJson(consts.Paths().TIME_CACHE)
        self.live_info.start_time = datetime.datetime.fromtimestamp(start_times[str(self.live_info.room_id)])
        self.config = room_config

    @staticmethod
    def live_start(room_id: int, start_time: datetime):
        """ 直播开始

        :param room_id: 直播间号
        :param start_time: 直播开始时间
        :return:
        """
        rooms = FileUtils.ReadJson(consts.Paths().TIME_CACHE)
        room_id = str(room_id)
        rooms[room_id] = start_time.timestamp()
        FileUtils.WriteDict(obj=rooms, path=consts.Paths().TIME_CACHE)

    @staticmethod
    def file_open(room_id: int, file_path: str):
        """ 录播文件写入

        :param room_id: 直播间号
        :param file_path: 录播文件路径(录播姬提供)
        :return:
        """
        rooms = FileUtils.ReadJson(consts.Paths().VIDEO_CACHE)
        room_id = str(room_id)
        file_path = file_path.replace('.flv', '')
        room = rooms.get(room_id, default=[])
        room.append(file_path)
        rooms[room_id] = room
        FileUtils.WriteDict(path=consts.Paths().VIDEO_CACHE, obj=rooms)

    @staticmethod
    async def run_shell(command: str, prefix: str) -> (str, str):
        """ 执行shell命令

        :param command: 命令
        :param prefix: 调用程序
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

    def live_end(self):
        """ 直播结束

        :return:
        """
        rooms = FileUtils.ReadJson(consts.Paths().VIDEO_CACHE)
        room_id = str(self.live_info.room_id)
        self.origin_stems = rooms[room_id]
        # clear video cache
        rooms[room_id] = []
        FileUtils.WriteDict(path=consts.Paths().VIDEO_CACHE, obj=rooms)
        # relative path ---(if exists)---> absolute path
        self.origin_stems = [os.path.join(self.recorder_dir, video) for video in self.origin_stems if
                              os.path.exists(os.path.join(self.recorder_dir, video + '.flv'))]

    def check_if_need_process(self) -> bool:
        """ 检查是否需要处理

        :return: 是否需要处理
        """
        # check if videos exist
        if len(self.origin_stems) == 0:
            logging.info('[%d] no videos exist', self.live_info.room_id)
            return False
        # check if in room config
        if self.config is None:
            logging.info('[%d] not in room config', self.live_info.room_id)
            return False
        # check extra conditions
        conditions = self.config.list_conditions(self.live_info)
        for condition in conditions:
            if not condition.process:
                logging.info('[%d] forbidden by condition', self.live_info.room_id)
                logging.debug('details:  item: %s, regexp: %s',
                              condition.item, condition.regexp)
                return False
        return True

    async def process(self, multipart: bool = False):
        """ 处理视频

        :param multipart: 是否多part
        """
        # copy files to process dir
        if os.path.exists(self.process_dir):
            raise FileExistsError(f'{self.process_dir} already exists')
        logging.info('[%d] moving files to dictionary %s...', self.live_info.room_id, self.process_dir)
        self.process_stems = FileUtils.CopyFiles(files=self.origin_stems, target=self.process_dir, types=['flv', 'xml'])
        # make danmaku
        logging.info('[%d] converting danmaku files...', self.live_info.room_id)
        await self.make_damaku(multipart)
        # preprocess videos
        if not multipart:
            # combine all videos to record.flv
            logging.info('[%s] combine all videos to record.flv', self.live_info.room_id)
            files = ''
            for video in self.process_stems:
                files += f"file '{video}.flv'\n"
            with open(os.path.join(self.process_dir, 'files.txt'), 'w') as f:
                f.write(files)
            command = f'{consts.Paths().FFMPEG} -f concat -safe 0 -i "{os.path.join(self.process_dir, "files.txt")}" ' \
                      f'-c copy "{os.path.join(self.process_dir, "record.flv")}"'
            await self.run_shell(command=command, prefix='ffmpeg')
            DeleteFiles(file_stems=self.process_stems, types=['flv'])
            self.process_stems = [os.path.join(self.process_dir, 'record')]

    async def make_damaku(self, multipart: bool = False):
        """ 处理弹幕文件

        """
        command = ''
        if multipart:
            # generate ass by each xml file
            for record in self.process_stems:
                command += f'{consts.Paths().DANMAKU_FACTORY} -o "{record}.ass" -i "{record}.xml" -d 50 -S 55 --ignore-warnings\n'
        else:
            # combine all xml files to one ass file
            command = f'{consts.Paths().DANMAKU_FACTORY} -o "{os.path.join(self.process_dir, "record.ass")}" -i '
            for record in self.process_stems:
                command += f'"{record}.xml" '
            command += f'-d 50 -S 55 --ignore-warnings'
        # run shell command
        await self.run_shell(command=command, prefix='danmaku factory')

    async def composite(self) -> list[str]:
        """ 合成弹幕和源视频

        :return: 处理后的视频文件
        """
        # set shell command
        command = ''
        results = []
        for index, record_stem in enumerate(self.process_stems):
            output = os.path.join(self.process_dir, f'out{index + 1}.flv')
            results.append(output)
            if os.path.exists(f'{record_stem}.ass'):
                ass_file = record_stem.replace("\\", "/").replace(":", "\\:") + '.ass'
                command += f'{consts.Paths().FFMPEG} -i "{record_stem}.flv" ' \
                           f'-vf "subtitles=\'{ass_file}\'" -ar 22050 "{output}"\n'
            else:
                command += f'{consts.Paths().FFMPEG} -i "{record_stem}.flv" -c copy "{output}"\n'
        # run shell command
        await self.run_shell(command=command, prefix='ffmpeg')
        logging.info('[%d] processed %d videos', self.live_info.room_id, len(results))
        return results
