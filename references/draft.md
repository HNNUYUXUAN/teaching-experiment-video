# 草稿编排

先读取实际素材、placement、SRT、草稿；截图和旧表不能替代当前状态，不固定页数、段数或总时长。

## 路线

界面操作使用当前环境可用的 Windows 桌面控制工具：取得真实窗口，观察后操作，再刷新状态；持续无法控制时停止界面操作并报告。

文件路线仅操作副本。先让用户保存并退出草稿/关闭剪映，确认文件稳定，记录 hash 并完整备份到使用者指定的备份目录。保留旧项目；不写正在编辑的 live 草稿。

从使用者提供的剪映安装目录枚举实际版本和 videoeditor.dll；本地 codec 用隔离子进程调用已安装 DLL，不上传远程解密。每个版本先对副本解密→加密→解密比较 JSON。不同安装版本须分别核验兼容性。

## 脚本

环境内 `python SKILL_ROOT/scripts/draft_ops.py inspect SOURCE --app APPDIR --output scratch.json` 读取草稿。明文仅在本地临时目录，用后删除，不展示整个草稿。

`prepare SOURCE --app APPDIR --output NEW_STAGE --plan plan.json --destination NEW_FINAL_PATH` 只生成新副本，不注册。

plan 的 ID 必须来自实际检查：

```json
{"visual_track_id":"观察到的ID","audio_track_id":"观察到的ID","caption_track_id":"观察到的ID","total_us":20000000,"visuals":[{"segment_id":"观察到的ID","path":"assets/01.png","kind":"image","end_us":20000000}],"captions":[{"text":"这是旁白。","start_ms":0,"end_ms":2500}]}
```

保留未知字段、音轨、字幕样式，只改图片时长、视觉入点和既有字幕时间。图片 source duration 随 target 改，视频源时长和速度不自动改。缺轨道时先在剪映导入经核验的字幕/音轨，再重新检查，不猜 schema。

真实视频用微秒；6,666,666us 不能机械变 6,667,000us，下一张静态图吸收舍入差。先计算精确 end_us 再调用。多轨、复合片段、变速超出已验证形状时扩展检查和测试，不能选同类型第一条轨道蒙混。

## 注册与重新打开

1. staging 验证后复制到唯一新草稿目录，备份 root_meta_info.json；原项目不动。
2. 优先让剪映正常发现/导入。需修改索引时先检查实际 all_draft_store schema，复制源条目更新新项目字段，保留无关条目；写前校验 hash，临时文件原子替换，冲突时重新读取。
3. project ID（meta.draft_id）与 timeline ID（content.id / Timelines 子目录）不同。根 draft_content.json 与活跃嵌套副本一致，检查 Timelines/project.json 和 timeline_layout.json 引用。
4. 剪映扫描可能重分配 project ID；按精确目录路径匹配唯一注册条目，必要时同步新副本 meta，不反复强制旧 ID。目录和标题存在不等于注册完成。
5. 重新打开新草稿，核验离线素材、时长、可编辑字幕，抽播开头、中段、关键动作、结尾。工具不可用仅报告文件级完成。

交付每张图每次出现的文件、入点、出点、持续秒数、同图合计，及画面/旁白/音频/字幕映射。轻微推近默认 100%–105%，只在获准且不裁文字时使用，无须每页都加效果。
