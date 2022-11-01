import asyncio
import getopt
import importlib
import logging
import multiprocessing
import sys
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from sanic import Sanic

from entity import BotConfig
from logger import init_logger
from utils import FileUtils

app = Sanic('bililive-uploader')
importlib.import_module('server.route')  # import it to register routes
importlib.import_module('server.tasks')  # import it to register tasks


@app.main_process_start
def init(*_):
    cpu_count = multiprocessing.cpu_count()
    app.ctx.bot_config = bot_config
    app.ctx.process_pool = ThreadPoolExecutor(max_workers=min(cpu_count, bot_config.workers),
                                              thread_name_prefix='process-pool')
    app.ctx.upload_queue = Queue()
    app.config.TIME_CACHE_PATH = './cache/time.json'
    app.config.VIDEO_CACHE_PATH = './cache/videos.json'
    app.config.FFMPEG_PATH = 'ffmpeg' if bot_config.docker else 'resources\\ffmpeg'
    app.config.DANMAKU_FACTORY_PATH = '/DanmakuFactory/DanmakuFactory' \
                                      if bot_config.docker else 'resources\\DanmakuFactory'


@app.on_request
def refresh_config(*_):
    app.ctx.global_config = BotConfig(work_dir)


if __name__ == '__main__':
    try:
        options, args = getopt.getopt(sys.argv[1:], 'w:', ['work-dir='])
        for option, value in options:
            if option in ('-w', '--work-dir'):
                work_dir = value
                break
        else:
            raise getopt.GetoptError('work dir is not specified')
    except getopt.GetoptError as e:
        logging.critical(e)
        sys.exit(2)
    FileUtils.deleteFolder('./cache')
    logger = init_logger(work_dir)
    logger.info('Server started.')
    bot_config = BotConfig(work_dir)
    logger.debug('Work dir: %s\nRecord dir: %s', work_dir, bot_config.rec_dir)
    app.run(host='0.0.0.0', port=bot_config.port, auto_reload=True,
            debug=False, access_log=False)
