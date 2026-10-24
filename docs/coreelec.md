# CoreELEC 说明

CoreELEC 是只跑 Kodi 的精简 Linux 系统。对电视盒子来说，它通常比
Android 更省资源、温度更低，也少了一层 Android 音频/视频管线。

本项目已在 CoreELEC 21.1.1-Omega 上实测通过。

## 实测环境

| 项目 | 值 |
|---|---|
| 盒子 | Phicomm N1（Amlogic S905D，2GB） |
| 系统 | CoreELEC 21.1.1-Omega（社区 `Dual-OS-By_joyo1_V3.9.9.9` 构建） |
| Kodi | 21.1.0 |
| 内核 | 4.9.269 |
| 设备树 | `/proc/device-tree/model` = `Phicomm,N1` |
| 插件 | `service.bili.cast` 0.2.0 |

实测结果：

- 1080P DASH 正常播放，`DVDVideoCodecAmlogic` 硬解
- 弹幕正常显示，中文无方框
- 暂停、继续、拖动、停止均正常，停止后 Kodi 保持运行
- 播放 1080P 时 SoC 约 59–61°C，load 约 1.25，可用内存约 1.47GB

对比 Android 7.1.2 + Kodi 21.3（同一台盒子、同一片源）：
约 70–71°C、load 4.0–4.5、可用内存约 0.29GB。

## 这台盒子（Phicomm N1 / S905D）的现实情况

- **最高 CoreELEC 21.x**：CoreELEC 22 起不再支持 GXL（S905X/S905D）
- **建议 U 盘/SD 卡启动**：社区 N1 镜像通常不支持 `installtoemmc`，
  U 盘启动不会改动 eMMC，拔掉 U 盘即可回到 Android
- **设备树**：`gxl_p230_2g.dtb`
- **没有 Android 应用**：云视听小电视、mpv 等都不再可用，盒子变成纯 Kodi

## 相对 Android 的收益

| 项目 | 实测变化 |
|---|---|
| 温度 | 播放 1080P 时约 60°C，Android 同片源约 70°C |
| load average | 约 1.25，Android 约 4.0–4.5 |
| 内存 | 可用约 1.47GB / 2GB，Android 约 0.29GB / 1.8GB |
| 视频路径 | 直接走 Amlogic 解码器，不经过 Android MediaCodec Surface |
| 音频 | 直接 ALSA，无 AudioTrack 重采样，便于直通 |
| 刷新率/HDR | 自动帧率切换更成熟 |
| 端口冲突 | 不存在官方 App 占用 9958 的问题 |

## 不会变好的地方

- 硬解能力上限相同（S905D）
- 弹幕单条渲染成本相同，只是 CPU 余量更多
- 取流速度取决于网络与 CDN

## 安装插件

```bash
scp -r service.bili.cast root@<box>:/storage/.kodi/addons/
ssh root@<box> "systemctl restart kodi"
```

或把 `dist/service.bili.cast-<version>.zip` 拷到盒子后用 Kodi 的
「从 zip 安装」。

CoreELEC 21.1.1 自带 `inputstream.adaptive`，无需额外安装。
如果使用更精简的构建，请确认 Kodi 中已启用它。

## 日志

```bash
ssh root@<box> "grep -i 'service.bili.cast' /storage/.kodi/temp/kodi.log"
```

## 字体

CoreELEC 这版自带中文字体，实测弹幕中文正常。如果你的构建出现方框，
把一个 CJK 字体（例如 Noto Sans CJK）放到：

```text
/storage/.kodi/media/Fonts/
```

然后重启 Kodi。

## 兼容设置

插件中的「关闭 MediaCodec Surface」只对 Android 生效，在 CoreELEC 上会
自动跳过（日志 `compat: not Android, skip MediaCodec surface setting`）。

## 参考

- [CoreELEC 官网](https://coreelec.org/)
- [CoreELEC 论坛：Phicomm N1 支持讨论](https://discourse.coreelec.org/t/support-phicomm-n1/8233)
