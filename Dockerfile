FROM ubuntu
MAINTAINER Gliese<3207960592@qq.com>
# 更新apt-get,安装wget
RUN apt-get update -y && \
    apt-get install wget -y

# 安装gcc和make
RUN apt-get install gcc -y && \
    apt-get install make -y

# 安装构建Python所需的依赖项
RUN apt-get install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev -y
# 安装python3.10.0
RUN wget https://cdn.npm.taobao.org/dist/python/3.9.8/Python-3.9.8.tgz && \
    tar -xf Python-3.9.8.tgz && \
    cd Python-3.9.8 && \
    ./configure && \
    make && \
    make install
RUN rm Python-3.9.8.tgz

# 安装yasm
RUN apt-get install yasm -y
# 安装ffmpeg
RUN wget https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/ffmpeg/7:4.4-6ubuntu5/ffmpeg_4.4.orig.tar.xz && \
    xz -d ffmpeg_4.4.orig.tar.xz && \
    tar -xf ffmpeg_4.4.orig.tar && \
    cd ffmpeg-4.4 && \
    ./configure && \
    make && \
    make install
RUN rm ffmpeg_4.4.orig.tar

# 安装git
RUN apt-get install git -y
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

ENTRYPOINT [ "python3", "main.py" ]
CMD [ "-c", "/config" ]