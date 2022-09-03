import os.path
from moviepy.editor import VideoFileClip


def getVideoTime(video: str) -> int:
    video_clip = VideoFileClip(video)
    duration = video_clip.duration
    video_clip.close()
    return duration


def getTotalTime(videos: list[str]) -> int:
    result = 0
    for video in videos:
        if os.path.exists(video):
            result += getVideoTime(video)
    return result
