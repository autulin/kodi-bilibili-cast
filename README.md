# kodi-bilibili-cast

把 Kodi 变成 B 站「云视听小电视」的投屏接收端：手机 B 站 App 直接投屏到
Kodi，支持 **1080P** 和 **弹幕**。

手机端不需要额外 App，也不需要电视端登录。插件在 Kodi 中实现 B 站私有的
「哔哩必连」（NVA）投屏协议，手机投屏列表里会显示为「我的小电视(有弹幕)」。

[English](README.en.md)

## 特性

- **手机 B 站原生投屏**：SSDP 自动发现，列表里选择「我的小电视(有弹幕)」即可
- **1080P**：通过 DASH 取流，`inputstream.adaptive` 播放；`durl` 仅作回退（720P）
- **弹幕**：B 站弹幕 XML 转 ASS 字幕，可调区域、字号、透明度、行数
- **完整控制**：播放、暂停、继续、拖动、停止、音量、倍速、切清晰度、弹幕开关
- **状态回传**：进度、播放状态、清晰度、倍速实时同步到手机
- **纯标准库**：除 Kodi 自带的 `inputstream.adaptive` 外无第三方依赖
- **跨平台**：Kodi 21.x，Android 与 CoreELEC/LibreELEC 均可运行

## 已知限制

- 弹幕和普通字幕共用 Kodi 唯一一条字幕轨，暂不能同时显示
- 直播、DLNA 实际播放、番剧自动下一集尚未实现
- 手机端实时发送的弹幕只会以通知形式显示，暂不叠加到画面
- 1080P 依赖片源；只有 720P 片源时回退为 `durl`

## 快速开始

1. 安装 `inputstream.adaptive`（Kodi 官方仓库）
2. 下载 [Releases](https://github.com/autulin/kodi-bilibili-cast/releases) 中的
   `service.bili.cast-<version>.zip`，或运行 `./tools/build_zip.sh` 自行打包
3. Kodi → 设置 → 插件 → 从 zip 安装
4. 手机 B 站打开视频 → 右上角 TV 图标 → 选择「我的小电视(有弹幕)」

详细步骤见 [docs/install.md](docs/install.md)。

> **Android 用户注意**：官方「云视听小电视」也占用 `tcp/9958`。
> 安装后请先停掉它（`adb shell am force-stop com.xiaodianshi.tv.yst`），
> 否则手机无法连接本插件。CoreELEC 无此问题。

## 架构

```text
手机 B站 App
  → SSDP 发现 (udp/1900)
  → NVA/1.0 握手 (tcp/9958)
  → Play {aid, cid, accessKey, userDesireQn, ...}
  → x/tv/playurl (fnval=4048) → DASH
  → 生成 MPD → http://<box>:9958/dash/*.mpd → inputstream.adaptive
  → 弹幕 XML → ASS → setSubtitles
  → 每秒 OnProgress / OnPlayState 回传
```

详见 [docs/architecture.md](docs/architecture.md)。

## 兼容性

| 环境 | 状态 |
|---|---|
| Kodi 21.3 / Android 7.1.2 / Phicomm N1 (S905D) | 已实测 |
| Kodi 21.1.0 / CoreELEC 21.1.1-Omega / Phicomm N1 (S905D) | 已实测 |

CoreELEC 上走 Amlogic 原生解码（`DVDVideoCodecAmlogic`），1080P DASH、
弹幕、暂停/拖动/停止均正常；详见 [docs/coreelec.md](docs/coreelec.md)。

Android + Amlogic 盒子如果出现「停止后卡死/黑屏」，是
`videoplayer.usemediacodecsurface` 的问题，插件默认已处理，见
[docs/install.md](docs/install.md#android-mediacodec-surface)。

## 开发

```bash
# 不装 Kodi，本地跑协议层
python3 tools/dev_run.py --port 19958

# 模拟手机发送 NVA 命令
python3 tools/fake_nva_client.py 127.0.0.1 19958

# 打包成可安装的 zip
./tools/build_zip.sh
```

更多见 [docs/development.md](docs/development.md)。

## 更新记录

见 [CHANGELOG.md](CHANGELOG.md)。

## 参考与许可

本项目的 NVA 协议层参考并移植了 MIT 许可的
[Macast nirvana 插件](https://github.com/xfangfang/Macast-plugins/tree/main/nirvana)；
协议细节参考 [xfangfang 的协议分析](https://xfangfang.github.io/028)。
[Yiiiike/bilibili-mobile-cast-to-pc](https://github.com/Yiiiike/bilibili-mobile-cast-to-pc)
仅作行为参考，未复制代码。

项目以 MIT 许可发布，详见 [LICENSE](LICENSE) 与
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 免责声明

本项目是非官方的第三方实现，与哔哩哔哩无关联。仅用于个人在自有设备上
接收自己账号的投屏内容。请遵守 B 站用户协议与当地法律，不要用于商业用途
或内容分发。
