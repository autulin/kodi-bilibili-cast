# 故障排查

## 手机看不到「我的小电视」

按顺序检查：

1. **是否同一局域网**：手机和盒子是否在同一网段（例如都在 `192.168.1.x`）
2. **SSDP 是否启动**：日志中应有 `SSDP listening on udp/1900`
3. **路由器是否开启 AP 隔离**：开启后设备间无法互相发现
4. **Kodi 自带 UPnP 是否冲突**：建议关闭
   `services.upnp` / `services.upnpserver`
5. **端口是否被占用**：见下方「9958 被占用」

可以用下面的命令验证 SSDP 是否响应：

```bash
python3 tools/ssdp_search.py --st urn:app-bilibili-com:service:NirvanaControl:3
```

## 能看到但连接失败 / 投屏没反应

- 检查日志是否有 `NVA SETUP`：没有说明手机连不上 `tcp/9958`
- 检查是否出现 `preferred port 9958 busy`
- 防火墙/路由器是否拦截了 9958
- 手机 B 站版本过旧时设备描述字段可能不匹配

## 9958 被占用

官方「云视听小电视」`com.xiaodianshi.tv.yst` 也监听 9958。

```bash
adb shell am force-stop com.xiaodianshi.tv.yst
```

注意它在盒子重启后可能自启，需要重新执行。

## 有画面但无弹幕

- 日志应有 `danmaku ready:` 和 `Kodi subtitles set:`
- Kodi 只有一条字幕轨；如果视频自带字幕，弹幕会顶替它
- 设置里弹幕区域/字号是否过小
- CoreELEC 上如果显示方框，是缺中文字体，见下方「CoreELEC 字体」

## 弹幕卡顿

弹幕由 Kodi 的 libass 在 CPU 上渲染，S905 这类盒子压力较大。可以：

- 减小弹幕区域（1/4 屏）
- 减小字号
- 减少最大行数
- 关闭弹幕对比测试

## 停止后卡死 / 退回桌面

Android + Amlogic 盒子的 `videoplayer.usemediacodecsurface` 问题。
插件默认关闭它；如果手动改回来了，请在设置中重新开启
「兼容性 → 关闭 MediaCodec Surface」，或执行：

```bash
curl -u <kodi-user>:<kodi-password> -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"Settings.SetSettingValue",
       "params":{"setting":"videoplayer.usemediacodecsurface","value":false}}' \
  http://<box>:8088/jsonrpc
```

## 只有 720P

- 日志中 `playurl qn=` 是 64 表示确实只拿到 720P
- 检查是否 `DASH selected`：没有则走了 `durl` 回退
- 片源本身可能最高只有 720P
- 用 `tools/probe_playurl.py` 单独确认接口返回

## CoreELEC 字体

CoreELEC 21.1.1 实测自带中文字体，弹幕中文正常。如果你的构建缺少中文字体，
ASS 弹幕会显示方框。把一个 CJK 字体（例如 Noto Sans CJK）放到：

```text
/storage/.kodi/media/Fonts/
```

然后重启 Kodi。

## 提交 issue 前

请附上：

- Kodi 版本、系统（Android/CoreELEC）、盒子型号
- 日志中 `service.bili.cast` 相关行
- 复现步骤和大概时间点

**注意**：日志已脱敏 `accessKey` 等字段，但仍请自行检查一遍再上传。
