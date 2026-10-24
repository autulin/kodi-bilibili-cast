# 安装

## 前置条件

- Kodi 21.x（Android 或 CoreELEC/LibreELEC）
- `inputstream.adaptive`（Kodi 官方仓库，或 CoreELEC 自带）
- 手机与盒子在同一局域网
- 盒子 `tcp/9958` 空闲

## 方式一：打包成 zip 安装

```bash
./tools/build_zip.sh
```

然后在 Kodi 中：**设置 → 插件 → 从 zip 安装**，选择
`dist/service.bili.cast-<version>.zip`。

## 方式二：直接拷贝目录（开发）

```bash
# Android
adb push service.bili.cast \
  /sdcard/Android/data/org.xbmc.kodi/files/.kodi/addons/

# CoreELEC
scp -r service.bili.cast root@<box>:/storage/.kodi/addons/
```

重启 Kodi，插件会作为 service 自动启动。

## 启用与设置

首次安装后确认插件已启用：

**设置 → 插件 → 我的插件 → 服务 → Bili Cast**

设置项：

| 设置 | 默认 | 说明 |
|---|---|---|
| 设备名称 | 我的小电视 | 手机投屏列表中显示的名字 |
| HTTP/NVA 端口 | 9958 | 必须与官方协议一致，一般不要改 |
| 启用 SSDP 发现 | 开 | 关闭后手机无法自动发现 |
| 弹幕区域 | 1/4 | 1/4、1/2、3/4、全屏 |
| 弹幕字号 | 48 | 1080P 画布下的像素字号 |
| 弹幕不透明度 | 85% | |
| 弹幕最大行数 | 4 | 与区域共同决定同屏条数 |
| 关闭 MediaCodec Surface | 开 | 仅 Android，见下方说明 |

修改弹幕设置后需要重启 Kodi 生效。

## 端口冲突

官方“云视听小电视”（`com.xiaodianshi.tv.yst`）也监听 `tcp/9958`。

Android 上先停掉它：

```bash
adb shell am force-stop com.xiaodianshi.tv.yst
```

如果日志出现 `preferred port 9958 busy`，说明端口被占用，手机将无法连接。
插件会退到随机端口并在 Kodi 里弹通知，但 NVA 客户端只认 9958，所以必须释放端口。

CoreELEC 上不存在这个问题。

## Android：关闭 MediaCodec Surface

<a id="android-mediacodec-surface"></a>

部分 Amlogic 盒子（例如 Phicomm N1）在
`videoplayer.usemediacodecsurface=true` 时，播放几秒后 Kodi 会销毁视频窗口
退回桌面，表现为“停止/切清晰度后卡死”。

插件在 Android 上默认把该设置改为 `false`。硬解仍然生效
（`amc-h264(S)`），播放、暂停、拖动、停止都正常。

如果不希望插件修改 Kodi 全局设置，可以在设置页关闭
“兼容性 → 关闭 MediaCodec Surface”，但 N1 上建议保持开启。

## 首次使用

1. 手机 B 站打开任意视频，点右上角 TV 图标
2. 列表中选择“我的小电视”或“我的小电视(有弹幕)”
3. Kodi 开始播放，弹幕显示在顶部
4. 手机端可暂停、拖动、切清晰度、开关弹幕

1080P 需要片源本身支持；`durl` 回退时为 720P，日志中
`playurl qn=80` 表示拿到了 1080P。

## CoreELEC

CoreELEC 21.1.1-Omega 已实测通过（Kodi 21.1.0，Amlogic S905D），
`inputstream.adaptive` 为系统自带。安装方式见
[docs/coreelec.md](coreelec.md)。
