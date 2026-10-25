# .env 配置与授权

.env 由 bootstrap 自动创建在 RUNTIME。升级技能时继续使用该配置，不把它复制到共享包。示例模板只有公开 API 路径和空密钥。

| 配置 | 填写方式 |
|---|---|
| DASHSCOPE_API_KEY | 用户在百炼控制台取得的 API Key，只在本机填写 |
| BAILIAN_REGION | cn-beijing 或 ap-southeast-1，与 Key 所属地域一致 |
| BAILIAN_BASE_URL | 可空；默认使用地域公共地址；也可填控制台提供的业务空间专属 HTTPS 基址 |
| IMAGE_ENDPOINT / TTS_ENDPOINT / ASR_ENDPOINT | 可空，由基址拼接；如需覆盖，填官方完整接口地址 |
| IMAGE_PROVIDER | auto、agent、chatgpt-browser、bailian 或 manual |
| IMAGE_MODEL | 默认 qwen-image-2.0-pro；调用前确认账号可用 |
| IMAGE_SIZE | 宽*高；默认 1664*928，最终按目标画面统一裁切/留白 |
| BROWSER | auto、chrome 或 edge，用户指定的优先 |
| TTS_MODEL / TTS_VOICE / ASR_MODEL | 保留经过项目使用的示例；按本账号和官方接口确认后使用 |
| JY_APPS_ROOT / JY_PROJECTS_ROOT | 实际剪映安装、项目目录；未知可空，执行草稿任务时再发现 |

Key 和 endpoint 是两种不同信息，百炼 Bearer 鉴权不需要用户再提供另一套 AccessKey Secret。北京与新加坡的 Key、接口不可混用。

引导话术示例：
“已创建本机 .env。请在该文件填写 DASHSCOPE_API_KEY，并确认 BAILIAN_REGION 与控制台一致；如控制台要求专属域名，填 BAILIAN_BASE_URL。保存后告诉我已填写，不要把 Key 发到聊天里。”

用文件编辑器打开文件时尊重宿主权限；用户自行输入。Agent 后续只运行 doctor 检查 credential_present。不要用 cat/type/Get-Content 打印 .env，不把 Key 放入参数、命令历史、截图、日志或项目状态。公开报告不保存签名图片下载 URL。

缺 Key 时继续本地音频整理、分镜、提示词、已有图片验收；不能把未调用的 API 写成成功。用户选择 Agent 原生生图或 ChatGPT 网页时，该图像路线不依赖百炼 Key；需要百炼配音/识别时再配置。

参考：[获取 API Key](https://help.aliyun.com/zh/model-studio/get-api-key)、[千问文生图接口](https://help.aliyun.com/zh/model-studio/qwen-image-api)。模型默认值不是账号可用性的保证，401/403、地域或模型错误时按 recovery.md 排查。
