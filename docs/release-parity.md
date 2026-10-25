# 跨渠道版本一致性

教学实验视频制作 **1.1.0** 以提交联想开放平台的完整技能包作为功能基准。该版本于 2026-10-25 15:29:19（北京时间）提交，应用 ID 为 `202610251502271650`。官方 CLI 返回上传成功，Edge 管理中心当日显示“待审核”；后续审核结果以平台为准。

## 同一套功能，两种包装

| 项目 | 联想原始上传包 | GitHub 适配包 |
|---|---|---|
| 功能文件 | 36 个 | 同一组 36 个文件 |
| 版本元数据 | `version: 1.1.0` | `metadata.version: "1.1.0"` |
| 运行脚本与使用指南 | 基准内容 | 相同内容，文本换行可统一为 LF |
| 根目录许可 | 原上传内容 | 增加原创代码与文档的 MIT `LICENSE` |

GitHub 的元数据调整用于通用 Agent Skill 校验。技能正文保持相同；`assets/`、`references/`、`scripts/` 的全部文件均接受一致性校验。README、示意图、仓库工具与 CI 是开源协作资料，可独立完善。

[基准清单](release-baseline.json)记录原包哈希、36 个文件的原始 SHA-256、适配后的 LF 哈希以及允许的精确转换。当前适配包与原包对比：26 个文件字节相同，9 个文件仅改变换行，`SKILL.md` 只调整上述元数据位置；适配包额外含根目录 `LICENSE`。

## 原始包身份

原始上传文件名：`teaching-experiment-video-1.1.0.zip`。

为区分渠道，在 [v1.1.0 Release](https://github.com/HNNUYUXUAN/teaching-experiment-video/releases/tag/v1.1.0) 中以 `teaching-experiment-video-1.1.0-lenovo-original.zip` 命名保存同一文件。

- 字节数：`67622`
- SHA-256：`434a4629ab4a21397b77624363a6af297025ef7ee53e6e509d8b5c296361c6e5`
- 原包 36 个文件，ZIP 根目录含 `SKILL.md`

附件命名只用于区分渠道，原始包的文件字节保持不变。GitHub 适配包继续使用 `teaching-experiment-video-1.1.0.zip`。

## 本地与 CI 校验

在仓库根目录运行：

```text
python -B tools/verify_release_parity.py
python -B -m unittest discover -s tools/tests -p "test_*.py" -v
```

下载原始渠道包后，还可同时核对 ZIP 的完整文件哈希、大小、逐文件清单及元数据转换：

```text
python -B tools/verify_release_parity.py --archive teaching-experiment-video-1.1.0-lenovo-original.zip
```

门禁检查文件缺失、指定源码目录中的新增文件，以及内容变化。只归一化 CRLF 为 LF，不忽略空格、注释或其他文本改动。使用 `python -B` 保持源码目录整洁；源码目录中的缓存文件也会被报告为新增文件。

后续更新功能时，应先生成并验证新的渠道包，再建立对应版本的基准清单。维护者在同一变更中说明版本、功能变化、渠道提交证据与验证结果；CI 随即检查这份明确的基准。
