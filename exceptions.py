import logging
import sys

logger = logging.getLogger('bililive-uploader')


class ConfigNotCompletedException(Exception):
    path: str

    def __init__(self, path: str):
        super().__init__(self)
        self.path = path
        logger.fatal(self)
        sys.exit(1)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.path} not found in config, please check if it's set."


class ChannelNotFoundException(Exception):
    msg: str
    parent_area: str
    sub_area:  str

    def __init__(self, msg='', parent_area= '', sub_area= ''):
        super().__init__()
        self.msg = msg
        self.parent_area = parent_area
        self.sub_area = sub_area
        logger.error(self)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.msg} ' \
               f'{self.parent_area}-{self.sub_area} -> ?'


class UploadVideosNotFoundException(Exception):
    msg: str

    def __init__(self, msg=''):
        super().__init__()
        self.msg = msg
        logger.error(self)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.msg}'


class UnknownError(Exception):
    msg: str

    def __init__(self, msg):
        super().__init__(self)
        self.msg = msg
        logger.error(self)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.msg}\n' \
                f'This error shouldn\'t happen when the bot running normally. ' \
                f'You can ignore it if bot is still running normally.' \
                f'It might happen when bot restarts while bililive recorder recording.' \
                f'If you think it\'s a bug, please report it to the developer.'
