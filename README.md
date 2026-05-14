# TimePredict Agent

这是一个面向时间序列预测论文的本地自动化管理 agent。它可以从多个论文来源收集近两三年的论文，写入本地 SQLite 数据库，并生成便于阅读的中文论文速览和 Markdown 报告。

## 功能

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
  agent.py          # agent 编排逻辑
  arxiv_client.py   # arXiv API 客户端
  cli.py            # 命令行入口
  config.py         # TOML 配置
  models.py         # 数据模型
  storage.py        # SQLite 存储
  summarizer.py     # 本地摘要器
  sources.py        # 多源采集器
  citation.py       # 引用分析和相似推荐
  fulltext.py       # PDF 下载
  tagger.py         # 论文分类标签
  scheduler.py      # 定时更新
  web.py            # 本地 Web 服务
  static/           # 可视化操作台
```

## 后续可扩展方向

- 增加论文阅读状态、收藏、已读/待读工作流
- 增加更细的方向分类，例如 foundation model、probabilistic、process mining、anomaly detection
- 增加批量 LLM 综述和跨论文对比报告
- 增加更稳定的浏览器辅助导入流程

## 本地密钥文件

项目启动时会自动读取根目录的 `.env` 或 `.env.local`。可以参考 `.env.example` 创建本地密钥文件：

```text
ANTHROPIC_BASE_URL=https://token-plan-cn.xiaomimimo.com/anthropic
ANTHROPIC_MODEL=mimo-v2.5-pro
ANTHROPIC_AUTH_TOKEN=你的新token
TIMEPREDICT_LLM_MAX_TOKENS=1800
```

`.env` 和 `.env.local` 已加入 `.gitignore`，不会作为代码文件提交。真实 token 不要写进 Python/JavaScript 源码。
