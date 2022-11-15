FROM python:3.10
MAINTAINER Gliese<gliese129@gmail.com>

ENV DEBIAN_FRONTEND=noninteractive
# 设置UTF-8编码
ENV LANG=en_US.UTF-8
# 设置时区为北京时间
ENV TZ=Asia/Shanghai
# 更新apt-get,安装wget，yasm和nasm
RUN apt-get update -y && \
    apt-get install --fix-missing && \
    apt-get install wget yasm nasm -y
# 安装gcc和make和git
RUN apt-get install gcc make -y && \
    apt-get install git -y
# 安装libx264, libass, libfreetype, fontconfig, fribidis, libavformat, libvcodec, libavfilter
RUN apt-get install libx264-dev libass-dev libfreetype6-dev fontconfig libfribidi-dev libavcodec-dev libavfilter-dev libavformat-dev -y
# 复制微软雅黑字体
COPY ./resources/msyh.ttf /usr/share/fonts/msyh.ttf
# 安装ffmpeg
RUN git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg && \
    cd ffmpeg && \
    ./configure --enable-gpl --enable-libx264 --enable-libass && \
    make && \
    make install

# 安装danmaku factory
RUN git clone https://github.com/hihkm/DanmakuFactory.git && \
    cd DanmakuFactory && \
    mkdir temp && \
    make

#
COPY ./requirements.txt /app/requirements.txt
COPY ./**/*.py /app/
COPY ./resources/*.json /app/resources/

VOLUME /record
VOLUME /process
EXPOSE 8866

WORKDIR /app

RUN pip3 install --upgrade -r requirements.txt

ENTRYPOINT [ "python3", "run.py" ]
CMD [ "-w", "/process" ]
