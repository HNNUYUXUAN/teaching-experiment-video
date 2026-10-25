# 版本与测试边界

本包不依赖任何 Agent 私有 API。需要宿主提供文件与终端能力才能直接执行脚本；浏览器和原生图像工具通过宿主能力适配，不存在可以通用调用所有 Agent 的固定函数名。

| 平台/能力 | 本版实现 |
|---|---|
| Windows x64 | PowerShell 预检、已有 conda 发现、官方 Miniconda 安装、精确依赖锁、.env、全部本地处理 |
| Linux x86_64/aarch64 | bash 安装入口、对应官方 Miniconda、conda-forge 环境、图片音频字幕处理 |
| Apple Silicon macOS | bash 安装入口、arm64 官方 Miniconda、conda-forge 环境、图片音频字幕处理 |
| Windows 剪映 | 保留本地 DLL 编解码适配器，使用前对实际安装版本做往返核验 |
| 其他系统剪映草稿 | 不执行 Windows DLL；保留导入包，交给适用编辑器 |
| 百炼生图 | Qwen-Image 同步 HTTP 适配器；其他模型先按当前官方文档适配 |
| 原生 Agent / ChatGPT 网页生图 | 能力检查、连接、逐步操作与验收指南，取决于当前宿主和账号 |

安装包固定文件名及哈希在 assets/miniconda-installers.json；Windows 包依赖在 conda-win-64.lock.txt。Unix 依赖是版本约束求解，不能宣称跨平台字节级一致。

验证时应区分：源码/语法检查、模拟网络测试、实际创建环境、真实云请求、真实浏览器生图、实际编辑器播放。运行 test_pipeline.py 和 test_portable.py 仅代表离线测试，不代表账号云端成功。没有实机跑过的系统须在交付记录中标为未验证。

第三方源码 scripts/vendor/draft_crypto.py 原样保留 Apache-2.0 许可与来源记录；不捆绑剪映二进制。Miniconda 由使用者从官方站点下载并接受适用条款；本 Skill ZIP 不捆绑安装器。
