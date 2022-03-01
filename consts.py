import os

from models import GlobalConfig
from utils.FileUtils import CopyFile


def Singleton(cls):
    _instance = {}

    def _singleton(*args, **kw):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kw)
        return _instance[cls]

    return _singleton


@Singleton
class Paths:
    VIDEO_CACHE = './cache/videos.json'
    TIME_CACHE = './cache/times.json'
    LIVE2VIDEO = './resources/live2video.json'
    DANMAKU_FACTORY: str
    FFMPEG: str

    def __init__(self, global_config: GlobalConfig):
        if global_config.docker:
            self.DANMAKU_FACTORY = '/DanmakuFactory/DanmakuFactory'
            self.FFMPEG = 'ffmpeg'
        else:
            self.DANMAKU_FACTORY = 'resources\\DanmakuFactory'
            self.FFMPEG = 'resources\\ffmpeg'
        new_live2video = os.path.join(global_config.config_dir, 'live2video.json')
        if not os.path.exists(new_live2video):
            CopyFile(self.LIVE2VIDEO, global_config.config_dir)
        self.LIVE2VIDEO = new_live2video

