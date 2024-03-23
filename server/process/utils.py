import logging
import os
import subprocess
from typing import Tuple

from sanic import Sanic

from exceptions import UnknownError
from utils import FileUtils

app = Sanic.get_app()
logger = logging.getLogger('bililive-uploader')


def run_shell(command: str, executable: str) -> (str, str):
    """ Run command and return output."""
    assert executable in ('ffmpeg', 'danmaku factory'), UnknownError(f'Unknown executable application: {executable}')
    if executable == 'ffmpeg':
        app_path = app.config.FFMPEG_PATH
    else:
        app_path = app.config.DANMAKU_FACTORY_PATH

    command = command.replace('%APPLICATION', app_path)
    logger.debug('Running shell command: \n%s', command)
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) as proc:
        stdout, stderr = proc.communicate()
    logger.debug('stdout:\n%s\n------------\nstderr:\n%s', stdout, stderr)

    return stdout.decode(), stderr.decode()


def merge_videos(input_files: list, output_folder: str, output_file: str):
    """ Merge videos.

    :param input_files: input files(full path)
    :param output_folder: output dir
    :param output_file: output file(only name)
    :return:
    """
    inputs = os.path.join(output_folder, 'files.txt')
    with open(inputs, 'w', encoding='utf-8') as f:
        lines = [f"file '{input_file}'" for input_file in input_files]
        f.write('\n'.join(lines))
    output = os.path.join(output_folder, output_file)
    command = f'%APPLICATION -f concat -safe 0 -i "{inputs}" -c copy "{output}"'
    run_shell(command, 'ffmpeg')


async def merge_danmaku(input_files: list, output_folder: str, output_file: str):
    """ Merge danmaku

    :param input_files: input files(full path)
    :param output_folder: output dir
    :param output_file: output file(only name)
    :return:
    """
    inputs = ' '.join([f'"{input_file}"' for input_file in input_files])
    output = os.path.join(output_folder, output_file)
    command = f'%APPLICATION -o "{output}" -i {inputs} -d 50 -S 55 --ignore-warnings'
    await run_shell(command, 'danmaku factory')


def convert_danmakus(files: list[Tuple[str, str]]):
    """ Convert damaku files

    :param files: [(input, output)]
    :return:
    """
    commands = []
    for input_file, output_file in files:
        input_file, output_file = input_file.replace('\\', '/'), output_file.replace('\\', '/')
        commands.append(f'%APPLICATION -o "{output_file}" -i "{input_file}" -d 50 -S 55 --ignore-warnings')
    command = ' & '.join(commands)
    run_shell(command, 'danmaku factory')


def combine_videos_and_danmakus(files: list[Tuple[str, str, str]]):
    """ Combine videos and danmakus

    :param files: [(video, danmaku, output)]
    :return:
    """
    commands = []
    for video, danmaku, output in files:
        if os.path.exists(danmaku):
            video, danmaku, output = video.replace('\\', '/'), danmaku.replace('\\', '/'), output.replace('\\', '/')
            commands.append(rf'%APPLICATION -i "{video}" -vf "subtitles=\'{danmaku}\'" "{output}"')
        else:
            logger.warning('Cannot find danmaku file: %s, skip it.', danmaku)
            FileUtils.renameFile(video, output)
    command = ' & '.join(commands)
    run_shell(command, 'ffmpeg')
