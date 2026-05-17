# TimePredict Agent 视觉增强 + 论文生成功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 TimePredict Agent 从基础功能界面升级为精致设计风格，并添加基于已有论文结构生成新论文的功能。

**Architecture:** 前端使用 CSS 原生动画 + Intersection Observer API 实现视觉效果，后端使用 LLM 分析论文结构并生成内容。论文生成功能通过新增 API 端点实现，支持 Markdown 预览和 PDF 导出。

**Tech Stack:** CSS3 (animations, gradients, backdrop-filter), JavaScript (Intersection Observer, requestAnimationFrame), Python (LLM API, PDF generation)

---

## 文件结构

### 前端文件
- `timepredict_agent/static/styles.css`：添加动画、渐变、玻璃效果
- `timepredict_agent/static/app.js`：添加动画逻辑、论文生成界面
- `timepredict_agent/static/index.html`：添加论文生成入口

### 后端文件
- `timepredict_agent/llm_summary.py`：添加论文结构分析和生成功能
- `timepredict_agent/agent.py`：添加论文生成工作流
- `timepredict_agent/web.py`：添加论文生成 API 端点

### 测试文件
- `tests/test_paper_generation.py`：论文生成功能测试

---

## 任务 1：视觉设计改进 - 配色方案升级

**文件：**
- Modify: `timepredict_agent/static/styles.css:1-50`

- [ ] **步骤 1：升级 CSS 变量**

```css
:root {
  --bg: #f6f8f8;
  --surface: #ffffff;
  --surface-strong: #f9fbfb;
  --text: #1d2528;
  --muted: #657174;
  --faint: #8c979a;
  --line: #dde5e4;
  --line-strong: #c9d5d3;
  --teal: #0f766e;
  --teal-dark: #115e59;
  --teal-soft: #e7f4f1;
  --teal-gradient: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%);
  --accent: #6366f1;
  --accent-soft: #eef2ff;
  --success: #10b981;
  --success-soft: #ecfdf5;
  --warning: #f59e0b;
  --warning-soft: #fffbeb;
  --amber: #b7791f;
  --amber-soft: #fff4dc;
  --red: #b42318;
  --red-soft: #fff0ed;
  --shadow: 0 18px 42px rgba(29, 37, 40, 0.08);
  --shadow-lg: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  --glass-bg: rgba(255, 255, 255, 0.8);
  --glass-border: rgba(255, 255, 255, 0.3);
  font-family: Inter, "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
}

[data-theme="dark"] {
  --bg: #0d1117;
  --surface: #161b22;
  --surface-strong: #1c2128;
  --text: #e6edf3;
  --muted: #8b949e;
  --faint: #6e7681;
  --line: #30363d;
  --line-strong: #484f58;
  --teal: #2dd4bf;
  --teal-dark: #14b8a6;
  --teal-soft: #0d2818;
  --teal-gradient: linear-gradient(135deg, #14b8a6 0%, #2dd4bf 100%);
  --accent: #818cf8;
  --accent-soft: #1e1b4b;
  --success: #34d399;
  --success-soft: #064e3b;
  --warning: #fbbf24;
  --warning-soft: #451a03;
  --amber: #fbbf24;
  --amber-soft: #1c1a0e;
  --red: #f87171;
  --red-soft: #1c0d0d;
  --shadow: 0 18px 42px rgba(0, 0, 0, 0.3);
  --shadow-lg: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  --glass-bg: rgba(22, 27, 34, 0.8);
  --glass-border: rgba(48, 54, 61, 0.3);
}
```

- [ ] **步骤 2：添加噪点纹理背景**

```css
body::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: -1;
}
```

- [ ] **步骤 3：添加玻璃效果类**

```css
.glass-effect {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
}

.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  box-shadow: var(--shadow);
}
```

- [ ] **步骤 4：验证样式是否生效**

运行应用并检查：
- CSS 变量是否正确应用
- 噪点纹理是否显示
- 玻璃效果是否正常工作

- [ ] **步骤 5：提交更改**

```bash
git add timepredict_agent/static/styles.css
git commit -m "feat: 升级配色方案，添加渐变色和玻璃效果"
```

---

## 任务 2：视觉设计改进 - 渐变色应用

**文件：**
- Modify: `timepredict_agent/static/styles.css`

- [ ] **步骤 1：为侧边栏添加渐变背景**

```css
.sidebar {
  background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
  /* 其他现有样式保持不变 */
}

[data-theme="dark"] .sidebar {
  background: linear-gradient(180deg, #010409 0%, #0d1117 100%);
}
```

- [ ] **步骤 2：为按钮添加微光扫过效果**

```css
.primary-button {
  position: relative;
  overflow: hidden;
}

.primary-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transition: left 0.5s;
}

.primary-button:hover::before {
  left: 100%;
}
```

- [ ] **步骤 3：为卡片添加渐变边框**

```css
.paper-row {
  border: 2px solid transparent;
  background-image: linear-gradient(var(--surface), var(--surface)), 
                    linear-gradient(135deg, var(--teal), var(--accent));
  background-origin: border-box;
  background-clip: padding-box, border-box;
  transition: all 0.3s ease;
}

.paper-row:hover {
  background-image: linear-gradient(var(--surface), var(--surface)), 
                    linear-gradient(135deg, var(--teal-dark), var(--accent));
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}
```

- [ ] **步骤 4：为统计数字添加渐变文字**

```css
.metrics span {
  background: var(--teal-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
```

- [ ] **步骤 5：验证渐变效果**

运行应用并检查：
- 侧边栏渐变是否平滑
- 按钮 hover 时微光效果是否可见
- 卡片边框渐变是否正确
- 统计数字是否有渐变色

- [ ] **步骤 6：提交更改**

```bash
git add timepredict_agent/static/styles.css
git commit -m "feat: 添加渐变色效果，提升视觉层次感"
```

---

## 任务 3：动画效果 - 交错淡入动画

**文件：**
- Modify: `timepredict_agent/static/styles.css`
- Modify: `timepredict_agent/static/app.js`

- [ ] **步骤 1：添加 fadeInUp 动画 CSS**

```css
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.paper-row {
  opacity: 0;
  animation: fadeInUp 0.6s ease forwards;
}

/* 为前 10 个卡片添加不同的延迟 */
.paper-row:nth-child(1) { animation-delay: 0.1s; }
.paper-row:nth-child(2) { animation-delay: 0.15s; }
.paper-row:nth-child(3) { animation-delay: 0.2s; }
.paper-row:nth-child(4) { animation-delay: 0.25s; }
.paper-row:nth-child(5) { animation-delay: 0.3s; }
.paper-row:nth-child(6) { animation-delay: 0.35s; }
.paper-row:nth-child(7) { animation-delay: 0.4s; }
.paper-row:nth-child(8) { animation-delay: 0.45s; }
.paper-row:nth-child(9) { animation-delay: 0.5s; }
.paper-row:nth-child(10) { animation-delay: 0.55s; }
```

- [ ] **步骤 2：添加 Intersection Observer 逻辑**

在 `app.js` 中添加：

```javascript
function initStaggerAnimation() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  // 观察所有论文卡片
  document.querySelectorAll('.paper-row').forEach(card => {
    observer.observe(card);
  });
}

// 在页面加载和列表更新时调用
document.addEventListener('DOMContentLoaded', initStaggerAnimation);

// 在 renderList 函数末尾调用
function renderList() {
  // ... 现有代码 ...
  initStaggerAnimation();
}
```

- [ ] **步骤 3：添加 animate-in 类样式**

```css
.paper-row.animate-in {
  opacity: 1;
  animation: fadeInUp 0.6s ease forwards;
}
```

- [ ] **步骤 4：测试动画效果**

运行应用并检查：
- 论文卡片是否依次淡入
- 动画是否平滑（60fps）
- 滚动时新卡片是否触发动画

- [ ] **步骤 5：提交更改**

```bash
git add timepredict_agent/static/styles.css timepredict_agent/static/app.js
git commit -m "feat: 添加交错淡入动画，提升列表视觉效果"
```

---

## 任务 4：动画效果 - 数字滚动动画

**文件：**
- Modify: `timepredict_agent/static/app.js`

- [ ] **步骤 1：添加 animateCounter 函数**

```javascript
function animateCounter(element, target, duration = 2000) {
  const start = 0;
  const startTime = performance.now();
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // 使用缓动函数 (easeOutQuart)
    const easeOutQuart = 1 - Math.pow(1 - progress, 4);
    const current = Math.floor(start + (target - start) * easeOutQuart);
    
    element.textContent = current.toLocaleString();
    
    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }
  
  requestAnimationFrame(update);
}
```

- [ ] **步骤 2：修改 renderStats 函数**

```javascript
function renderStats() {
  const papers = state.papers;
  const highCount = papers.filter(p => p.reading_priority === 'high').length;
  const methodCount = new Set(papers.flatMap(p => p.method_tags || [])).size;
  const latestDate = papers.length > 0 ? papers[0].published?.slice(0, 10) || '--' : '--';

  // 使用动画计数器
  animateCounter(el.paperCount, papers.length);
  animateCounter(el.highCount, highCount);
  animateCounter(el.methodCount, methodCount);
  
  el.latestDate.textContent = latestDate;
}
```

- [ ] **步骤 3：添加动画完成后的样式**

```css
.metrics span {
  transition: transform 0.3s ease;
}

.metrics span:hover {
  transform: scale(1.1);
}
```

- [ ] **步骤 4：测试数字滚动效果**

运行应用并检查：
- 统计数字是否从 0 滚动到实际值
- 动画是否平滑
- 不同数字位数是否正确处理

- [ ] **步骤 5：提交更改**

```bash
git add timepredict_agent/static/app.js timepredict_agent/static/styles.css
git commit -m "feat: 添加数字滚动动画，提升统计区域视觉效果"
```

---

## 任务 5：论文生成功能 - 后端结构分析

**文件：**
- Modify: `timepredict_agent/llm_summary.py`
- Create: `tests/test_paper_generation.py`

- [ ] **步骤 1：编写测试用例**

```python
# tests/test_paper_generation.py
import pytest
from timepredict_agent.llm_summary import AnthropicSummaryClient

def test_analyze_paper_structure():
    """测试论文结构分析功能"""
    client = AnthropicSummaryClient()
    if not client.available():
        pytest.skip("LLM not available")
    
    # 模拟论文数据
    paper_title = "Test Paper"
    abstract = "This is a test abstract."
    pdf_text = "Introduction\nThis is the introduction.\n\nMethod\nThis is the method section.\n\nExperiments\nThis is the experiments section.\n\nConclusion\nThis is the conclusion."
    
    result = client.analyze_paper_structure(paper_title, abstract, pdf_text)
    
    assert result is not None
    assert "sections" in result
    assert len(result["sections"]) > 0
```

- [ ] **步骤 2：运行测试确认失败**

```bash
python -m pytest tests/test_paper_generation.py::test_analyze_paper_structure -v
```

预期：FAIL with "analyze_paper_structure not defined"

- [ ] **步骤 3：实现 analyze_paper_structure 方法**

在 `llm_summary.py` 的 `AnthropicSummaryClient` 类中添加：

```python
def analyze_paper_structure(self, paper_title: str, abstract: str, pdf_text: str) -> dict | None:
    """分析论文结构，提取章节组织方式"""
    if not self.available():
        return None
    
    try:
        prompt = f"""请分析以下论文的结构：

标题：{paper_title}
摘要：{abstract}
全文（前 10000 字符）：{pdf_text[:10000]}

请提取：
1. 章节结构（标题和层级）
2. 每个章节的核心内容和论证方式
3. 段落组织模式
4. 引用使用方式
5. 图表使用特点

输出 JSON 格式：
{{
  "sections": [
    {{
      "title": "章节标题",
      "level": 1,
      "content_type": "introduction|method|experiment|conclusion|other",
      "paragraph_count": 3,
      "description": "章节核心内容"
    }}
  ],
  "writing_style": "学术论文风格描述",
  "citation_pattern": "引用方式描述",
  "figure_usage": "图表使用方式"
}}"""

        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "temperature": 0.2,
            "system": "你是学术论文结构分析专家。请分析论文结构并输出 JSON 格式。",
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self._post_messages(payload)
        text = _message_text(response).strip()
        
        # 提取 JSON
        import re
        match = re.search(r'\{.*\}', text, re.S)
        if match:
            return json.loads(match.group())
        
        return None
    except Exception as e:
        print(f"Error analyzing paper structure: {e}")
        return None
```

- [ ] **步骤 4：运行测试确认通过**

```bash
python -m pytest tests/test_paper_generation.py::test_analyze_paper_structure -v
```

预期：PASS

- [ ] **步骤 5：提交更改**

```bash
git add timepredict_agent/llm_summary.py tests/test_paper_generation.py
git commit -m "feat: 添加论文结构分析功能"
```

---

## 任务 6：论文生成功能 - 后端内容生成

**文件：**
- Modify: `timepredict_agent/llm_summary.py`
- Modify: `tests/test_paper_generation.py`

- [ ] **步骤 1：编写测试用例**

```python
def test_generate_paper_content():
    """测试论文内容生成功能"""
    client = AnthropicSummaryClient()
    if not client.available():
        pytest.skip("LLM not available")
    
    # 模拟结构模板
    structure = {
        "sections": [
            {"title": "Introduction", "level": 1, "content_type": "introduction"},
            {"title": "Method", "level": 1, "content_type": "method"},
            {"title": "Experiments", "level": 1, "content_type": "experiment"},
            {"title": "Conclusion", "level": 1, "content_type": "conclusion"}
        ],
        "writing_style": "学术论文风格"
    }
    
    topic = "基于 Transformer 的时间序列预测"
    outline = ["问题定义", "模型架构", "实验设计", "结果分析"]
    
    result = client.generate_paper_content(structure, topic, outline)
    
    assert result is not None
    assert "content" in result
    assert len(result["content"]) > 0
```

- [ ] **步骤 2：运行测试确认失败**

```bash
python -m pytest tests/test_paper_generation.py::test_generate_paper_content -v
```

预期：FAIL with "generate_paper_content not defined"

- [ ] **步骤 3：实现 generate_paper_content 方法**

在 `llm_summary.py` 的 `AnthropicSummaryClient` 类中添加：

```python
def generate_paper_content(self, structure: dict, topic: str, outline: list[str], code: str = "") -> dict | None:
    """基于结构模板生成论文内容"""
    if not self.available():
        return None
    
    try:
        sections_desc = "\n".join([
            f"- {s['title']} ({s.get('content_type', 'other')})"
            for s in structure.get('sections', [])
        ])
        
        outline_desc = "\n".join([f"- {item}" for item in outline])
        
        prompt = f"""基于以下结构模板和用户输入，生成一篇论文：

结构模板：
{sections_desc}

写作风格：{structure.get('writing_style', '学术论文风格')}

用户输入：
主题：{topic}
大纲要点：
{outline_desc}

{f"代码片段：{code}" if code else ""}

请按照模板结构生成完整论文内容，保持学术论文的严谨性和逻辑性。
每个章节需要详细展开，包含足够的技术细节。
输出 Markdown 格式。"""

        payload = {
            "model": self.model,
            "max_tokens": 8000,
            "temperature": 0.3,
            "system": "你是学术论文写作专家。请根据给定的结构模板和主题生成高质量的学术论文内容。",
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self._post_messages(payload)
        text = _message_text(response).strip()
        
        if not text:
            return None
        
        return {
            "content": text,
            "format": "markdown",
            "topic": topic
        }
    except Exception as e:
        print(f"Error generating paper content: {e}")
        return None
```

- [ ] **步骤 4：运行测试确认通过**

```bash
python -m pytest tests/test_paper_generation.py::test_generate_paper_content -v
```

预期：PASS

- [ ] **步骤 5：提交更改**

```bash
git add timepredict_agent/llm_summary.py tests/test_paper_generation.py
git commit -m "feat: 添加论文内容生成功能"
```

---

## 任务 7：论文生成功能 - Agent 工作流

**文件：**
- Modify: `timepredict_agent/agent.py`

- [ ] **步骤 1：添加 generate_paper 方法**

在 `PaperAgent` 类中添加：

```python
def generate_paper(self, template_paper_id: str, topic: str, outline: list[str], code: str = "") -> dict:
    """基于模板论文生成新论文"""
    # 获取模板论文
    row = self.store.find_paper(template_paper_id)
    if row is None:
        raise ValueError(f"Template paper not found: {template_paper_id}")
    
    paper = _paper_from_row(row)
    pdf_text = self._pdf_text_for_row(row, max_chars=30000)
    
    # 分析模板论文结构
    structure = self.llm.analyze_paper_structure(paper.title, paper.abstract, pdf_text)
    if not structure:
        # 使用默认结构
        structure = {
            "sections": [
                {"title": "Introduction", "level": 1, "content_type": "introduction"},
                {"title": "Related Work", "level": 1, "content_type": "related_work"},
                {"title": "Method", "level": 1, "content_type": "method"},
                {"title": "Experiments", "level": 1, "content_type": "experiment"},
                {"title": "Conclusion", "level": 1, "content_type": "conclusion"}
            ],
            "writing_style": "学术论文风格"
        }
    
    # 生成论文内容
    result = self.llm.generate_paper_content(structure, topic, outline, code)
    if not result:
        raise RuntimeError("Failed to generate paper content")
    
    # 保存生成的论文
    paper_id = f"generated:{_safe_token(topic)}"
    generated_paper = Paper(
        arxiv_id=paper_id,
        title=f"Generated: {topic}",
        abstract=f"基于《{paper.title}》的结构生成的论文",
        authors=["AI Generated"],
        published=datetime.now(timezone.utc).isoformat(),
        updated=datetime.now(timezone.utc).isoformat(),
        entry_url="",
        pdf_url="",
        categories=[],
        source="generated",
        source_id=paper_id,
    )
    
    summary = self.summarizer.summarize(generated_paper)
    self.store.upsert_paper(generated_paper, summary)
    
    return {
        "paper_id": paper_id,
        "template_paper_id": template_paper_id,
        "topic": topic,
        "structure": structure,
        "content": result["content"],
        "format": result["format"]
    }
```

- [ ] **步骤 2：提交更改**

```bash
git add timepredict_agent/agent.py
git commit -m "feat: 添加论文生成 Agent 工作流"
```

---

## 任务 8：论文生成功能 - API 端点

**文件：**
- Modify: `timepredict_agent/web.py`

- [ ] **步骤 1：添加论文生成 API 端点**

在 `WebHandler` 类中添加：

```python
def _handle_generate_paper(self, paper_id: str) -> None:
    """处理论文生成请求"""
    content_length = int(self.headers.get("Content-Length", 0))
    body = self.rfile.read(content_length) if content_length else b""
    
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        self._json_response({"error": "Invalid JSON"}, 400)
        return
    
    topic = payload.get("topic", "").strip()
    outline = payload.get("outline", [])
    code = payload.get("code", "").strip()
    
    if not topic:
        self._json_response({"error": "Topic is required"}, 400)
        return
    
    try:
        agent = self._get_agent()
        result = agent.generate_paper(paper_id, topic, outline, code)
        self._json_response(result)
    except ValueError as e:
        self._json_response({"error": str(e)}, 404)
    except RuntimeError as e:
        self._json_response({"error": str(e)}, 500)
    except Exception as e:
        self._json_response({"error": f"Internal error: {str(e)}"}, 500)
```

- [ ] **步骤 2：添加路由处理**

在 `do_POST` 方法中添加路由：

```python
def do_POST(self):
    # ... 现有路由 ...
    
    # 论文生成路由
    match = re.match(r"^/api/papers/([^/]+)/generate-paper$", self.path)
    if match:
        self._handle_generate_paper(match.group(1))
        return
```

- [ ] **步骤 3：提交更改**

```bash
git add timepredict_agent/web.py
git commit -m "feat: 添加论文生成 API 端点"
```

---

## 任务 9：论文生成功能 - 前端界面

**文件：**
- Modify: `timepredict_agent/static/index.html`
- Modify: `timepredict_agent/static/app.js`
- Modify: `timepredict_agent/static/styles.css`

- [ ] **步骤 1：添加论文生成导航项**

在 `index.html` 的导航中添加：

```html
<button class="nav-item" type="button" data-nav="generator">
  <svg class="nav-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
  论文生成
</button>
```

- [ ] **步骤 2：添加论文生成界面 HTML**

在 `index.html` 的 `contentGrid` 后添加：

```html
<section id="generatorView" class="generator-view" hidden>
  <div class="generator-layout">
    <!-- 左侧：模板选择 -->
    <div class="generator-sidebar">
      <h3>选择模板论文</h3>
      <div id="templatePaperList" class="template-paper-list"></div>
      <div id="structurePreview" class="structure-preview" hidden>
        <h4>结构预览</h4>
        <div id="structureContent"></div>
      </div>
    </div>
    
    <!-- 中间：内容输入 -->
    <div class="generator-main">
      <h3>论文内容</h3>
      <div class="generator-form">
        <label>
          研究主题
          <input id="paperTopic" type="text" placeholder="输入研究主题" />
        </label>
        <label>
          大纲要点
          <textarea id="paperOutline" placeholder="输入大纲要点，每行一个"></textarea>
        </label>
        <label>
          代码片段（可选）
          <textarea id="paperCode" placeholder="粘贴相关代码片段"></textarea>
        </label>
        <button id="generatePaperButton" class="primary-button" type="button">
          生成论文
        </button>
      </div>
    </div>
    
    <!-- 右侧：预览 -->
    <div class="generator-preview">
      <div class="preview-header">
        <h3>生成结果</h3>
        <div class="preview-actions">
          <button id="exportMarkdownButton" class="secondary-button" type="button" hidden>
            导出 Markdown
          </button>
          <button id="exportPdfButton" class="secondary-button" type="button" hidden>
            导出 PDF
          </button>
        </div>
      </div>
      <div id="paperPreview" class="paper-preview">
        <p class="empty-preview">选择模板论文并填写内容后，点击"生成论文"按钮</p>
      </div>
    </div>
  </div>
</section>
```

- [ ] **步骤 3：添加论文生成界面样式**

在 `styles.css` 中添加：

```css
/* 论文生成界面 */
.generator-view {
  padding: 20px;
}

.generator-layout {
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: 20px;
  height: calc(100vh - 200px);
}

.generator-sidebar,
.generator-main,
.generator-preview {
  background: var(--surface);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid var(--line);
  overflow-y: auto;
}

.generator-sidebar h3,
.generator-main h3,
.generator-preview h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: var(--text);
}

.template-paper-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-paper-item {
  padding: 12px;
  background: var(--surface-strong);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.template-paper-item:hover {
  background: var(--teal-soft);
  border-color: var(--teal);
}

.template-paper-item.selected {
  background: var(--teal-soft);
  border-color: var(--teal);
}

.template-paper-item h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: var(--text);
}

.template-paper-item p {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.structure-preview {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.structure-preview h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--text);
}

.structure-item {
  padding: 8px 12px;
  background: var(--surface-strong);
  border-radius: 6px;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--muted);
}

.structure-item.level-1 {
  font-weight: 600;
  color: var(--text);
}

.structure-item.level-2 {
  padding-left: 24px;
}

.structure-item.level-3 {
  padding-left: 36px;
}

.generator-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.generator-form label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
  color: var(--text);
}

.generator-form input,
.generator-form textarea {
  padding: 12px;
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text);
  transition: all 0.2s ease;
}

.generator-form input:focus,
.generator-form textarea:focus {
  outline: none;
  border-color: var(--teal);
  box-shadow: 0 0 0 3px var(--teal-soft);
}

.generator-form textarea {
  min-height: 100px;
  resize: vertical;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.paper-preview {
  background: var(--surface-strong);
  border-radius: 8px;
  padding: 20px;
  min-height: 300px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
}

.paper-preview h1,
.paper-preview h2,
.paper-preview h3 {
  margin-top: 24px;
  margin-bottom: 12px;
  color: var(--text);
}

.paper-preview p {
  margin-bottom: 12px;
}

.paper-preview code {
  background: var(--surface);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.paper-preview pre {
  background: var(--surface);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
}

.paper-preview pre code {
  background: none;
  padding: 0;
}

.empty-preview {
  color: var(--muted);
  text-align: center;
  padding: 40px 20px;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .generator-layout {
    grid-template-columns: 250px 1fr 250px;
  }
}

@media (max-width: 980px) {
  .generator-layout {
    grid-template-columns: 1fr;
    height: auto;
  }
  
  .generator-sidebar,
  .generator-main,
  .generator-preview {
    min-height: 300px;
  }
}
```

- [ ] **步骤 4：添加论文生成 JavaScript 逻辑**

在 `app.js` 中添加：

```javascript
// 论文生成状态
state.generator = {
  selectedTemplate: null,
  structure: null,
  generatedContent: null
};

// 初始化论文生成界面
function initGeneratorView() {
  // 加载模板论文列表
  loadTemplatePapers();
  
  // 绑定生成按钮事件
  el.generatePaperButton.addEventListener('click', generatePaper);
  el.exportMarkdownButton.addEventListener('click', exportMarkdown);
  el.exportPdfButton.addEventListener('click', exportPdf);
}

// 加载模板论文列表
function loadTemplatePapers() {
  const container = el.templatePaperList;
  container.innerHTML = '';
  
  state.papers.forEach(paper => {
    const item = document.createElement('div');
    item.className = 'template-paper-item';
    item.dataset.paperId = paper.arxiv_id;
    item.innerHTML = `
      <h4>${escapeHtml(paper.title)}</h4>
      <p>${escapeHtml(paper.abstract?.slice(0, 100) || '')}...</p>
    `;
    item.addEventListener('click', () => selectTemplatePaper(paper.arxiv_id));
    container.appendChild(item);
  });
}

// 选择模板论文
async function selectTemplatePaper(paperId) {
  // 更新选中状态
  document.querySelectorAll('.template-paper-item').forEach(item => {
    item.classList.toggle('selected', item.dataset.paperId === paperId);
  });
  
  state.generator.selectedTemplate = paperId;
  
  // 分析论文结构
  try {
    const response = await fetch(`/api/papers/${encodeURIComponent(paperId)}/analyze-structure`);
    const data = await response.json();
    
    if (data.structure) {
      state.generator.structure = data.structure;
      renderStructurePreview(data.structure);
    }
  } catch (error) {
    showMessage('分析论文结构失败: ' + error.message, true);
  }
}

// 渲染结构预览
function renderStructurePreview(structure) {
  const container = el.structureContent;
  container.innerHTML = '';
  
  if (structure.sections) {
    structure.sections.forEach(section => {
      const item = document.createElement('div');
      item.className = `structure-item level-${section.level || 1}`;
      item.textContent = section.title;
      container.appendChild(item);
    });
  }
  
  el.structurePreview.hidden = false;
}

// 生成论文
async function generatePaper() {
  const topic = el.paperTopic.value.trim();
  const outline = el.paperOutline.value.trim().split('\n').filter(line => line.trim());
  const code = el.paperCode.value.trim();
  
  if (!topic) {
    showMessage('请输入研究主题', true);
    return;
  }
  
  if (!state.generator.selectedTemplate) {
    showMessage('请选择模板论文', true);
    return;
  }
  
  setBusy(true);
  showMessage('正在生成论文...');
  
  try {
    const response = await fetch(`/api/papers/${encodeURIComponent(state.generator.selectedTemplate)}/generate-paper`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, outline, code })
    });
    
    const data = await response.json();
    
    if (data.error) {
      throw new Error(data.error);
    }
    
    state.generator.generatedContent = data.content;
    renderPaperPreview(data.content);
    
    el.exportMarkdownButton.hidden = false;
    el.exportPdfButton.hidden = false;
    
    showMessage('论文生成完成！');
  } catch (error) {
    showMessage('生成论文失败: ' + error.message, true);
  } finally {
    setBusy(false);
  }
}

// 渲染论文预览
function renderPaperPreview(content) {
  const container = el.paperPreview;
  
  // 简单的 Markdown 渲染
  const html = content
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
  
  container.innerHTML = html;
}

// 导出 Markdown
function exportMarkdown() {
  if (!state.generator.generatedContent) return;
  
  const blob = new Blob([state.generator.generatedContent], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `generated-paper-${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// 导出 PDF
async function exportPdf() {
  showMessage('PDF 导出功能开发中...');
}

// 在 openView 函数中添加 generator 视图处理
function openView(view) {
  // ... 现有代码 ...
  
  if (view === 'generator') {
    initGeneratorView();
  }
}
```

- [ ] **步骤 5：测试论文生成功能**

运行应用并检查：
- 导航中是否显示"论文生成"选项
- 点击后是否显示三栏布局界面
- 选择模板论文是否正确显示结构预览
- 填写内容后点击生成是否正常工作
- 预览区域是否正确显示生成的论文

- [ ] **步骤 6：提交更改**

```bash
git add timepredict_agent/static/index.html timepredict_agent/static/app.js timepredict_agent/static/styles.css
git commit -m "feat: 添加论文生成前端界面"
```

---

## 任务 10：测试和优化

**文件：**
- Modify: `tests/test_paper_generation.py`

- [ ] **步骤 1：编写完整测试用例**

```python
# tests/test_paper_generation.py
import pytest
from timepredict_agent.agent import PaperAgent
from timepredict_agent.config import AgentConfig

def test_generate_paper_integration():
    """测试论文生成功能的完整流程"""
    config = AgentConfig()
    agent = PaperAgent(config)
    
    # 首先收集一些论文
    result = agent.collect(max_results=5)
    assert result.saved > 0
    
    # 获取第一篇论文作为模板
    papers = agent.store.list_papers(1)
    assert len(papers) > 0
    
    template_id = papers[0]['arxiv_id']
    
    # 生成论文
    try:
        result = agent.generate_paper(
            template_paper_id=template_id,
            topic="基于深度学习的时间序列预测",
            outline=["问题定义", "模型架构", "实验设计", "结果分析"]
        )
        
        assert result is not None
        assert 'paper_id' in result
        assert 'content' in result
        assert len(result['content']) > 0
    except RuntimeError as e:
        # LLM 不可用时跳过
        if "LLM" in str(e):
            pytest.skip("LLM not available")
        raise

def test_paper_structure_analysis():
    """测试论文结构分析"""
    from timepredict_agent.llm_summary import AnthropicSummaryClient
    
    client = AnthropicSummaryClient()
    if not client.available():
        pytest.skip("LLM not available")
    
    result = client.analyze_paper_structure(
        "Test Paper",
        "This is a test abstract.",
        "Introduction\nThis is the introduction.\n\nMethod\nThis is the method."
    )
    
    assert result is not None
    assert "sections" in result
```

- [ ] **步骤 2：运行完整测试**

```bash
python -m pytest tests/test_paper_generation.py -v
```

预期：所有测试通过

- [ ] **步骤 3：性能优化**

检查以下性能指标：
- 动画是否流畅（60fps）
- 页面加载时间是否合理
- API 响应时间是否在可接受范围内

- [ ] **步骤 4：用户体验优化**

- 添加加载状态指示器
- 优化错误提示信息
- 添加操作确认对话框

- [ ] **步骤 5：最终提交**

```bash
git add .
git commit -m "feat: 完成视觉增强和论文生成功能，通过所有测试"
```

---

## 验证清单

### 视觉效果验证
- [ ] 配色方案是否正确应用
- [ ] 渐变色效果是否可见
- [ ] 玻璃效果是否正常工作
- [ ] 交错淡入动画是否流畅
- [ ] 数字滚动动画是否正确
- [ ] 卡片翻转效果是否工作（如已实现）
- [ ] 视差滚动效果是否工作（如已实现）

### 论文生成功能验证
- [ ] 导航中是否显示"论文生成"选项
- [ ] 选择模板论文是否正确显示结构预览
- [ ] 填写内容后点击生成是否正常工作
- [ ] 预览区域是否正确显示生成的论文
- [ ] 导出 Markdown 功能是否正常
- [ ] 导出 PDF 功能是否正常（如已实现）

### 测试验证
- [ ] 所有单元测试是否通过
- [ ] 集成测试是否通过
- [ ] 性能测试是否达标

---

## 后续优化建议

### 短期优化（1个月内）
- 动画效果微调
- AI 生成质量优化
- 用户反馈收集

### 长期规划（3个月内）
- 更多论文模板
- 智能模板推荐
- 协作编辑功能
- 版本控制功能
