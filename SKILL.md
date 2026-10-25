---
name: teaching-experiment-video
description: 从实验录像制作教学视频的一体化技能。首次运行检查并配置 conda、独立 Python 环境和百炼 .env；支持 Agent 原生生图、Chrome或Edge中的ChatGPT生图、百炼生图，衔接配音、字幕、剪映草稿、成片验收和归档。适合环境尚未准备好的电脑与不同 Agent。
metadata:
  version: "1.1.0"
---

# 教学实验视频制作

这是一个自包含技能。运行代码、配音字幕、剪映处理及图像适配器都在本包内，不要求 Codex，也不需要再安装另一个剪映技能。以当前 Agent 实际拥有的文件、终端、浏览器和图像工具执行；禁止猜工具名或假装能力存在。

## 每次开始：按顺序做

1. 找到包含本文件的实际目录，记为 SKILL_ROOT；保留用户指定的项目、浏览器、编辑器和已有进度。
2. **首次使用或环境发生变化**，完整阅读 [首次运行](references/first-run.md)，执行 bootstrap。它建立独立环境并创建不含密钥的 .env。已有环境先预检，重复运行不覆盖 .env。
3. 完整阅读 [Agent 与浏览器适配](references/agent-adapter.md)。把能力状态写入项目 state.json；“检测到浏览器安装”不能等同于“已连接浏览器”。
4. 阅读 [生产执行表](references/execution.md)，从 state.json 最早未完成的步骤继续。未创建项目时运行 project.py init。
5. 生图前阅读 [图片生成](references/images.md)，按用户选择走 Agent 原生、ChatGPT 浏览器或百炼路径。缺少某条路径时继续证据整理、旁白、提示词和本地制作；切换需要用户账号、费用或改变指定服务的路线前取得必要授权。
6. 配音与字幕读取 [音频](references/audio.md)；剪映副本处理读取 [草稿](references/draft.md)。不用字数比例冒充语音时间戳，不改正在编辑的草稿。
7. 每个步骤完成前检查其输出文件和验收条件，再更新 state.json。失败按 [恢复表](references/recovery.md)处理，报告具体错误和下一动作。

## 一分钟入口

在 **技能目录** 打开 PowerShell：

```powershell
& ./scripts/bootstrap.ps1
& ./scripts/run.ps1 -Script doctor
```

Linux 或 Apple Silicon macOS：

```bash
bash scripts/bootstrap.sh
bash scripts/run.sh doctor
```

bootstrap 发现 Anaconda/Miniconda 就复用其 conda 创建本技能独立环境。缺少 conda 时，先提示 Miniconda 官方许可；用户接受后增加相应参数，自动下载官方锁定版本、校验 SHA-256、按当前用户安装并创建环境。命令、退出码及许可参数见首次运行文档。不能代替用户同意条款、验证码或浏览器权限。

## 凭据与能力

.env 在运行目录，不在技能发布包中。必须引导用户在本机填写自己的百炼 API Key 和地域/API 地址；API 地址不是另一把密钥。不要索取整份 .env、读取无关项目凭据或把密钥放到命令行。密钥暂缺时标记 cloud_pending，继续可做的本地工作。

Agent 原生图像工具和已登录 ChatGPT 的浏览器生图不需要百炼 Key；百炼路径需要。浏览器登录、连接批准、计费与 API 可用性分别验证，不互相推定。详情见 [配置](references/configuration.md)。

## 生产原则

基于真实录像建立观察证据、分镜和旁白；区分实拍现象与理想条件。以最终 WAV 样本数确定时长，画面用整数微秒，字幕用毫秒。图片和视频按出现顺序统一编号，音频单独编号。保持原始素材、旧制作包和草稿可恢复。

输出需要逐页视觉核对、字幕阅读、试听和全片解码；程序检查不能代替物理事实核对。按用户要求提供封面、发布文案、导入包和交接资料。格式字段见 [交付结构](references/delivery.md)，详细制作标准见 [制作验收](references/workflow.md)。

Windows x64 支持本地剪映 DLL 适配；Linux/macOS 可做音频、图像、字幕和媒体检查，剪映原生草稿操作移交有相应软件的 Windows 设备。未实际验证的平台和接口应如实标记，不宣称任何 Agent、网络或权限条件下均能全自动成功。
