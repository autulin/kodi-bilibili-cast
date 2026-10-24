# 架构

## 组件

```text
service.bili.cast/
  addon.xml              Kodi addon 元数据（xbmc.service，开机启动）
  service.py             service 入口：读设置、应用兼容项、启动/停止 server
  lib/
    ssdp.py              1900 组播：MediaRenderer + NirvanaControl:3 广播与 M-SEARCH 响应
    http_dlna.py         description.xml / SCPD / SOAP / /dash/*.mpd
    nva.py               9958 TCP：NVA/1.0 握手、帧编解码、心跳、命令收发
    server.py            连接管理、命令分发、播放调度、进度与状态回传
    bili_api.py          B 站 TV playurl（含签名）、视频标题、弹幕 XML
    dash.py              DASH video+audio → 最小 MPD（SegmentBase 字节范围）
    danmaku.py           弹幕 XML → ASS（区域、字号、透明度、行数限制）
    player.py            Kodi Player 封装：inputstream.adaptive、字幕、音量、倍速
    device.py            设备描述 XML、NirvanaControl SCPD
    net.py               本机地址探测、HTTP 日期、UUID
    storage.py           addon_data 目录、持久化设备 UUID
    log.py               Kodi 日志 / 纯 Python 日志
  resources/
    settings.xml         设备名、端口、弹幕、兼容性设置
    language/            中英文文案
```

## 投屏时序

```text
手机 B站 App
  │
  ├─ SSDP M-SEARCH (udp/1900)
  │     └─ 回应 urn:app-bilibili-com:service:NirvanaControl:3
  │
  ├─ GET /bilibili/description.xml
  │     └─ friendlyName / capability / ottVersion 等设备描述
  │
  ├─ SETUP /projection NVA/1.0 (tcp/9958)
  │     └─ NVA/1.0 200 OK + Session/UUID
  │
  ├─ Play {aid, cid, epid, seasonId, accessKey, userDesireQn, seekTs, ...}
  │     └─ 插件：x/tv/playurl (fnval=4048) → DASH
  │         └─ 生成 MPD → http://<box>:9958/dash/xxx.mpd
  │             └─ inputstream.adaptive 播放
  │         └─ 弹幕 XML → ASS → setSubtitles()
  │
  └─ Pause / Resume / Seek / Stop / SetVolume / SwitchQn / SwitchSpeed / SwitchDanmaku

插件 → 手机（每秒）
  OnProgress {duration, position}
  OnPlayState {playState: 3 loading / 4 playing / 5 paused / 7 stopped}
  OnEpisodeSwitch / OnQnSwitch / OnDanmakuSwitch / SpeedChanged
```

## 为什么用 DASH 而不是 durl

B 站 TV `x/tv/playurl` 有两种返回：

| 请求 | 返回 | 最高清晰度 |
|---|---|---|
| 默认 | `durl` 混流 MP4 | 720P |
| `fnval=4048` | `dash` 分离视频/音频 | 1080P（id=80） |

`durl` 的混流封顶在 720P，所以插件默认请求 DASH。DASH 的视频和音频是
两个独立的 `.m4s` 文件，Kodi 需要一个 MPD 来描述它们；`inputstream.adaptive`
又只接受 HTTP URL，所以插件把生成的 MPD 通过自己的 `tcp/9958` 暴露为
`/dash/<cid>_<qn>.mpd`。

MPD 使用 `SegmentBase` + 字节范围（`Initialization` / `indexRange`），
因为 B 站给的是单文件分片，不是分段的 `SegmentList`。

## 清晰度协商

手机端显示的清晰度来自插件回传的 `OnQnSwitch.curQn`，不是手机自己猜的。
所以：

- 只有拿到真实 `playurl` 后才发送 `OnQnSwitch`，否则手机会锁在占位值
- `supportQnList` 保持 B 站返回的顺序（高→低），不按数值排序
- `durl` 回退时 `curQn` 会是 64，手机就显示 720P，这是真实结果

## 线程模型

- `BiliCast-TCP`：`socketserver.ThreadingTCPServer`，每个连接一个线程
- `BiliCast-NVA-Ping`：每连接每秒发一次心跳
- `BiliCast-Play`：取流 + 启动播放，不阻塞 NVA 命令线程
- `BiliCast-Progress`：每秒读播放器进度并广播
- `BiliCast-Danmaku`：下载弹幕并转 ASS
- `BiliCast-Stop`：异步停播放器，避免 Kodi 拆播放器时阻塞回包

## 端口

| 端口 | 协议 | 用途 |
|---|---|---|
| 9958/tcp | HTTP + NVA | 设备描述、SOAP、MPD、NVA 控制通道 |
| 1900/udp | SSDP | 发现与广播 |

官方“云视听小电视”也占用 9958/tcp，两者不能同时运行。
