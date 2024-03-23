import logging

from bilibili_api import Credential
from sanic import Sanic

from entity import BotConfig, RoomConfig
from exceptions import ChannelNotFoundException, UploadVideosNotFoundException
from utils import FileUtils
from .handler import Upload
from ..upload import bp

logger = logging.getLogger('bililive-uploader')


@bp.signal('record.upload.<room_id:int>')
async def start_upload(room_id: int, room_config: RoomConfig, credential: Credential, info: dict):
    """ 开始上传
    从上传队列中取出视频并上传

    :param room_id
    :param room_config
    :param credential
    :param info: {videos, live_info, folder}
    :return:
    """
    app = Sanic.get_app()
    bot_config: BotConfig = app.ctx.bot_config
    uploader = Upload(room_config=room_config, credential=credential, **info)
    origins = info['origins']
    folder = info['folder']
    try:
        await uploader.upload()
        logger.info('Uploaded successfully.', extra={'room_id': room_id})
        FileUtils.deleteFolder(folder)
        if bot_config.delete:
            files = [origin + extension for origin in origins for extension in ('.flv', '.xml')]
            FileUtils.deleteFiles(files)
    except (ChannelNotFoundException, UploadVideosNotFoundException) as _:
        logger.error('Uploading failed.', extra={'room_id': room_id})
        app.ctx.upload_queue.put(info)
