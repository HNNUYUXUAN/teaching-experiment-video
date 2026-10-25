# 首次运行：从未配置环境到可开工

## 0. 明确两个目录

- SKILL_ROOT：解压后 SKILL.md 所在目录。通过文件工具确认，不假设技能在某个 Agent 的固定目录。
- RUNTIME：可写的用户运行目录。默认 Windows 为 LOCALAPPDATA 下的 TeachingVideoSkill；Linux/macOS 为 XDG_DATA_HOME（未设则用户 .local/share）下的 teaching-video-skill。
- 用户可设置 TEACHING_VIDEO_HOME 指定 RUNTIME。自定义 Windows 目录应在后续 run.ps1 中也传 -RuntimeRoot，或在每个新终端设置该环境变量。
- 环境在 RUNTIME/envs/teaching-video，配置在 RUNTIME/.env，安装缓存仅在 RUNTIME/downloads。不要把这些目录打入 Skill ZIP。

## 1. 先看 Agent 能做什么

确认能否读写本地文件、运行 PowerShell/bash、联网、控制 Chrome/Edge、生成图像。没有终端时不要声称完成安装；输出下面准确命令让用户执行，并请求返回脱敏的 bootstrap-report.json/doctor 输出，不要请求 .env。

Windows 使用系统 PowerShell 5.1 或更新版本，不需要预先安装 Python。不要使用可能指向应用商店的 python 命令来安装环境。

## 2. Windows x64

在 SKILL_ROOT 运行：

```powershell
& ./scripts/bootstrap.ps1 -CheckOnly
& ./scripts/bootstrap.ps1
```

需要自定义位置或 conda 不在常见位置时：

```powershell
& ./scripts/bootstrap.ps1 -RuntimeRoot $runtimeRoot -CondaExe $condaExe
& ./scripts/run.ps1 -RuntimeRoot $runtimeRoot -Script doctor
```

变量先由真实目录赋值，不直接复制未定义的变量。CondaExe 指向现有安装里的 Scripts/conda.exe。脚本会检索当前 CONDA_EXE、PATH、用户目录、LOCALAPPDATA 和 ProgramData 中常见 Anaconda/Miniconda 安装；不会改全局 PATH、默认 Python 或其他环境。

缺少 conda 时退出 20，给出官方许可页。通过用户指定的 Chrome/Edge 连接打开 https://www.anaconda.com/legal ，说明将按当前用户安装 Miniconda。用户确认接受条款后执行：

```powershell
& ./scripts/bootstrap.ps1 -AcceptMinicondaTerms
```

若用了自定义 -RuntimeRoot，应保留相同参数。这个开关记录本次运行已获得用户许可的事实，不能由 Agent 在没有用户同意时自动添加。随后下载、校验、安装和建环境均自动执行。Windows 使用 /InstallationType=JustMe、/AddToPath=0、/RegisterPython=0，避免改变其他应用环境。

脚本按官方已核验文件名和 SHA-256 固定 Miniconda 26.9.4（base 为 Python 3.11），环境依赖按附带 win-64 锁文件创建。校验失败不得执行安装器；没有管理员权限通常不影响用户级安装，企业策略阻止时交给用户。

## 3. Linux / Apple Silicon macOS

```bash
bash scripts/bootstrap.sh --check-only
bash scripts/bootstrap.sh
# 仅当用户已接受官方许可且缺少 conda：
bash scripts/bootstrap.sh --accept-miniconda-terms
bash scripts/run.sh doctor
```

支持安装器选择 Linux x86_64、Linux aarch64、macOS arm64。需要 bash、curl 和 sha256sum 或 shasum；缺少时按操作系统官方包管理方式补齐并重新运行。无需预先安装 Python。系统须满足当前 Miniconda 要求（包括 glibc/macOS 版本）；安装器报告不兼容时不要强装或下载猜测版本。

Unix 环境按 portable-spec.txt 从 conda-forge 求解；安装器固定哈希，但整个依赖集合未做跨平台精确锁定。Windows ARM64、32 位及 Intel macOS 不在此版本自动安装范围，返回 unsupported_platform 后请使用受支持设备或单独验证适配方案。

## 4. 查看结果并填写 .env

Windows 会保存 RUNTIME/bootstrap-report.json。成功状态 ready_local 表示本地工具齐全；不表示 API 已充值、密钥有效、浏览器已连接或图像已生成。

打开报告里的 config_file，按 configuration.md 指引让用户**本地填写**百炼 Key、地域、API 地址和模型。说明文件位置及需要填的键即可，不要读出密钥。复跑 doctor，credential_present 只说明非空，不是联网鉴权成功。

## 5. 首次验收

1. doctor 的 local_ready=true，ffmpeg/ffprobe 可运行。
2. .env 已创建，已有内容重复运行后保留。
3. 图像路线已选定；浏览器路线已有真实标签页连接证据。
4. 创建工作项目，整理证据和提示词。
5. 云请求有授权时先做一段语音或一张图片，确认下载、格式和内容；不要以安装成功替代云验证。

## 退出与恢复

- 0：本地就绪或 CheckOnly 检查完成；读 status 区分。
- 20：等待用户接受 Miniconda 许可。
- 21：下载、哈希、安装或运行中断；保留现状。
- 22：conda 或依赖环境异常；检查再修复。
- 23：未支持的系统/架构。
- 普通脚本的 1：业务校验失败；读取简短原因，按 recovery.md 处理。

安装中断可重新运行同一命令；完整缓存必须再次过哈希。已有完整环境检查通过就复用；残缺目录不会自动删除。Windows 对确认为该技能的 conda 环境可用 -Repair 按锁补齐；不能识别的目录应改用新 RUNTIME，并保留旧目录待检查。

依据：2026-10-25 经 Edge 查阅的 [官方安装说明](https://www.anaconda.com/docs/getting-started/advanced-install/silent-mode)、[官方安装包与哈希](https://repo.anaconda.com/miniconda/)。
