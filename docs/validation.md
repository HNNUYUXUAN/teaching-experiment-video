# 1.1.0 验证记录

验证日期：2026-10-25。发布代码以仓库提交及 Release 所附 SHA-256 清单定位。

| 层级 | 本次结果 | 覆盖范围 |
|---|---|---|
| Windows x64 本地环境 | 通过 | 发现已有 conda，创建独立环境，bootstrap 返回 ready_local，健康检查通过 |
| 离线自动测试 | 17 项通过 | 音频样本拼接、真实偏移、字幕一致性、草稿字段保留、配置创建与保留、地域端点、图像 dry-run、模拟网络与缓存、请求中断保护 |
| Miniconda 全新安装 | 实现与指南已提供 | 本轮使用已有 conda，未在无 conda 设备上实装 |
| Linux / Apple Silicon macOS | 入口与适配指南已提供 | 本轮未做相应平台实机验证 |
| 百炼真实请求 | 配置与适配器已提供 | 本轮发布验证未发送计费云请求；调用前核验账号、地域、模型与授权 |
| 浏览器生图 | 操作与验收指南已提供 | 当前展示插图由已连接 Chrome 的 ChatGPT 创建并下载；其他 Agent/账号需独立验证连接 |
| 剪映本地 DLL | 适配器及往返检查已提供 | 使用者应针对自己的安装版本运行往返测试，再检查草稿播放 |

离线测试复现：

```powershell
& ./scripts/run.ps1 -Script test_pipeline
& ./scripts/run.ps1 -Script test_portable
```

也可在装有 `requests`、`python-dotenv`、`Pillow`，且 PATH 中可以运行 `ffmpeg` 的 Python 3.11 环境中运行：

```text
python -B -m unittest discover -s scripts -p "test_*.py" -v
```

离线测试通过证明所列脚本行为；每次课程作品仍需要物理事实、字形、字幕、试听和播放检查。自动化检查与人工检查共同构成交付记录。
