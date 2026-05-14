const state = {
  papers: [],
  selectedId: null,
  keyword: "",
  selectedIds: new Set(),
  status: null,
  activeView: "library",
};

const el = {
  databasePath: document.querySelector("#databasePath"),
  defaultRange: document.querySelector("#defaultRange"),
  llmStatus: document.querySelector("#llmStatus"),
  searchInput: document.querySelector("#searchInput"),
  maxResults: document.querySelector("#maxResults"),
  recentDays: document.querySelector("#recentDays"),
  addPaperButton: document.querySelector("#addPaperButton"),
  collectButton: document.querySelector("#collectButton"),
  exportButton: document.querySelector("#exportButton"),
  refreshButton: document.querySelector("#refreshButton"),
  paperList: document.querySelector("#paperList"),
  paperDetail: document.querySelector("#paperDetail"),
  message: document.querySelector("#message"),
  paperCount: document.querySelector("#paperCount"),
  highCount: document.querySelector("#highCount"),
  methodCount: document.querySelector("#methodCount"),
  latestDate: document.querySelector("#latestDate"),
};

const priorityLabel = {
  high: "高优先级",
  medium: "中优先级",
  low: "低优先级",
};

const sourceLabel = {
  arxiv: "arXiv",
  semantic_scholar: "Semantic Scholar",
  openalex: "OpenAlex",
  ieee_xplore: "IEEE Xplore",
  google_scholar: "Google Scholar HTML",
  manual: "手动加入",
};

init();

function init() {
  bindEvents();
  loadStatus();
  loadPapers();
}

function bindEvents() {
  el.refreshButton.addEventListener("click", () => loadPapers());
  el.addPaperButton.addEventListener("click", openManualAddPanel);
  el.collectButton.addEventListener("click", collectPapers);
  el.exportButton.addEventListener("click", exportReport);
  el.searchInput.addEventListener("input", debounce(() => {
    state.keyword = el.searchInput.value.trim();
    state.activeView = "library";
    selectNav("library");
    loadPapers();
  }, 280));

  document.querySelectorAll("[data-keyword]").forEach((button) => {
    button.addEventListener("click", () => {
      el.searchInput.value = button.dataset.keyword;
      state.keyword = button.dataset.keyword;
      state.activeView = "library";
      selectNav("library");
      loadPapers();
    });
  });

  document.querySelectorAll("[data-nav]").forEach((button) => {
    button.addEventListener("click", () => openView(button.dataset.nav));
  });
}

async function loadStatus() {
  try {
    const status = await getJson("/api/status");
    state.status = status;
    renderStatus(status);
    if (state.papers.length || state.activeView !== "library") {
      render();
    }
  } catch (error) {
    el.databasePath.textContent = "加载失败";
    el.defaultRange.textContent = "加载失败";
    el.llmStatus.textContent = "加载失败";
    showMessage(`状态读取失败：${error.message}`, true);
  }
}

function renderStatus(status) {
  el.databasePath.textContent = status.database_path || "未读取到路径";
  el.defaultRange.textContent = `${status.max_results} 篇 / ${status.recent_days} 天`;
  el.llmStatus.textContent = status.llm_available ? `已启用 ${status.llm_model}` : "未配置 token";
  el.maxResults.value = status.max_results;
  el.recentDays.value = status.recent_days;
  document.querySelectorAll('input[name="source"]').forEach((input) => {
    input.checked = (status.sources || []).includes(input.value);
  });
}

async function loadPapers() {
  setBusy(true);
  try {
    const data = await getJson(`/api/papers?limit=80&keyword=${encodeURIComponent(state.keyword)}`);
    state.papers = data.papers || [];
    state.selectedIds = new Set(Array.from(state.selectedIds).filter((id) => state.papers.some((paper) => paper.arxiv_id === id)));

    if (!state.papers.some((paper) => paper.arxiv_id === state.selectedId)) {
      state.selectedId = state.papers[0]?.arxiv_id || null;
    }

    render();
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function collectPapers() {
  const sources = selectedSources();
  if (!sources.length) {
    showMessage("请至少选择一个论文来源。", true);
    return;
  }

  setBusy(true);
  showMessage(`正在从 ${sources.map((source) => sourceLabel[source] || source).join("、")} 收集论文，请稍等。`);
  try {
    const data = await postJson("/api/collect", {
      max_results: el.maxResults.value,
      recent_days: el.recentDays.value,
      sources,
    });

    await loadPapers();
    state.selectedId = state.papers[0]?.arxiv_id || state.selectedId;
    state.activeView = "library";
    selectNav("library");
    render();

    const errors = Object.entries(data.result.errors || {}).map(([source, message]) => `${sourceLabel[source] || source}: ${message}`);
    const suffix = errors.length ? ` 部分来源失败：${errors.join("；")}` : "";
    showMessage(`收集完成：获取 ${data.result.fetched} 篇，写入 ${data.result.saved} 篇。${suffix}`);
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function exportReport() {
  setBusy(true);
  try {
    const data = await postJson("/api/export", { output: "reports/papers.md", limit: 80 });
    state.activeView = "report";
    selectNav("report");
    renderReportPanel(data);
    showMessage(`报告已导出：${data.path}`);
    window.open(data.url, "_blank", "noopener");
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

function openView(view) {
  state.activeView = view;
  selectNav(view);
  if (view === "library") {
    renderDetail();
  } else if (view === "report") {
    renderReportPanel();
  } else if (view === "settings") {
    renderSettingsPanel();
  }
}

function openManualAddPanel() {
  state.activeView = "manual";
  document.querySelectorAll("[data-nav]").forEach((button) => button.classList.remove("active"));
  renderManualAddPanel();
}

function selectNav(view) {
  document.querySelectorAll("[data-nav]").forEach((button) => {
    button.classList.toggle("active", button.dataset.nav === view);
  });
}

function render() {
  renderStats();
  renderList();
  if (state.activeView === "report") {
    renderReportPanel();
  } else if (state.activeView === "settings") {
    renderSettingsPanel();
  } else {
    renderDetail();
  }
}

function renderStats() {
  const methodTags = new Set();
  let high = 0;
  for (const paper of state.papers) {
    if (paper.summary.reading_priority === "high") high += 1;
    for (const tag of paper.summary.method_tags || []) methodTags.add(tag);
  }
  el.paperCount.textContent = state.papers.length;
  el.highCount.textContent = high;
  el.methodCount.textContent = methodTags.size;
  el.latestDate.textContent = state.papers[0]?.published?.slice(0, 10) || "--";
}

function renderList() {
  if (!state.papers.length) {
    el.paperList.innerHTML = `
      <div class="empty-list">
        <p class="paper-title">暂无论文</p>
        <p class="paper-meta">点击“多源收集”开始建立本地论文库；也可以先调整关键词、数量和时间范围。</p>
      </div>
    `;
    return;
  }

  const rows = state.papers.map((paper) => renderPaperRow(paper)).join("");
  const batchBar = state.selectedIds.size ? renderBatchBar() : "";
  el.paperList.innerHTML = rows + batchBar;

  el.paperList.querySelectorAll("[data-check]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => togglePaperSelection(checkbox.dataset.check, checkbox.checked));
  });
  el.paperList.querySelectorAll("[data-select-paper]").forEach((content) => {
    content.addEventListener("click", () => {
      state.selectedId = content.dataset.selectPaper;
      state.activeView = "library";
      selectNav("library");
      render();
    });
    content.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        content.click();
      }
    });
  });
  el.paperList.querySelectorAll("[data-batch]").forEach((button) => {
    button.addEventListener("click", () => runBatchAction(button.dataset.batch));
  });
}

function renderPaperRow(paper) {
  const priority = paper.summary.reading_priority || "medium";
  const tags = [priorityLabel[priority] || priority, ...(paper.summary.method_tags || []).slice(0, 3)];
  const isSelected = state.selectedIds.has(paper.arxiv_id);
  const isActive = paper.arxiv_id === state.selectedId && state.activeView === "library";
  return `
    <article class="paper-row ${isActive ? "selected" : ""}">
      <label class="paper-checkbox" title="选择用于批量操作">
        <input type="checkbox" data-check="${escapeAttribute(paper.arxiv_id)}" ${isSelected ? "checked" : ""} />
      </label>
      <div class="paper-content" data-select-paper="${escapeAttribute(paper.arxiv_id)}" role="button" tabindex="0">
        <p class="paper-title">${escapeHtml(paper.title)}</p>
        <div class="paper-meta">
          <span>${escapeHtml(sourceLabel[paper.source] || paper.source || "未知来源")}</span>
          <span>${escapeHtml(paper.arxiv_id)}</span>
          <span>引用 ${paper.citation_count || 0}</span>
          <span>${escapeHtml((paper.authors || []).slice(0, 3).join(", "))}</span>
        </div>
        <div class="tag-row">${tags.map((tag, index) => `<span class="tag ${index === 0 ? `priority-${priority}` : ""}">${escapeHtml(tag)}</span>`).join("")}</div>
      </div>
      <time class="paper-date">${escapeHtml((paper.published || "").slice(0, 10))}</time>
    </article>
  `;
}

function renderBatchBar() {
  const canCompare = state.selectedIds.size >= 2;
  return `
    <div class="batch-bar">
      <span>已选 ${state.selectedIds.size} 篇</span>
      <button data-batch="llm-summary" type="button" ${state.status?.llm_available ? "" : "disabled title=\"LLM 未配置\""}>批量 LLM 解读</button>
      <button data-batch="review" type="button">生成综述</button>
      <button data-batch="download" type="button">批量下载 PDF</button>
      <button data-batch="compare" type="button" ${canCompare ? "" : "disabled"}>对比论文</button>
      <button data-batch="clear" type="button">取消选择</button>
    </div>
  `;
}

function renderManualAddPanel() {
  el.paperDetail.className = "paper-detail";
  el.paperDetail.innerHTML = `
    <h2 class="detail-title">添加已读论文</h2>
    <p class="panel-note">把你已经看过、但自动收集没有覆盖到的论文加入本地论文库。保存后会自动标记为“已读”和“手动加入”。</p>
    <form id="manualPaperForm" class="manual-form">
      <label>
        标题
        <input name="title" required placeholder="论文标题" />
      </label>
      <label>
        作者
        <input name="authors" placeholder="多个作者用逗号分隔" />
      </label>
      <div class="manual-form-grid">
        <label>
          年份
          <input name="year" inputmode="numeric" placeholder="2024" />
        </label>
        <label>
          DOI
          <input name="doi" placeholder="可选" />
        </label>
      </div>
      <label>
        论文页面
        <input name="entry_url" placeholder="https://..." />
      </label>
      <label>
        PDF 链接
        <input name="pdf_url" placeholder="https://..." />
      </label>
      <label>
        摘要或你的阅读笔记
        <textarea name="abstract" rows="8" placeholder="粘贴摘要，或者写你已经读过后的简要笔记"></textarea>
      </label>
      <label>
        标签
        <input name="tags" value="已读,手动加入" placeholder="例如：事件序列预测,剩余时间预测" />
      </label>
      <div class="report-actions">
        <button type="submit">保存到论文库</button>
        <button type="button" data-manual-cancel>取消</button>
      </div>
    </form>
  `;
  el.paperDetail.querySelector("#manualPaperForm").addEventListener("submit", submitManualPaper);
  el.paperDetail.querySelector("[data-manual-cancel]").addEventListener("click", () => {
    state.activeView = "library";
    selectNav("library");
    renderDetail();
  });
}

async function submitManualPaper(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  setBusy(true);
  try {
    const data = await postJson("/api/papers/manual", payload);
    state.selectedId = data.paper.arxiv_id;
    state.keyword = "";
    el.searchInput.value = "";
    state.activeView = "library";
    selectNav("library");
    await loadPapers();
    showMessage(`已加入论文库：${data.paper.title}`);
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

function togglePaperSelection(id, checked) {
  if (checked) {
    state.selectedIds.add(id);
  } else {
    state.selectedIds.delete(id);
  }
  renderList();
}

async function runBatchAction(action) {
  const ids = Array.from(state.selectedIds);
  if (action === "clear") {
    state.selectedIds.clear();
    render();
    return;
  }
  if (action === "compare") {
    renderComparison();
    return;
  }
  if (action === "review") {
    await generateReview(ids);
    return;
  }
  if (!ids.length) return;
  if (action === "llm-summary" && !state.status?.llm_available) {
    showMessage("LLM 未配置，无法批量生成深度解读。请先在配置面板检查 token。", true);
    return;
  }

  const endpoint = action === "download" ? "/api/papers/batch-download" : "/api/papers/batch-llm-summary";
  const label = action === "download" ? "下载 PDF" : "生成 LLM 解读";
  setBusy(true);
  showMessage(`正在为 ${ids.length} 篇论文批量${label}。`);
  try {
    const data = await postJson(endpoint, { paper_ids: ids });
    const ok = (data.results || []).filter((item) => item.status === "ok").length;
    const failed = (data.results || []).filter((item) => item.status !== "ok");
    await loadPapers();
    showMessage(`批量任务完成：${ok}/${ids.length} 篇成功。${failed.length ? `失败 ${failed.length} 篇，可稍后重试。` : ""}`, failed.length > 0);
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function generateReview(ids) {
  if (ids.length < 2) {
    showMessage("请至少选择 2 篇论文来生成综述。", true);
    return;
  }
  const topic = state.keyword || "事件序列预测与预测性流程监控";
  setBusy(true);
  showMessage(`正在基于 ${ids.length} 篇论文生成中文综述草稿。`);
  try {
    const data = await postJson("/api/review", {
      paper_ids: ids,
      topic,
      prefer_llm: true,
    });
    state.activeView = "library";
    selectNav("library");
    renderReviewPanel(data);
    const suffix = data.used_llm ? `已使用 ${state.status?.llm_model || "LLM"}。` : "已使用本地结构化模板。";
    showMessage(`综述草稿已生成：${data.path}。${suffix}${data.llm_error ? ` LLM 失败原因：${data.llm_error}` : ""}`, Boolean(data.llm_error));
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

function renderReviewPanel(data) {
  el.paperDetail.className = "paper-detail review-detail";
  el.paperDetail.innerHTML = `
    <h2 class="detail-title">论文综述草稿</h2>
    <p class="panel-note">基于已选 ${data.paper_count} 篇论文生成。草稿保留 [P1] 这类引用编号，建议你后续按学校或期刊格式改写、补充正式参考文献。</p>
    <div class="report-actions">
      <button data-review-action="copy" type="button">复制草稿</button>
      <a href="${escapeAttribute(data.url)}" target="_blank" rel="noopener">打开 Markdown</a>
    </div>
    <textarea class="review-output" readonly>${escapeHtml(data.markdown)}</textarea>
  `;
  el.paperDetail.querySelector("[data-review-action='copy']").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(data.markdown);
      showMessage("综述草稿已复制到剪贴板。");
    } catch (error) {
      showMessage("浏览器不允许直接复制，你可以手动选中下方文本复制。", true);
    }
  });
}

function renderComparison() {
  const papers = state.papers.filter((paper) => state.selectedIds.has(paper.arxiv_id));
  if (papers.length < 2) {
    showMessage("请至少选择 2 篇论文进行对比。", true);
    return;
  }

  state.activeView = "library";
  selectNav("library");
  el.paperDetail.className = "paper-detail";
  const fields = [
    { key: "deep_summary", label: "深度总结" },
    { key: "innovation_points", label: "创新点", isList: true },
    { key: "method", label: "方法" },
    { key: "method_comparison", label: "方法对比" },
    { key: "experiments", label: "实验" },
    { key: "datasets_used", label: "数据集", isList: true },
    { key: "metrics_used", label: "指标", isList: true },
    { key: "limitations", label: "局限性" },
    { key: "future_directions", label: "未来方向" },
  ];

  el.paperDetail.innerHTML = `
    <h2 class="detail-title">论文对比 (${papers.length} 篇)</h2>
    <p class="panel-note">对比内容来自本地摘要和 LLM 深度解读；没有生成过 LLM 解读的维度会显示较少。</p>
    <div class="comparison-table" style="--cols:${papers.length}">
      <div class="comparison-header">
        <div class="comparison-label">维度</div>
        ${papers.map((paper) => `<div class="comparison-cell-title">${escapeHtml(paper.title.slice(0, 56))}</div>`).join("")}
      </div>
      ${fields.map((field) => renderComparisonRow(field, papers)).join("")}
    </div>
  `;
}

function renderComparisonRow(field, papers) {
  const hasAny = papers.some((paper) => {
    const value = paper.summary[field.key];
    return field.isList ? value && value.length : value;
  });
  if (!hasAny) return "";

  return `
    <div class="comparison-row">
      <div class="comparison-label">${escapeHtml(field.label)}</div>
      ${papers.map((paper) => {
        const value = paper.summary[field.key];
        if (field.isList) {
          return `<div class="comparison-cell">${(value || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join(" ") || "--"}</div>`;
        }
        return `<div class="comparison-cell">${escapeHtml(value) || "--"}</div>`;
      }).join("")}
    </div>
  `;
}

function renderDetail() {
  const paper = state.papers.find((item) => item.arxiv_id === state.selectedId);
  if (!paper) {
    el.paperDetail.className = "paper-detail empty";
    el.paperDetail.innerHTML = `
      <p class="empty-title">选择一篇论文</p>
      <p>左侧列表会展示收集到的论文，点击后可以查看中文摘要、关键要点、相关性判断、PDF 链接和引用关系。</p>
    `;
    return;
  }

  el.paperDetail.className = "paper-detail";
  el.paperDetail.innerHTML = `
    <h2 class="detail-title">${escapeHtml(paper.title)}</h2>
    <div class="paper-meta">
      <span>${escapeHtml((paper.published || "").slice(0, 10))}</span>
      <span>${escapeHtml(paper.arxiv_id)}</span>
      <span>${escapeHtml(sourceLabel[paper.source] || paper.source || "未知来源")}</span>
      <span>引用 ${paper.citation_count || 0}</span>
      <span>${escapeHtml((paper.categories || []).join(", "))}</span>
    </div>
    <div class="tag-row">
      <span class="tag priority-${paper.summary.reading_priority}">${escapeHtml(priorityLabel[paper.summary.reading_priority] || paper.summary.reading_priority)}</span>
      ${(paper.tags || paper.summary.method_tags || []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
      ${paper.local_pdf_path ? `<span class="tag">已下载 PDF</span>` : ""}
    </div>
    <div class="detail-actions">
      <a href="${escapeAttribute(paper.entry_url)}" target="_blank" rel="noopener">论文页面</a>
      <a href="${escapeAttribute(paper.pdf_url)}" target="_blank" rel="noopener">在线 PDF</a>
      <button data-action="download" data-id="${escapeAttribute(paper.arxiv_id)}" type="button">下载全文</button>
      <button data-action="local-summary" data-id="${escapeAttribute(paper.arxiv_id)}" type="button">本地中文解读</button>
      <button data-action="llm-summary" data-id="${escapeAttribute(paper.arxiv_id)}" type="button" ${state.status?.llm_available ? "" : "disabled"}>LLM 深度解读</button>
      <button data-action="enrich" data-id="${escapeAttribute(paper.arxiv_id)}" type="button">引用分析</button>
      <button data-action="recommend" data-id="${escapeAttribute(paper.arxiv_id)}" type="button">相似推荐</button>
    </div>
    ${state.status?.llm_available ? "" : `<p class="panel-note warning">LLM 未配置，深度解读按钮会保持不可用。请在配置面板检查 .env。</p>`}
    <section class="detail-block">
      <h3>摘要速览</h3>
      <p>${escapeHtml(paper.summary.short_summary || "暂无摘要。")}</p>
    </section>
    <section class="detail-block">
      <h3>相关性判断</h3>
      <p>${escapeHtml(paper.summary.relevance || "暂无相关性判断。")}</p>
    </section>
    ${renderDeepSummary(paper.summary)}
    <section class="detail-block">
      <h3>关键要点</h3>
      ${renderListItems(paper.summary.key_points)}
    </section>
    <section class="detail-block">
      <h3>作者</h3>
      <p>${escapeHtml((paper.authors || []).join(", ") || "未知作者")}</p>
    </section>
    ${renderRelations("相似论文推荐", paper.related)}
    ${renderRelations("近期引用", paper.citations)}
    ${renderRelations("参考文献", paper.references)}
  `;

  el.paperDetail.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => runPaperAction(button.dataset.action, button.dataset.id));
  });
}

async function runPaperAction(action, paperId) {
  setBusy(true);
  try {
    if (action === "download") {
      const data = await postJson(`/api/papers/${encodeURIComponent(paperId)}/download`, {});
      const paper = state.papers.find((item) => item.arxiv_id === paperId);
      if (paper) paper.local_pdf_path = data.path;
      render();
      showMessage(`全文已下载：${data.path}`);
      return;
    }
    if (action === "enrich") {
      const data = await postJson(`/api/papers/${encodeURIComponent(paperId)}/enrich`, {});
      updatePaper(data.paper);
      showMessage("引用关系已更新。");
      return;
    }
    if (action === "llm-summary") {
      showMessage("正在生成 LLM 深度解读，可能需要几十秒。");
      const data = await postJson(`/api/papers/${encodeURIComponent(paperId)}/llm-summary`, {});
      updatePaper(data.paper);
      showMessage("LLM 深度解读已生成。");
      return;
    }
    if (action === "local-summary") {
      const data = await postJson(`/api/papers/${encodeURIComponent(paperId)}/local-summary`, {});
      updatePaper(data.paper);
      showMessage("本地中文解读已刷新。");
      return;
    }
    if (action === "recommend") {
      const data = await postJson(`/api/papers/${encodeURIComponent(paperId)}/recommend`, { limit: 8 });
      const paper = state.papers.find((item) => item.arxiv_id === paperId);
      if (paper) paper.related = data.related;
      render();
      showMessage("相似论文推荐已生成。");
    }
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

function renderReportPanel(lastReport) {
  el.paperDetail.className = "paper-detail";
  const reportUrl = lastReport?.url || "/reports/papers.md";
  el.paperDetail.innerHTML = `
    <h2 class="detail-title">阅读报告</h2>
    <p class="panel-note">这里会把当前论文库整理成 Markdown 阅读清单，包含优先级、中文摘要、关键要点和深度解读字段。</p>
    <div class="report-actions">
      <button data-report-action="export" type="button">重新生成报告</button>
      <a href="${escapeAttribute(reportUrl)}" target="_blank" rel="noopener">打开最近报告</a>
    </div>
    <section class="detail-block">
      <h3>报告内容</h3>
      <ul>
        <li>按最新发布时间整理论文。</li>
        <li>保留本地摘要、LLM 深度解读、标签和优先级。</li>
        <li>适合复制进笔记软件或继续整理文献综述。</li>
      </ul>
    </section>
  `;
  el.paperDetail.querySelector("[data-report-action='export']").addEventListener("click", exportReport);
}

function renderSettingsPanel() {
  const status = state.status || {};
  const sources = selectedSources();
  el.paperDetail.className = "paper-detail";
  el.paperDetail.innerHTML = `
    <h2 class="detail-title">配置与功能状态</h2>
    <p class="panel-note">这里展示当前前端会使用的真实配置，修改数量、天数和来源后点击“多源收集”即可生效。</p>
    <section class="detail-block">
      <h3>本地路径</h3>
      <p>数据库：${escapeHtml(status.database_path || "未读取")}</p>
      <p>报告目录：${escapeHtml(status.report_dir || "未读取")}</p>
      <p>PDF 目录：${escapeHtml(status.pdf_dir || "未读取")}</p>
    </section>
    <section class="detail-block">
      <h3>LLM</h3>
      <p>${status.llm_available ? `已连接模型：${escapeHtml(status.llm_model)}` : "未检测到可用 token，LLM 深度解读不可用。"}</p>
    </section>
    <section class="detail-block">
      <h3>本次收集参数</h3>
      <p>数量：${escapeHtml(el.maxResults.value)} 篇；天数：${escapeHtml(el.recentDays.value)} 天；来源：${escapeHtml(sources.map((source) => sourceLabel[source] || source).join("、") || "未选择")}</p>
    </section>
    <section class="detail-block">
      <h3>功能可用性</h3>
      <ul>
        <li>多源收集：已接入 arXiv、Semantic Scholar、OpenAlex、IEEE Xplore 公开检索。</li>
        <li>Google Scholar：支持保存结果页 HTML 后本地解析，默认读取 data/google_scholar.html。</li>
        <li>全文下载：对有 PDF 链接的论文可用。</li>
        <li>引用分析：依赖 Semantic Scholar，可遇到公共接口限流。</li>
        <li>相似推荐：使用本地论文库做相似度排序。</li>
      </ul>
    </section>
  `;
}

function renderDeepSummary(summary) {
  if (!summary.deep_summary && !summary.contribution && !summary.method && !summary.llm_error) return "";
  if (summary.llm_error) {
    return `
      <section class="detail-block">
        <h3>LLM 深度解读</h3>
        <p class="panel-note warning">${escapeHtml(summary.llm_error)}</p>
      </section>
    `;
  }

  const rows = [
    ["深度总结", summary.deep_summary],
    ["主要贡献", summary.contribution],
    ["方法拆解", summary.method],
    ["方法对比", summary.method_comparison],
    ["实验结论", summary.experiments],
    ["局限与改进", summary.limitations],
    ["未来方向", summary.future_directions],
    ["阅读建议", summary.reading_notes],
  ].filter(([, value]) => value);

  return `
    <section class="detail-block">
      <h3>LLM 深度解读 ${summary.llm_model ? `<span class="paper-meta">${escapeHtml(summary.llm_model)}</span>` : ""}</h3>
      ${rows.map(([title, value]) => `<p><strong>${escapeHtml(title)}：</strong>${escapeHtml(value)}</p>`).join("")}
    </section>
    ${renderOptionalListBlock("核心创新点", summary.innovation_points)}
    ${renderExperimentBlock(summary)}
  `;
}

function renderExperimentBlock(summary) {
  const datasets = summary.datasets_used || [];
  const metrics = summary.metrics_used || [];
  if (!datasets.length && !metrics.length) return "";
  return `
    <section class="detail-block">
      <h3>实验详情</h3>
      ${datasets.length ? `<p><strong>数据集：</strong>${datasets.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join(" ")}</p>` : ""}
      ${metrics.length ? `<p><strong>评价指标：</strong>${metrics.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join(" ")}</p>` : ""}
    </section>
  `;
}

function renderOptionalListBlock(title, items = []) {
  if (!items.length) return "";
  return `
    <section class="detail-block">
      <h3>${escapeHtml(title)}</h3>
      ${renderListItems(items)}
    </section>
  `;
}

function renderListItems(items = []) {
  if (!items.length) return "<p>暂无内容。</p>";
  return `<ul>${items.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul>`;
}

function updatePaper(paper) {
  const index = state.papers.findIndex((item) => item.arxiv_id === paper.arxiv_id);
  if (index >= 0) {
    state.papers[index] = paper;
  }
  render();
}

function renderRelations(title, items = []) {
  if (!items.length) return "";
  return `
    <section class="detail-block">
      <h3>${escapeHtml(title)}</h3>
      <ul>${items.slice(0, 8).map((item) => `<li><a href="${escapeAttribute(item.url || "#")}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a> <span class="paper-meta">${escapeHtml(item.reason || item.source || "")}</span></li>`).join("")}</ul>
    </section>
  `;
}

async function getJson(url) {
  let response;
  try {
    response = await fetch(url);
  } catch (error) {
    throw new Error(`无法连接本地服务，请确认 http://127.0.0.1:8765 正在运行。原始错误：${error.message}`);
  }
  return parseResponse(response);
}

async function postJson(url, payload) {
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new Error(`请求被中断，可能是本地服务重启、接口超时或网络被拦截。请刷新后重试。原始错误：${error.message}`);
  }
  return parseResponse(response);
}

async function parseResponse(response) {
  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    throw new Error(`接口返回不是 JSON：${response.status}`);
  }
  if (!response.ok) {
    throw new Error(data.error || `请求失败：${response.status}`);
  }
  return data;
}

function showMessage(text, isError = false) {
  el.message.hidden = false;
  el.message.textContent = text;
  el.message.classList.toggle("error", isError);
}

function setBusy(isBusy) {
  document.body.classList.toggle("loading", isBusy);
  [el.addPaperButton, el.collectButton, el.exportButton, el.refreshButton].forEach((button) => {
    button.disabled = isBusy;
  });
}

function selectedSources() {
  return Array.from(document.querySelectorAll('input[name="source"]:checked')).map((input) => input.value);
}

function debounce(fn, delay) {
  let timer = null;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), delay);
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
