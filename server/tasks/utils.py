import asyncio
import logging
import os
from typing import Tuple

from sanic import Sanic

from exceptions import UnknownError
from utils import FileUtils

app = Sanic.get_app()
logger = logging.getLogger('bililive-uploader')

__all__ = ['_merge_videos', '_merge_danmaku', '_convert_danmakus', '_combine_videos_and_danmakus']


async def _run_shell(command: str, execute: str) -> (str, str):
    """ Run shell command and return output.

    :param command: shell command, which application will be replaced with '%APPLICATION'
    :param execute: executable application name
    :return: (stdout, stderr)
    """
    assert execute in ('ffmpeg', 'danmaku factory'), UnknownError(f'Unknown executable application: {execute}')
    if execute == 'ffmpeg':
        app_path = app.config.FFMPEG_PATH
    else:
        app_path = app.config.DANMAKU_FACTORY_PATH

    command = command.replace('%APPLICATION', app_path)
    proc = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE,
                                                 stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    logger.debug(f'command:\n{command}\n------------\nstdout:\n{stdout}\n------------\nstderr:\n{stderr}')
    return stdout.decode(), stderr.decode()


async def _merge_videos(input_files: list, output_folder: str, output_file: str):
    """ Merge videos.

    :param input_files: input files(with folder)
    :param output_folder: output dir
    :param output_file: output file(without folder)
    :return:
    """
    inputs = os.path.join(output_folder, 'files.txt')
    with open(inputs, 'w', encoding='utf-8') as f:
        lines = [f"file '{input_file}'" for input_file in input_files]
        f.write('\n'.join(lines))
    output = os.path.join(output_folder, output_file)
    command = f'%APPLICATION -f concat -safe 0 -i "{inputs}" -c copy "{output}"'
    await _run_shell(command, 'ffmpeg')


async def _merge_danmaku(input_files: list, output_folder: str, output_file: str):
    """ Merge danmaku

    :param input_files: input files(with folder)
    :param output_folder: output dir
    :param output_file: output file(without folder)
    :return:
    """
    inputs = ' '.join([f'"{input_file}"' for input_file in input_files])
    output = os.path.join(output_folder, output_file)
    command = f'%APPLICATION -o "{output}" -i {inputs} -d 50 -S 55 --ignore-warnings'
    await _run_shell(command, 'danmaku factory')


async def _convert_danmakus(files: list[Tuple[str, str]]):
    """ Convert damaku files

    :param files: [(input, output)]
    :return:
    """
    commands = []
    for input_file, output_file in files:
        commands.append(f'%APPLICATION -o "{output_file}" -i "{input_file}" -d 50 -S 55 --ignore-warnings')
    command = ' & '.join(commands)
    await _run_shell(command, 'danmaku factory')


async def _combine_videos_and_danmakus(files: list[Tuple[str, str, str]]):
    """ Combine videos and danmakus

    :param files: [(video, danmaku, output)]
    :return:
    """
    commands = []
    for video, danmaku, output in files:
        if os.path.exists(danmaku):
            commands.append(f'%APPLICATION -i "{video}" -vf "subtitles=\'{danmaku}\'" "{output}"')
        else:
            logger.warning(f'Cannot find danmaku file: {danmaku}, skip it.')
            FileUtils.renameFile(video, output)
    command = ' & '.join(commands)
    await _run_shell(command, 'ffmpeg')
