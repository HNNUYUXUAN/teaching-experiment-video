# 生产执行表：逐步检查，不跳阶段

## 建立项目

从用户给出的工作区选择一个**不存在的新目录**。技能目录和用户项目目录分开。PowerShell 示例：

```powershell
& ./scripts/run.ps1 -Script project init --directory $projectDir --title "教学实验视频" --provider auto
```

把 $projectDir 设为用户确认的输出位置。已有目录不要重新初始化，读取其 state.json 并延续当前阶段。脚本创建 evidence、storyboard、prompts、images、audio、subtitles、edit、delivery、checks；source 原片留在原位置。

## 阶段和完成条件

| 阶段 | 输入 | 具体动作 | 必须存在的结果 | 完成条件 |
|---|---|---|---|---|
| evidence | 原始录像和教学目标 | 探测媒体、抽帧、回看动作，填写 evidence/index.csv | 时间点、可见操作与现象、限制 | 每个核心结论有原片依据，无法辨认处标注 |
| script | 证据表 | 写分镜及逐段旁白，填写 storyboard/shots.csv | 分镜、旁白、取段、预计时长 | 物理表述准确；用户需确认的稿件已经确认 |
| images | 每张图的具体目的和提示词 | 按 images.md 选择并执行一条路径 | 原始 PNG/JPEG 与来源/验收记录 | 中文、图示、比例逐张通过 |
| audio | 定稿旁白或已有录音 | synthesize 或 assemble | 分段 WAV、continuous.wav、placement.json | PCM 样本拼接一致，实测时长可用 |
| subtitles | 最终 WAV 与同源 ASR | asr 后 align，必要时听音修正 | captions.srt、alignment-audit.json | 单行、全文覆盖、无越界重叠，警告已核对 |
| edit | 原片、图片、placement、字幕 | 建导入映射；Windows 剪映按 draft.md 在副本编排 | 导入包/草稿副本/时间线表 | 路径存在、精确时长、关键动作完整 |
| export | 已检查的时间线 | 用户或可用工具导出，再 media_audit | 成片、媒体报告、播放核验 | 完整解码通过，画面字幕声音人工确认 |
| archive | 验收通过成片 | 按项目规范整理导航和过程材料 | 当前交付入口、归档导航、哈希 | 不破坏草稿引用，路径均可解析 |

不存在本次任务范围内的阶段，记录 skipped 与理由；未完成不能标 done。没有桌面工具时 edit 可记录 file_ready，并把 editor_validation 留 pending。只有本地交付不需要发布步骤。

## 命令协议

Windows 都使用 `scripts/run.ps1 -Script 名称`，Linux/macOS 用 `bash scripts/run.sh 名称`。这样会选独立 Python 并补齐 ffmpeg 路径，无需 conda activate。

音频示例：

```powershell
& ./scripts/run.ps1 -Script pipeline doctor
& ./scripts/run.ps1 -Script pipeline synthesize $manifestFile $newAudioDir
& ./scripts/run.ps1 -Script pipeline asr $placementFile
& ./scripts/run.ps1 -Script pipeline align $placementFile
```

已有录音使用 assemble 替代 synthesize。manifest 的例子在 assets/example-manifest.json，详细字段看 audio.md。示例没有录音路径，不能直接用于 assemble；先给每段加 audio 字段，相对路径以 manifest 所在目录为基准。

输出目录必须是新目录；重做旁白应新建版本，相关 ASR、字幕、时间线同时更新。TTS 和 ASR 会调用云服务，必须处于用户已授权的任务范围；不要为了环境检查调用它们。

成片检查：

```powershell
& ./scripts/run.ps1 -Script media_audit $videoFile --max-bytes 100000000 --expected-duration $durationSeconds --report $newReportFile
```

若没有体积/时长硬要求，省略对应参数。media_audit 只能判断文件层面，不知道物理内容是否正确。

## state.json 更新约定

每阶段只记录实际状态：pending、running、done、blocked、skipped、file_ready。修改 current_stage、next_action 和 blockers。blockers 每项写 stage、reason、needed_user_action；不得放 Key、cookie、签名 URL 或完整账号。

外部调用前先记录将要做的工作；调用结束后检查实际文件。如果 Agent 中断，后续 Agent 首先检查 *.pending.json，避免因忘记历史重复收费。图片生成标记和 API 凭据不应跟随发布包上传。

## 交接给其他 Agent

交接内容：技能版本、SKILL_ROOT、RUNTIME 配置文件位置（仅位置）、项目目录、state.json、已经生成的文件、下一命令和未解决的问题。用自然语言注明哪些测试尚未完成，不需要用户重新描述整个制作流程。
