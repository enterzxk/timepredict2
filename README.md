# TimePredict Agent

这是一个面向时间序列预测论文的**完整 Agent 系统**。它具备规划、记忆、反思和多 Agent 协作能力，可以从多个论文来源收集近两三年的论文，写入本地 SQLite 数据库，并生成便于阅读的中文论文速览和 Markdown 报告。

## 核心 Agent 能力

### 1. 意图识别系统
- 7 维意图识别：概念理解、方法分析、实验评估、创新点、对比分析、研究方向、代码实现
- 自动理解用户问题类型，精准匹配回答策略

### 2. 任务规划系统
- 动态生成 5-8 步执行计划
- 根据问题意图自动选择工具和步骤
- 支持计划执行和状态追踪

### 3. 多 Agent 协作
- **Planner Agent**：任务规划和分解
- **Reader Agent**：论文阅读和理解
- **Code Agent**：GitHub 代码搜索
- **Critic Agent**：自我反思和检查
- **Tutor Agent**：答案生成和解释

### 4. 自我反思机制
- 自动检查回答是否覆盖问题
- 检查是否有证据支持
- 自动修复不完整的回答

### 5. 记忆系统
- 长期记忆存储（agent_memory）
- 基于问题检索相关记忆
- 支持记忆权重和更新

### 6. 会话管理
- 多轮对话支持
- 历史会话持久化
- 会话状态管理

## 功能特性

- 多源论文收集：arXiv、Semantic Scholar、OpenAlex、IEEE Xplore 公开检索/官方 API、Google Scholar HTML 导入
- 过滤最近 N 天内的论文，默认近 1095 天
- 将论文元数据、摘要和阅读优先级保存到 SQLite
- 使用本地抽取式摘要器生成论文速览，无需 API key
- 支持列表查看、关键词搜索、单篇详情和 Markdown 报告导出
- 支持勾选多篇论文生成中文文献综述草稿
- 论文全文 PDF 下载
- Semantic Scholar 引用/参考文献分析
- Semantic Scholar 或本地标签相似论文推荐
- 自动论文分类标签，包括方法标签、主题标签、来源标签和 CCF 会议等级标签
- 增强流程挖掘方向：Predictive process monitoring、Remaining time prediction、Process mining、Incremental event log
- **GitHub 代码仓库搜索**：根据论文内容自动搜索相关代码仓库（支持按关键词、方法名匹配）
- **每日推荐**：基于阅读历史和偏好生成每日论文推荐列表
- **用户反馈系统**：支持点赞/点踩，帮助 Agent 改进
- 定时任务循环更新论文库

## 快速开始

```powershell
python -m timepredict_agent collect --max-results 80 --recent-days 1095
python -m timepredict_agent list --limit 10
python -m timepredict_agent export --output reports/papers.md --limit 30
```

启动可视化界面：

```powershell
python -m timepredict_agent web
```

然后打开：

```text
http://127.0.0.1:8765
```

也可以安装为命令：

```powershell
python -m pip install -e .
timepredict-agent collect
```

## 常用命令

收集最新论文：

```powershell
python -m timepredict_agent collect
```

使用自定义 arXiv 查询：

```powershell
python -m timepredict_agent collect --query "(all:forecasting AND all:foundation model AND cat:cs.LG)" --max-results 20
```

查看论文列表：

```powershell
python -m timepredict_agent list --limit 20
```

关键词搜索：

```powershell
python -m timepredict_agent list --keyword transformer
```

查看单篇论文：

```powershell
python -m timepredict_agent show 2501.12345
```

导出阅读报告：

```powershell
python -m timepredict_agent export --output reports/papers.md
```

启动本地 Web 操作台：

```powershell
python -m timepredict_agent web --port 8765
```

Web 界面支持：

- 一键多源收集近两三年论文
- 搜索标题、摘要和方法标签
- 点击论文查看中文摘要、关键要点、相关性判断、作者和 PDF 链接
- 下载论文全文 PDF
- 补充引用关系和相似论文推荐
- **GitHub 代码搜索**：为论文查找相关代码实现，支持一键跳转
- **每日推荐**：查看个性化论文推荐，按相关性排序
- **论文专家对话**：支持多轮对话，自动规划任务，自我反思改进
- **历史对话面板**：左侧显示历史会话，支持切换和继续对话
- **论文面板折叠**：可折叠论文列表，聊天区域更宽敞
- **Agent 状态显示**：实时显示 Agent 执行进度和使用的工具
- **用户反馈系统**：支持点赞/点踩 + 分类备注，帮助 Agent 改进
- 导出 Markdown 阅读报告
- 勾选多篇论文后生成中文综述草稿，并保存到 `reports/literature_review.md`

## 增强命令

指定来源收集：

```powershell
python -m timepredict_agent collect --sources arxiv,semantic_scholar,openalex,ieee_xplore --max-results 80 --recent-days 1095
```

IEEE Xplore：

未配置 Key 时会先尝试 IEEE Xplore 公开站内检索抓取；如果被网络或站点策略拦截，可以改用官方 Metadata API：

```powershell
$env:IEEE_XPLORE_API_KEY="你的 IEEE API Key"
python -m timepredict_agent collect --sources ieee_xplore --max-results 80 --recent-days 1095
```

Google Scholar：

Google Scholar 不适合无人值守自动抓取。本项目支持“保存结果页 HTML 后本地解析”的方式：

```text
1. 在浏览器打开 Google Scholar 搜索结果页
2. 将网页另存为 data/google_scholar.html
3. 勾选 Web 界面的 Google Scholar HTML，或运行：
```

```powershell
python -m timepredict_agent collect --sources google_scholar --max-results 80 --recent-days 1095
```

下载全文：

```powershell
python -m timepredict_agent download 2605.13816v1
```

补充引用关系：

```powershell
python -m timepredict_agent enrich 2605.13816v1
```

推荐相似论文：

```powershell
python -m timepredict_agent recommend 2605.13816v1 --limit 8
```

使用 Anthropic-compatible 模型生成中文深度解读：

```powershell
$env:ANTHROPIC_BASE_URL="https://token-plan-cn.xiaomimimo.com/anthropic"
$env:ANTHROPIC_MODEL="mimo-v2.5-pro"
$env:ANTHROPIC_AUTH_TOKEN="你的新token"
python -m timepredict_agent llm-summary 2605.13816v1
```

Web 界面中也可以点击单篇论文详情里的 `LLM 深度解读` 按钮。请不要把真实 token 写入仓库文件，建议只放在当前终端环境变量或系统环境变量里。

定时自动更新：

```powershell
python -m timepredict_agent schedule --interval-minutes 1440
```

说明：Google Scholar 没有稳定官方公开 API，本项目不会内置绕过验证码或反爬策略的无人值守爬虫；当前采用本地 HTML 导入解析。CCF 更适合作为会议/期刊等级标签，本项目会根据论文 venue 自动打 `CCF-A`、`CCF-B` 等标签。

## 配置

默认配置在 `timepredict-agent.toml`：

```toml
[agent]
database_path = "data/papers.sqlite3"
report_dir = "reports"
pdf_dir = "data/pdfs"
max_results = 80
recent_days = 1095
sources = ["arxiv", "semantic_scholar", "openalex", "ieee_xplore"]
query = '(((all:time AND all:series) AND (all:forecasting OR all:prediction OR all:forecast)) OR (all:predictive AND all:process AND all:monitoring) OR (all:remaining AND all:time AND all:prediction) OR (all:process AND all:mining) OR (all:incremental AND all:event AND all:log)) AND (cat:cs.LG OR cat:stat.ML OR cat:cs.AI OR cat:cs.DB OR cat:cs.SE)'
```

打印配置模板：

```powershell
python -m timepredict_agent init-config
```

## 项目结构

```text
timepredict_agent/
  agent.py          # Agent 核心逻辑（规划、记忆、反思、多 Agent 协作）
  arxiv_client.py   # arXiv API 客户端
  cli.py            # 命令行入口
  config.py         # TOML 配置
  models.py         # 数据模型
  storage.py        # SQLite 存储（含 Agent 相关表）
  summarizer.py     # 本地摘要器
  sources.py        # 多源采集器
  citation.py       # 引用分析和相似推荐
  fulltext.py       # PDF 下载
  tagger.py         # 论文分类标签
  scheduler.py      # 定时更新
  github_search.py  # GitHub 代码仓库搜索
  web.py            # 本地 Web 服务（含 Agent API）
  static/           # 可视化操作台（含历史对话面板）
```

## 数据库表结构

```text
papers              # 论文元数据、摘要、标签
agent_sessions      # Agent 会话管理
agent_turns         # 对话历史（含计划、工具调用、反思）
agent_memory        # 长期记忆存储
agent_feedback      # 用户反馈（点赞/点踩）
agent_task_runs     # 任务执行记录
```

## Agent 架构

```
用户输入问题
      ↓
意图识别（7维）
      ↓
记忆检索（agent_memory）
      ↓
任务规划（动态 5-8 步）
      ↓
多 Agent 执行
  ├─ Reader Agent：读取论文、全文
  ├─ Code Agent：GitHub 搜索
  ├─ Reader Agent：引用分析、相关论文
  ├─ Tutor Agent：方法对比、综合解释
  └─ Critic Agent：反思检查
      ↓
自我反思 + 自动修复
      ↓
持久化存储（会话、记忆、反馈）
      ↓
返回结果 + 元数据
```

## 后续可扩展方向

- 语义记忆检索（当前基于关键词匹配）
- 动态规划调整（根据执行结果调整计划）
- LLM 驱动的深度反思
- 从用户反馈中学习
- 主动追问机制
- 增加论文阅读状态、收藏、已读/待读工作流
- 增加更细的方向分类，例如 foundation model、probabilistic、process mining、anomaly detection
- 增加批量 LLM 综述和跨论文对比报告
- 支持更多代码托管平台（GitLab、Bitbucket）

## 本地密钥文件

项目启动时会自动读取根目录的 `.env` 或 `.env.local`。可以参考 `.env.example` 创建本地密钥文件：

```text
ANTHROPIC_BASE_URL=https://token-plan-cn.xiaomimimo.com/anthropic
ANTHROPIC_MODEL=mimo-v2.5-pro
ANTHROPIC_AUTH_TOKEN=你的新token
TIMEPREDICT_LLM_MAX_TOKENS=1800
```

`.env` 和 `.env.local` 已加入 `.gitignore`，不会作为代码文件提交。真实 token 不要写进 Python/JavaScript 源码。
