FROM ubuntu
MAINTAINER Gliese<3207960592@qq.com>

ENV DEBIAN_FRONTEND=noninteractive
# 设置UTF-8编码
ENV LANG=en_US.UTF-8
# 设置时区为北京时间
ENV TZ=Asia/Shanghai
# 更新apt-get,安装wget, yum
RUN apt-get update -y && \
    apt-get install wget -y
# 安装gcc和make
RUN apt-get install gcc -y && \
    apt-get install make -y
# 安装git
RUN apt-get install git -y
# 安装构建Python所需的依赖项
RUN apt-get install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev -y
# 安装python3.9.8
RUN wget https://cdn.npm.taobao.org/dist/python/3.9.8/Python-3.9.8.tgz && \
    tar -xf Python-3.9.8.tgz && \
    cd Python-3.9.8 && \
    ./configure && \
    make && \
    make install
RUN rm Python-3.9.8.tgz

# 安装yasm和nasm
RUN apt-get install yasm -y && \
    apt-get install nasm -y
# 安装libx264, libass, libfreetype, fontconfig, fribidis, libavformat, libvcodec, libavfilter
RUN apt-get install libx264-dev libass-dev libfreetype6-dev fontconfig libfribidi-dev libavformat-dev libavcodec-dev libavfilter-dev  -y
# 安装微软雅黑
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
COPY ./*.py /app/.
COPY ./utils /app/utils
COPY ./resources/channel.json /app/resources/channel.json
COPY ./resources/live-to-video.json /app/resources/live-to-video.json

WORKDIR /app

RUN pip3 install --upgrade -r requirements.txt

ENTRYPOINT [ "python3", "server.py" ]
CMD [ "-c", "/config" ]