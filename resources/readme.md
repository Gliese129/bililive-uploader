## live2video.json
直播分区与视频分区的映射
~~~json
[
  {
    "name": "手游",
    "channel": "游戏 手机游戏"
  },
  {
    "name": "生活",
    "children": [
      {
        "name": "萌宠",
        "channel": "生活 动物圈"
      }
    ]
  }
]
~~~

由于该部分没有好心人~~大冤种~~整理，所以只能苦一苦用户了（

上例中，直播父分区为“手游”的录播会被直接归类为“游戏 手机游戏”

而“生活”分区因为没有设置对应频道，不会被映射，但是“生活 萌宠”会被归类为“生活 动物圈”

程序启动后会将/recorder/live2video.json复制到/config/live2video.json，如果需要修改，可以直接修改/config/live2video.json