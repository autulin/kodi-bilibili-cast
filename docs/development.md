# 开发

## 目录

```text
service.bili.cast/   Kodi addon 本体
tools/               本地开发与协议测试脚本
docs/                文档
```

## 本地跑协议层（不需要 Kodi）

```bash
python3 tools/dev_run.py --port 19958
```

它会启动 SSDP + HTTP + NVA，但不接 Kodi 播放器，只回传模拟状态。

另一个终端：

```bash
# 模拟手机发 NVA 命令
python3 tools/fake_nva_client.py 127.0.0.1 19958

# 发 SSDP 搜索
python3 tools/ssdp_search.py --st urn:app-bilibili-com:service:NirvanaControl:3
```

## 用真实视频测试

`tools/cast_test.py` 会完整模拟手机：SSDP 之后的 NVA 握手 + `Play`，
并打印所有回传帧。

```bash
BILI_ACCESS_KEY='<投屏会话 accessKey>' \
  python3 tools/cast_test.py <box-ip> 9958 <aid> <cid> --qn 80 --wait 20 --stop
```

`accessKey` 从手机投屏时插件日志里的 `NVA command Play` 读取；
也可以先用 `tools/probe_playurl.py` 单独验证取流。

## 检查取流结果

```bash
python3 tools/probe_playurl.py <aid> <cid> --qn 80
```

输出 `quality`、`format`、`dash_video`、`dash_audio`。
`quality=80` 表示 1080P，`format=dash` 表示走 MPD。

## 安装到设备

```bash
# Android
adb shell am force-stop org.xbmc.kodi
adb shell rm -rf /sdcard/Android/data/org.xbmc.kodi/files/.kodi/addons/service.bili.cast
adb push service.bili.cast /sdcard/Android/data/org.xbmc.kodi/files/.kodi/addons/
adb shell am start -n org.xbmc.kodi/.Main

# CoreELEC
scp -r service.bili.cast root@<box>:/storage/.kodi/addons/
systemctl restart kodi
```

## 日志

Android：

```bash
adb shell grep -i 'service.bili.cast' \
  /sdcard/Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log
```

CoreELEC：

```bash
ssh root@<box> "grep -i 'service.bili.cast' /storage/.kodi/temp/kodi.log"
```

常见检查点：

| 日志 | 含义 |
|---|---|
| `HTTP/NVA listening on tcp/9958` | 服务已启动 |
| `SSDP listening on udp/1900` | 发现服务已启动 |
| `preferred port 9958 busy` | 端口被官方 App 占用 |
| `NVA command Play` | 手机命令已到达 |
| `playurl qn=80 ... format=dash` | 拿到 1080P DASH |
| `DASH selected: 1920x1080` | 已生成并选择 MPD |
| `danmaku ready:` | 弹幕转换完成 |
| `Kodi subtitles set:` | 弹幕已加载 |
| `Bilibili API error:` | 取流失败（日志不会打印 access key） |

## 隐私

日志会脱敏 `accessKey`、`accessCode`、`sessionId`、`biz_session_id`，
不会写入完整 token。提交 issue 前请仍然检查一遍日志内容。

## 代码约定

- 只用 Python 标准库，不引入第三方依赖（Kodi 内置 Python 环境限制）
- 网络请求走 `urllib.request`，不依赖 `requests`
- 新功能优先复用 `lib/` 中现有模块，避免在 `server.py` 堆逻辑
- 提交前跑：

```bash
python3 -m compileall -q service.bili.cast tools
```
