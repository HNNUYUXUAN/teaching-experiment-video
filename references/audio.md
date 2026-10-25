# 音频和字幕

配置是独立运行目录 运行目录中的 .env。唯一待填项 DASHSCOPE_API_KEY；百炼 Bearer 鉴权不需要另一套 AccessKey Secret。HTTP endpoint 已填，是 API 地址而非凭据。默认 TTS qwen-audio-3.0-tts-flash / longanfengyue，48 kHz 单声道 PCM16；ASR qwen-audio-3.1-asr-flash。模型、音色、指令、速度和 endpoint 均可配置，不自动替换。

官方依据（2026-09-23 核对）：[TTS](https://help.aliyun.com/zh/model-studio/non-realtime-tts-user-guide)、[ASR HTTP](https://help.aliyun.com/en/model-studio/fun-asr-flash-recorded-speech-recognition-http-api)。TTS 临时音频 URL 及时下载；ASR 返回字词毫秒，base64 膨胀计入大小限制。脚本保守限制单段 60 秒、编码载荷 9.5 MB，超限在自然停顿处分段后重建 placement。模板 endpoint 与模型仅为示例；调用前按当前账号与官方文档核对，不猜工作空间配置。

## 运行

先依照 first-run.md 完成预检，将技能目录赋给 `$skillRoot`，再运行下面命令。doctor 不调用 API；synthesize/asr 上传对应文本或音频且可能计费，只在请求包含这些操作时运行。

```powershell
& "$skillRoot/scripts/run.ps1" -Script pipeline doctor
& "$skillRoot/scripts/run.ps1" -Script pipeline synthesize manifest.json 新输出目录
# 已有音频用 assemble，不重配音
& "$skillRoot/scripts/run.ps1" -Script pipeline assemble manifest.json 新输出目录
& "$skillRoot/scripts/run.ps1" -Script pipeline asr 输出目录\placement.json
& "$skillRoot/scripts/run.ps1" -Script pipeline align 输出目录\placement.json
```

manifest 示例（audio 仅 assemble 必需，相对 manifest 定位；段数和时长不固定）：

```json
{"segments":[{"id":"S01","text":"这是定稿旁白。","audio":"01.wav","lead_ms":0,"tail_ms":500,"slot_ms":20000,"equivalences":{}}]}
```

未设 slot_ms 使用实际语音+前后静默；指定时长不足时报错，不截断、不擅自加速。audio/ 只放连续导入的 01、02…WAV，静默已写入各段。continuous.wav 是总轨；audit/ 保存纯语音、元数据和 ASR 响应；placement.json 保存样本级位置和哈希。导入分段或总轨之一，不能叠加两套旁白。

## 对齐

ASR 针对最终语音 WAV 并检查哈希。native_word 是模型时间戳；多字词拆分标 within_word_interpolation，不声称原生逐字实测。稿件与识别不一致时输出 alignment-audit.json 并阻止 SRT 导出；听音确认后可在 manifest 添加有据可查的 equivalences（识别写法→稿件写法）并重建版本。不用 equivalences 隐藏漏读、增读或事实改变。

按语义和字词边界分单行，默认最大 5.5 秒、建议最小 1.2 秒、间隔 80 毫秒。caption-report.json 含短字幕等 readability warning，处理后才称直接可用。句尾标点可能轻微超过软字数上限；长英语词、公式及特殊字符人工检查。输出 UTF-8 BOM captions.srt，拒绝覆盖旧 SRT。改语音后同步重建总轨、ASR、字幕、画面 EDL。

请求结果不确定保留 pending 标记停止，不无限重试收费调用；核对计费和输出后再显式恢复。缓存绑定文本、配置和音频哈希。不得把签名 URL、密钥或鉴权头写入共享报告。
