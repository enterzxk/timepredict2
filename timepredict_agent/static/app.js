const MAX_EXPERT_SESSIONS = 60;

const state = {
  papers: [],
  selectedId: null,
  keyword: "",
  selectedIds: new Set(),
  status: null,
  activeView: "library",
  detailHistory: [],
  dailyRecommendations: null,
  dailyLoading: false,
  dailyError: "",
  expertPapersCollapsed: false,
  expertSessions: [],
  expertSessionsLoaded: false,
  expertSessionsLoading: false,
  activeExpertSessionId: null,
  agentStatus: "",
  expertImageAttachments: [],
  generator: {
    selectedTemplate: null,
    structure: null,
    generatedContent: null,
  },
};

const el = {
  workspace: document.querySelector(".workspace"),
  databasePath: document.querySelector("#databasePath"),
  defaultRange: document.querySelector("#defaultRange"),
  llmStatus: document.querySelector("#llmStatus"),
  searchInput: document.querySelector("#searchInput"),
  searchClear: document.querySelector("#searchClear"),
  maxResults: document.querySelector("#maxResults"),
  recentDays: document.querySelector("#recentDays"),
  viewTitle: document.querySelector("#viewTitle"),
  viewSubtitle: document.querySelector("#viewSubtitle"),
  listTitle: document.querySelector("#listTitle"),
  listSubtitle: document.querySelector("#listSubtitle"),
  contentGrid: document.querySelector("#contentGrid"),
  addPaperButton: document.querySelector("#addPaperButton"),
  uploadPaperButton: document.querySelector("#uploadPaperButton"),
  collectButton: document.querySelector("#collectButton"),
  exportButton: document.querySelector("#exportButton"),
  refreshButton: document.querySelector("#refreshButton"),
  expertPaperPanelToggle: document.querySelector("#expertPaperPanelToggle"),
  expertPaperRail: document.querySelector("#expertPaperRail"),
  paperList: document.querySelector("#paperList"),
  paperDetail: document.querySelector("#paperDetail"),
  message: document.querySelector("#message"),
  paperCount: document.querySelector("#paperCount"),
  highCount: document.querySelector("#highCount"),
  methodCount: document.querySelector("#methodCount"),
  latestDate: document.querySelector("#latestDate"),
  themeToggle: document.querySelector("#themeToggle"),
  themeLabel: document.querySelector("#themeLabel"),
  mobileMenuToggle: document.querySelector("#mobileMenuToggle"),
  sidebarOverlay: document.querySelector("#sidebarOverlay"),
  sidebar: document.querySelector(".sidebar"),
  generatorView: document.getElementById("generatorView"),
  templatePaperList: document.getElementById("templatePaperList"),
  structurePreview: document.getElementById("structurePreview"),
  structureContent: document.getElementById("structureContent"),
  paperTopic: document.getElementById("paperTopic"),
  paperOutline: document.getElementById("paperOutline"),
  paperCode: document.getElementById("paperCode"),
  generatePaperButton: document.getElementById("generatePaperButton"),
  exportMarkdownButton: document.getElementById("exportMarkdownButton"),
  exportPdfButton: document.getElementById("exportPdfButton"),
  paperPreview: document.getElementById("paperPreview"),
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
  uploaded: "上传论文",
};

const viewCopy = {
  library: {
    title: "论文库",
    subtitle: "先收集候选论文，再按相关性、方法标签、引用和解读完整度筛出值得精读的内容。",
    listTitle: "论文列表",
    listSubtitle: "按发布时间倒序排列",
  },
  triage: {
    title: "速筛看板",
    subtitle: "把论文变成可判断的阅读队列：先看是否相关、是否有方法创新、是否值得进入精读。",
    listTitle: "候选论文",
    listSubtitle: "点击论文仍可查看详情，右侧会给出精读优先级",
  },
  discovery: {
    title: "发现扩展",
    subtitle: "围绕你的研究方向扩展检索词和来源，减少“收集到的论文太少或太窄”的问题。",
    listTitle: "当前结果",
    listSubtitle: "用右侧检索方案继续扩展论文池",
  },
  daily: {
    title: "每日推荐",
    subtitle: "每天更新一组 AI、深度学习和机器学习方向的高质量候选论文，优先顶会顶刊和高引用。",
    listTitle: "本地论文库",
    listSubtitle: "每日推荐可加入这里继续精读",
  },
  expert: {
    title: "论文专家",
    subtitle: "把当前论文交给专家对话页，专门问方法思想、创新点、实验结果和 GitHub 复现。",
    listTitle: "选择咨询论文",
    listSubtitle: "点击左侧论文后，右侧专家页会切换到这篇论文",
  },
  report: {
    title: "阅读报告",
    subtitle: "把筛选后的论文整理成 Markdown 清单或综述草稿，方便后续写作。",
    listTitle: "报告素材",
    listSubtitle: "可勾选一篇或多篇论文生成综述",
  },
  settings: {
    title: "配置",
    subtitle: "查看本地路径、来源、LLM 可用性和收集参数。",
    listTitle: "配置关联论文",
    listSubtitle: "左侧保留论文列表，方便随时回到阅读对象",
  },
  manual: {
    title: "添加已读论文",
    subtitle: "把自动检索没覆盖到的重要论文补进本地库。",
    listTitle: "已有论文",
    listSubtitle: "保存后会回到论文库",
  },
  upload: {
    title: "上传论文",
    subtitle: "上传 PDF 后自动入库、提取全文，并基于这篇论文推荐相似论文。",
    listTitle: "已有论文",
    listSubtitle: "上传完成后会自动选中新论文",
  },
  generator: {
    title: "论文生成",
    subtitle: "选择模板论文结构，填写研究主题和大纲，自动生成论文草稿。",
    listTitle: "模板论文",
    listSubtitle: "点击论文查看其结构",
  },
};

const discoveryQueries = [
  {
    label: "预测性流程监控",
    query: "predictive process monitoring event log transformer remaining time",
    note: "适合找流程挖掘、下一活动预测、剩余时间预测的综合论文。",
  },
  {
    label: "增量事件日志",
    query: "incremental event log prediction online learning process mining",
    note: "适合找在线更新、概念漂移、持续学习相关工作。",
  },
  {
    label: "剩余时间预测",
    query: "business process remaining time prediction deep learning benchmark",
    note: "适合找与你当前题目最贴近的业务流程剩余时间预测论文。",
  },
  {
    label: "方法基线",
    query: "next activity prediction event log LSTM Transformer benchmark",
    note: "适合补充模型对比、baseline 和实验设置。",
  },
];

init();

function init() {
  initTheme();
  bindEvents();
  loadStatus();
  loadPapers();
}

function initTheme() {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeUI(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
  updateThemeUI(next);
}

function updateThemeUI(theme) {
  if (el.themeLabel) {
    el.themeLabel.textContent = theme === "dark" ? "浅色模式" : "深色模式";
  }
}

function toggleMobileMenu() {
  el.sidebar?.classList.toggle("open");
  el.sidebarOverlay?.classList.toggle("active");
}

function closeMobileMenu() {
  el.sidebar?.classList.remove("open");
  el.sidebarOverlay?.classList.remove("active");
}

function bindEvents() {
  el.refreshButton.addEventListener("click", () => loadPapers());
  el.addPaperButton.addEventListener("click", openManualAddPanel);
  el.uploadPaperButton.addEventListener("click", openUploadPanel);
  el.collectButton.addEventListener("click", collectPapers);
  el.exportButton.addEventListener("click", exportReport);
  el.expertPaperPanelToggle?.addEventListener("click", toggleExpertPaperPanel);
  el.expertPaperRail?.addEventListener("click", toggleExpertPaperPanel);
  el.themeToggle?.addEventListener("click", toggleTheme);

  el.mobileMenuToggle?.addEventListener("click", toggleMobileMenu);
  el.sidebarOverlay?.addEventListener("click", closeMobileMenu);
  el.searchInput.addEventListener("input", debounce(() => {
    state.keyword = el.searchInput.value.trim();
    state.activeView = "library";
    selectNav("library");
    loadPapers();
  }, 280));

  el.searchInput.addEventListener("input", () => {
    if (el.searchClear) {
      el.searchClear.hidden = !el.searchInput.value.trim();
    }
  });

  el.searchClear?.addEventListener("click", () => {
    el.searchInput.value = "";
    state.keyword = "";
    if (el.searchClear) el.searchClear.hidden = true;
    state.activeView = "library";
    selectNav("library");
    loadPapers();
  });

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
    button.addEventListener("click", () => {
      openView(button.dataset.nav);
      closeMobileMenu();
    });
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "k") {
      event.preventDefault();
      el.searchInput.focus();
      el.searchInput.select();
    }
    if (event.key === "Escape") {
      if (!el.message.hidden) {
        el.message.hidden = true;
      }
    }
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      const form = el.paperDetail?.querySelector("[data-expert-form]");
      if (form && document.activeElement?.closest("[data-expert-form]")) {
        event.preventDefault();
        form.dispatchEvent(new Event("submit", { cancelable: true }));
      }
    }
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
    if (el.databasePath) el.databasePath.textContent = "加载失败";
    if (el.defaultRange) el.defaultRange.textContent = "加载失败";
    if (el.llmStatus) el.llmStatus.textContent = "加载失败";
    showMessage(`状态读取失败：${error.message}`, true);
  }
}

function renderStatus(status) {
  if (el.databasePath) el.databasePath.textContent = status.database_path || "未读取到路径";
  if (el.defaultRange) el.defaultRange.textContent = `${status.max_results} 篇 / ${status.recent_days} 天`;
  if (el.llmStatus) el.llmStatus.textContent = status.llm_available ? `已启用 ${status.llm_model}` : "未配置 token";
  el.maxResults.value = status.max_results;
  el.recentDays.value = status.recent_days;
  document.querySelectorAll('input[name="source"]').forEach((input) => {
    input.checked = (status.sources || []).includes(input.value);
  });
}

async function loadPapers() {
  setBusy(true);
  renderSkeletonList();
  try {
    const limit = clampNumber(el.maxResults.value, 1, 500, 120);
    const data = await getJson(`/api/papers?limit=${limit}&keyword=${encodeURIComponent(state.keyword)}`);
    state.papers = sortPapersForDisplay(data.papers || []);
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

function renderSkeletonList() {
  const rows = Array.from({ length: 6 }, () => `
    <div class="skeleton-row">
      <div class="skeleton-line title"></div>
      <div class="skeleton-line meta"></div>
      <div class="skeleton-line tags"></div>
    </div>
  `).join("");
  el.paperList.innerHTML = rows;
}

async function collectPapers() {
  const sources = selectedSources();
  if (!sources.length) {
    showMessage("请至少选择一个论文来源。", true);
    return;
  }

  setBusy(true);
  const queryText = state.keyword ? `，检索词：${state.keyword}` : "";
  showMessage(`正在从 ${sources.map((source) => sourceLabel[source] || source).join("、")} 收集论文${queryText}，请稍等。`);
  try {
    const data = await postJson("/api/collect", {
      max_results: el.maxResults.value,
      recent_days: el.recentDays.value,
      sources,
      query: state.keyword || undefined,
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
    const data = await postJson("/api/export", { output: "reports/papers.md", limit: clampNumber(el.maxResults.value, 1, 500, 120) });
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
  // 保存当前视图的滚动位置
  const mainContent = document.querySelector(".main-content");
  if (mainContent && state.activeView) {
    state.scrollPositions = state.scrollPositions || {};
    state.scrollPositions[state.activeView] = mainContent.scrollTop;
  }
  state.activeView = view;
  selectNav(view);
  render();
  if (view === "expert") {
    loadExpertSessions();
  }
  if (view === "generator") {
    initGeneratorView();
  }
  // 恢复目标视图的滚动位置
  requestAnimationFrame(() => {
    if (mainContent && state.scrollPositions && state.scrollPositions[view] != null) {
      mainContent.scrollTop = state.scrollPositions[view];
    } else if (mainContent) {
      mainContent.scrollTop = 0;
    }
  });
}

function openManualAddPanel() {
  state.activeView = "manual";
  renderViewChrome();
  document.querySelectorAll("[data-nav]").forEach((button) => button.classList.remove("active"));
  renderManualAddPanel();
}

function openUploadPanel() {
  state.activeView = "upload";
  renderViewChrome();
  document.querySelectorAll("[data-nav]").forEach((button) => button.classList.remove("active"));
  renderUploadPanel();
}

function selectNav(view) {
  document.querySelectorAll("[data-nav]").forEach((button) => {
    button.classList.toggle("active", button.dataset.nav === view);
  });
}

function render() {
  renderViewChrome();
  renderStats();
  renderList();
  if (state.activeView === "triage") {
    renderTriagePanel();
  } else if (state.activeView === "discovery") {
    renderDiscoveryPanel();
  } else if (state.activeView === "daily") {
    renderDailyPanel();
  } else if (state.activeView === "expert") {
    renderExpertPanel();
  } else if (state.activeView === "report") {
    renderReportPanel();
  } else if (state.activeView === "settings") {
    renderSettingsPanel();
  } else if (state.activeView === "manual") {
    renderManualAddPanel();
  } else if (state.activeView === "upload") {
    renderUploadPanel();
  } else if (state.activeView === "generator") {
    // generator view uses its own HTML section, no panel rendering needed
  } else {
    renderDetail();
  }
}

function renderViewChrome() {
  const copy = viewCopy[state.activeView] || viewCopy.library;
  const isExpertView = state.activeView === "expert";
  const isGeneratorView = state.activeView === "generator";
  el.viewTitle.textContent = copy.title;
  el.viewSubtitle.textContent = copy.subtitle;
  el.listTitle.textContent = copy.listTitle;
  el.listSubtitle.textContent = copy.listSubtitle;
  el.contentGrid.hidden = isGeneratorView;
  if (el.generatorView) el.generatorView.hidden = !isGeneratorView;
  el.contentGrid.classList.toggle("wide-detail", ["triage", "discovery", "expert"].includes(state.activeView));
  el.contentGrid.classList.toggle("expert-view", isExpertView);
  el.contentGrid.classList.toggle("expert-collapsed", isExpertView && state.expertPapersCollapsed);
  el.workspace?.classList.toggle("expert-shell", isExpertView || isGeneratorView);
  if (el.expertPaperPanelToggle) {
    el.expertPaperPanelToggle.hidden = !isExpertView;
    el.expertPaperPanelToggle.textContent = state.expertPapersCollapsed ? "展开" : "收起";
    el.expertPaperPanelToggle.title = state.expertPapersCollapsed ? "展开咨询论文" : "收起咨询论文";
  }
  if (el.expertPaperRail) {
    el.expertPaperRail.hidden = !(isExpertView && state.expertPapersCollapsed);
  }
}

function animateCounter(element, target, duration = 2000) {
  const start = 0;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    const easeOutQuart = 1 - Math.pow(1 - progress, 4);
    const current = Math.floor(start + (target - start) * easeOutQuart);

    element.textContent = current.toLocaleString();

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

function renderStats() {
  const methodTags = new Set();
  for (const paper of state.papers) {
    for (const tag of paper.summary.method_tags || []) methodTags.add(tag);
  }
  const latestValidPaper = state.papers.find((paper) => !isFutureDate(paper.published));
  const highCount = state.papers.filter((paper) => readingScore(paper) >= 72).length;

  animateCounter(el.paperCount, state.papers.length);
  animateCounter(el.highCount, highCount);
  animateCounter(el.methodCount, methodTags.size);

  el.latestDate.textContent = latestValidPaper?.published?.slice(0, 10) || "--";
}

function initStaggerAnimation() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.paper-row').forEach(card => {
    observer.observe(card);
  });
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
      const staysInExpert = state.activeView === "expert";
      state.activeView = staysInExpert ? "expert" : "library";
      state.detailHistory = [];
      selectNav(state.activeView);
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
  initStaggerAnimation();
}

function renderPaperRow(paper) {
  const priority = paper.summary.reading_priority || "medium";
  const score = readingScore(paper);
  const decision = readingDecision(paper);
  const dateIsFuture = isFutureDate(paper.published);
  const tags = [
    decision.label,
    priorityLabel[priority] || priority,
    ...(dateIsFuture ? ["日期异常"] : []),
    ...(paper.summary.method_tags || []).slice(0, 2),
  ];
  const isSelected = state.selectedIds.has(paper.arxiv_id);
  const isActive = paper.arxiv_id === state.selectedId && ["library", "expert"].includes(state.activeView);
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
          <span>速筛 ${score}</span>
          <span>${escapeHtml((paper.authors || []).slice(0, 3).join(", "))}</span>
        </div>
        <div class="tag-row">${tags.map((tag, index) => `<span class="tag ${index <= 1 ? `priority-${priority}` : ""}">${escapeHtml(tag)}</span>`).join("")}</div>
      </div>
      <time class="paper-date ${dateIsFuture ? "date-warning" : ""}">${escapeHtml((paper.published || "").slice(0, 10))}</time>
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

function renderUploadPanel() {
  el.paperDetail.className = "paper-detail";
  el.paperDetail.innerHTML = `
    <h2 class="detail-title">上传 PDF 论文并推荐</h2>
    <p class="panel-note">选择一篇 PDF，系统会保存到本地 PDF 目录、尝试提取全文文本、生成本地中文解读，并基于它从现有论文库推荐相似论文。</p>
    <form id="uploadPaperForm" class="manual-form">
      <label>
        PDF 文件
        <input name="file" type="file" accept="application/pdf,.pdf" required />
      </label>
      <label>
        标题
        <input name="title" placeholder="可选；留空会尝试从 PDF 或文件名识别" />
      </label>
      <label>
        作者
        <input name="authors" placeholder="可选，多个作者用逗号分隔" />
      </label>
      <div class="manual-form-grid">
        <label>
          年份
          <input name="year" inputmode="numeric" placeholder="2024" />
        </label>
        <label>
          标签
          <input name="tags" value="上传论文" placeholder="例如：剩余时间预测,流程挖掘" />
        </label>
      </div>
      <label>
        摘要
        <textarea name="abstract" rows="6" placeholder="可选；留空会尝试从 PDF 提取摘要或正文片段"></textarea>
      </label>
      <div class="report-actions">
        <button type="submit">上传并推荐</button>
        <button type="button" data-upload-cancel>取消</button>
      </div>
    </form>
  `;
  el.paperDetail.querySelector("#uploadPaperForm").addEventListener("submit", submitUploadedPaper);
  el.paperDetail.querySelector("[data-upload-cancel]").addEventListener("click", () => {
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

async function submitUploadedPaper(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  setBusy(true);
  showMessage("正在上传并分析 PDF，较大的文件可能需要几秒。");
  try {
    const response = await fetch("/api/papers/upload", {
      method: "POST",
      body: formData,
    });
    const data = await parseResponse(response);
    state.selectedId = data.paper.arxiv_id;
    state.keyword = "";
    el.searchInput.value = "";
    state.activeView = "library";
    selectNav("library");
    await loadPapers();
    const paper = state.papers.find((item) => item.arxiv_id === data.paper.arxiv_id);
    if (paper) paper.related = data.related || paper.related || [];
    render();
    const textHint = data.pdf_text_available ? "已提取 PDF 文本。" : "未提取到 PDF 文本，可安装 pymupdf 后获得更好解读。";
    showMessage(`上传完成：${data.paper.title}。已生成 ${data.related?.length || 0} 条相似推荐。${textHint}`);
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
  if (ids.length < 1) {
    showMessage("请至少选择 1 篇论文来生成综述。", true);
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

function renderTriagePanel() {
  const ranked = [...state.papers].sort((a, b) => readingScore(b) - readingScore(a));
  el.paperDetail.className = "paper-detail triage-detail";
  if (!ranked.length) {
    el.paperDetail.innerHTML = `
      <h2 class="detail-title">速筛看板</h2>
      <p class="panel-note">当前没有可筛选的论文。先在“发现扩展”里选择一个检索方向，然后点击“多源收集”。</p>
    `;
    return;
  }

  const high = ranked.filter((paper) => readingScore(paper) >= 72).length;
  const medium = ranked.filter((paper) => readingScore(paper) >= 48 && readingScore(paper) < 72).length;
  const low = ranked.length - high - medium;
  el.paperDetail.innerHTML = `
    <h2 class="detail-title">速筛看板</h2>
    <p class="panel-note">这个分数不是论文质量结论，而是帮你决定阅读顺序：相关性、方法标签、引用、是否已有深度解读都会影响排序。</p>
    <div class="triage-summary">
      <div><strong>${high}</strong><span>建议精读</span></div>
      <div><strong>${medium}</strong><span>可以扫读</span></div>
      <div><strong>${low}</strong><span>暂时跳过</span></div>
    </div>
    <div class="triage-list">
      ${ranked.slice(0, 12).map((paper) => renderTriageCard(paper)).join("")}
    </div>
  `;

  el.paperDetail.querySelectorAll("[data-triage-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const paperId = button.dataset.paperId;
      const action = button.dataset.triageAction;
      if (action === "open") {
        state.selectedId = paperId;
        state.activeView = "library";
        selectNav("library");
        render();
      } else if (action === "select") {
        state.selectedIds.add(paperId);
        render();
      } else {
        runPaperAction(action, paperId);
      }
    });
  });
}

function renderTriageCard(paper) {
  const score = readingScore(paper);
  const decision = readingDecision(paper);
  const evidence = readingEvidence(paper);
  return `
    <article class="triage-card">
      <div class="score-ring ${decision.tone}">
        <strong>${score}</strong>
        <span>${escapeHtml(decision.label)}</span>
      </div>
      <div class="triage-card-body">
        <h3>${escapeHtml(paper.title)}</h3>
        <p>${escapeHtml(paper.summary.short_summary || paper.abstract || "暂无摘要。")}</p>
        <div class="tag-row">${evidence.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>
        <div class="triage-actions">
          <button data-triage-action="open" data-paper-id="${escapeAttribute(paper.arxiv_id)}" type="button">查看详情</button>
          <button data-triage-action="select" data-paper-id="${escapeAttribute(paper.arxiv_id)}" type="button">加入批量</button>
          <button data-triage-action="local-summary" data-paper-id="${escapeAttribute(paper.arxiv_id)}" type="button">刷新解读</button>
          <button data-triage-action="recommend" data-paper-id="${escapeAttribute(paper.arxiv_id)}" type="button">找相似</button>
        </div>
      </div>
    </article>
  `;
}

function renderDiscoveryPanel() {
  const counts = countBySource();
  const activeQuery = state.keyword || "使用默认配置主题";
  el.paperDetail.className = "paper-detail discovery-detail";
  el.paperDetail.innerHTML = `
    <h2 class="detail-title">发现扩展</h2>
    <p class="panel-note">当前检索词：${escapeHtml(activeQuery)}。点击下面的方向会写入搜索框，再点“多源收集”即可按该方向扩展论文池。</p>
    <section class="discovery-section">
      <h3>推荐检索方向</h3>
      <div class="query-grid">
        ${discoveryQueries.map((item) => `
          <button class="query-card" data-discovery-query="${escapeAttribute(item.query)}" type="button">
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(item.query)}</span>
            <small>${escapeHtml(item.note)}</small>
          </button>
        `).join("")}
      </div>
    </section>
    <section class="discovery-section">
      <h3>来源覆盖</h3>
      <div class="source-grid">
        ${Object.entries(sourceLabel)
          .filter(([source]) => source !== "manual")
          .map(([source, label]) => `<div><strong>${counts[source] || 0}</strong><span>${escapeHtml(label)}</span></div>`)
          .join("")}
      </div>
    </section>
    <section class="discovery-section">
      <h3>效率建议</h3>
      <ul>
        <li>先用较宽关键词收集，再到“速筛看板”看分数和理由。</li>
        <li>对高分论文执行“LLM 深度解读”，再用“找相似”扩展同主题论文。</li>
        <li>如果某个来源经常为空，增大“天数”或换成更具体的英文关键词。</li>
      </ul>
    </section>
  `;

  el.paperDetail.querySelectorAll("[data-discovery-query]").forEach((button) => {
    button.addEventListener("click", () => {
      state.keyword = button.dataset.discoveryQuery;
      el.searchInput.value = state.keyword;
      loadPapers();
      showMessage("已切换检索词。确认数量、天数和来源后，点击“多源收集”扩展论文。");
    });
  });
}

function renderDailyPanel() {
  el.paperDetail.className = "paper-detail daily-detail";
  if (!state.dailyRecommendations && !state.dailyLoading && !state.dailyError) {
    loadDailyRecommendations(false);
  }
  if (state.dailyLoading) {
    el.paperDetail.innerHTML = `
      <h2 class="detail-title">每日推荐</h2>
      <p class="panel-note">正在更新今日 AI/深度学习论文推荐，请稍等。</p>
    `;
    return;
  }
  const data = state.dailyRecommendations;
  if (!data) {
    el.paperDetail.innerHTML = `
      <h2 class="detail-title">每日推荐</h2>
      <p class="panel-note warning">${escapeHtml(state.dailyError || "还没有加载推荐。点击下方按钮重新获取。")}</p>
      <div class="report-actions">
        <button data-daily-refresh type="button">刷新今日推荐</button>
      </div>
    `;
    bindDailyPanelEvents();
    return;
  }
  const items = data.items || [];
  el.paperDetail.innerHTML = `
    <div class="daily-heading">
      <div>
        <h2 class="detail-title">每日推荐</h2>
        <p class="panel-note">日期：${escapeHtml(data.date || "--")}；方向：${escapeHtml(data.topic || "人工智能、深度学习")}${data.from_cache ? "；已使用今日缓存" : "；刚刚更新"}</p>
      </div>
      <button data-daily-refresh type="button">刷新今日推荐</button>
    </div>
    <section class="daily-summary">
      <div><strong>${items.length}</strong><span>今日候选</span></div>
      <div><strong>${items.filter((item) => (item.quality_signals || []).some((signal) => /NeurIPS|ICML|ICLR|CVPR|ACL|EMNLP|AAAI|IJCAI|KDD|TPAMI|JMLR|Nature|Science/i.test(signal))).length}</strong><span>顶会顶刊信号</span></div>
      <div><strong>${items.filter((item) => (item.paper?.citation_count || 0) > 0).length}</strong><span>有引用数据</span></div>
    </section>
    <div class="daily-list">
      ${items.length ? items.map(renderDailyRecommendationCard).join("") : `<p class="panel-note warning">今天暂时没有拿到推荐结果，可以点“刷新今日推荐”重试，或检查论文来源是否可访问。</p>`}
    </div>
  `;
  bindDailyPanelEvents();
}

async function loadDailyRecommendations(force) {
  state.dailyLoading = true;
  state.dailyError = "";
  renderDailyPanel();
  try {
    const data = await getJson(`/api/daily-recommendations?limit=10${force ? "&force=1" : ""}`);
    state.dailyRecommendations = data;
    for (const item of data.items || []) {
      if (item.paper) mergePaperIntoState(item.paper);
    }
    showMessage(force ? "今日推荐已刷新。" : "今日推荐已加载。");
  } catch (error) {
    state.dailyError = `每日推荐加载失败：${error.message}`;
    showMessage(state.dailyError, true);
  } finally {
    state.dailyLoading = false;
    if (state.activeView === "daily") renderDailyPanel();
  }
}

function renderDailyRecommendationCard(item) {
  const paper = item.paper || {};
  const summary = paper.summary || {};
  const signals = item.quality_signals || [];
  return `
    <article class="daily-card">
      <div class="daily-rank">D${item.rank || ""}</div>
      <div class="daily-card-body">
        <div class="daily-title-row">
          <h3>${escapeHtml(paper.title || "未命名论文")}</h3>
          <span>${escapeHtml(String(item.score ?? "--"))}</span>
        </div>
        <div class="paper-meta">
          <span>${escapeHtml(sourceLabel[paper.source] || paper.source || "未知来源")}</span>
          <span>${escapeHtml(paper.venue || paper.year || (paper.published || "").slice(0, 10) || "未知年份")}</span>
          <span>引用 ${paper.citation_count || 0}</span>
        </div>
        <p>${escapeHtml(item.reason || summary.relevance || "基于主题和质量信号推荐。")}</p>
        <div class="daily-signal-row">
          <strong>质量信号</strong>
          ${(signals.length ? signals : ["AI/深度学习主题"]).map((signal) => `<span class="tag">${escapeHtml(signal)}</span>`).join("")}
        </div>
        <p>${escapeHtml(summary.short_summary || paper.abstract || "暂无摘要。")}</p>
        <div class="recommendation-actions">
          <button class="recommendation-link" data-daily-action="add" data-paper-id="${escapeAttribute(paper.arxiv_id)}" type="button">加入论文库</button>
          <button class="recommendation-link primary" data-daily-action="open" data-paper-id="${escapeAttribute(paper.arxiv_id)}" type="button">查看站内总结</button>
          ${paper.entry_url ? `<a class="recommendation-link" href="${escapeAttribute(paper.entry_url)}" target="_blank" rel="noopener">打开出处</a>` : ""}
        </div>
      </div>
    </article>
  `;
}

function bindDailyPanelEvents() {
  el.paperDetail.querySelectorAll("[data-daily-refresh]").forEach((button) => {
    button.addEventListener("click", () => loadDailyRecommendations(true));
  });
  el.paperDetail.querySelectorAll("[data-daily-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const paper = state.papers.find((item) => item.arxiv_id === button.dataset.paperId);
      if (!paper) {
        showMessage("这篇论文还没有加入本地状态，请先刷新今日推荐。", true);
        return;
      }
      if (button.dataset.dailyAction === "add") {
        state.selectedId = paper.arxiv_id;
        renderList();
        showMessage(`已加入论文库：${paper.title}`);
        return;
      }
      state.selectedId = paper.arxiv_id;
      state.activeView = "library";
      selectNav("library");
      render();
    });
  });
}

function mergePaperIntoState(paper) {
  const index = state.papers.findIndex((item) => item.arxiv_id === paper.arxiv_id);
  if (index >= 0) {
    state.papers[index] = paper;
  } else {
    state.papers.unshift(paper);
  }
  state.papers = sortPapersForDisplay(state.papers);
}

function readingScore(paper) {
  let score = 20;
  const summary = paper.summary || {};
  if (summary.reading_priority === "high") score += 28;
  if (summary.reading_priority === "medium") score += 16;
  score += Math.min(18, Math.log10((paper.citation_count || 0) + 1) * 8);
  score += Math.min(12, (summary.method_tags || []).length * 3);
  score += Math.min(10, (summary.topic_tags || paper.tags || []).length * 2);
  if (summary.deep_summary || summary.method || summary.contribution) score += 12;
  if ((summary.innovation_points || []).length) score += 8;
  if (paper.local_pdf_path) score += 4;
  return Math.max(0, Math.min(100, Math.round(score)));
}

function readingDecision(paper) {
  const score = readingScore(paper);
  if (score >= 72) return { label: "建议精读", tone: "strong" };
  if (score >= 48) return { label: "可以扫读", tone: "medium" };
  return { label: "暂时跳过", tone: "low" };
}

function readingEvidence(paper) {
  const summary = paper.summary || {};
  const evidence = [];
  if (summary.reading_priority === "high") evidence.push("主题高度相关");
  if ((summary.method_tags || []).length) evidence.push(`方法：${summary.method_tags.slice(0, 2).join(" / ")}`);
  if (paper.citation_count) evidence.push(`引用 ${paper.citation_count}`);
  if (summary.deep_summary) evidence.push("已有深度解读");
  if ((summary.innovation_points || []).length) evidence.push("有创新点拆解");
  if (!evidence.length) evidence.push("信息不足，建议先扫摘要");
  return evidence.slice(0, 4);
}

function countBySource() {
  return state.papers.reduce((result, paper) => {
    result[paper.source] = (result[paper.source] || 0) + 1;
    return result;
  }, {});
}

function sortPapersForDisplay(papers) {
  return [...papers].sort((a, b) => {
    const aRank = dateRank(a.published);
    const bRank = dateRank(b.published);
    if (aRank !== bRank) return aRank - bRank;
    return paperTime(b.published) - paperTime(a.published);
  });
}

function dateRank(value) {
  if (!value) return 2;
  return isFutureDate(value) ? 1 : 0;
}

function isFutureDate(value) {
  const time = paperTime(value);
  if (!Number.isFinite(time)) return false;
  const today = new Date();
  today.setHours(23, 59, 59, 999);
  return time > today.getTime();
}

function paperTime(value) {
  const time = Date.parse(value || "");
  return Number.isFinite(time) ? time : 0;
}

function shortDateTime(value) {
  const time = Date.parse(value || "");
  if (!Number.isFinite(time)) return "刚刚";
  const date = new Date(time);
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  const hour = `${date.getHours()}`.padStart(2, "0");
  const minute = `${date.getMinutes()}`.padStart(2, "0");
  return `${month}-${day} ${hour}:${minute}`;
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
    ${renderDetailHistoryBar()}
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
      <button data-action="innovation-advice" data-id="${escapeAttribute(paper.arxiv_id)}" type="button">创新建议</button>
      <button data-expert-open-selected type="button">论文专家</button>
      <button data-action="delete-paper" data-id="${escapeAttribute(paper.arxiv_id)}" type="button" class="danger-btn">删除</button>
    </div>
    ${state.status?.llm_available ? "" : `<p class="panel-note warning">LLM 未配置，深度解读按钮会保持不可用。请在配置面板检查 .env。</p>`}
    ${renderRecommendationSpotlight(paper)}
    ${renderRelatedSummaryPreview(paper.relatedPreview)}
    ${renderInnovationAdvice(paper.innovationAdvice)}
    ${renderExpertChat(paper)}
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
    ${renderRelations("近期引用", paper.citations)}
    ${renderRelations("参考文献", paper.references)}
  `;

  el.paperDetail.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => runPaperAction(button.dataset.action, button.dataset.id));
  });
  el.paperDetail.querySelectorAll("[data-open-related]").forEach((button) => {
    button.addEventListener("click", () => openRelatedPaper(button.dataset.openRelated));
  });
  el.paperDetail.querySelectorAll("[data-promote-related]").forEach((button) => {
    button.addEventListener("click", () => promoteRelatedPaper(button.dataset.promoteRelated));
  });
  el.paperDetail.querySelectorAll("[data-close-related-preview]").forEach((button) => {
    button.addEventListener("click", closeRelatedPreview);
  });
  el.paperDetail.querySelectorAll("[data-return-recommendations]").forEach((button) => {
    button.addEventListener("click", returnToRecommendationList);
  });
  el.paperDetail.querySelectorAll("[data-history-back]").forEach((button) => {
    button.addEventListener("click", restoreDetailHistory);
  });
  el.paperDetail.querySelectorAll("[data-expert-open-selected]").forEach((button) => {
    button.addEventListener("click", openExpertForSelectedPaper);
  });
  bindExpertChatEvents(paper);
}

function renderDetailHistoryBar() {
  const last = state.detailHistory[state.detailHistory.length - 1];
  if (!last) return "";
  return `
    <div class="detail-history-bar">
      <button data-history-back type="button">← 返回上一步</button>
      <span>${escapeHtml(last.label || "回到刚刚的论文推荐")}</span>
    </div>
  `;
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
      showMessage(`相似论文推荐已生成，已在详情页顶部显示 ${data.related?.length || 0} 条推荐。`);
      return;
    }
    if (action === "innovation-advice") {
      showMessage("正在根据上传论文和相似论文生成创新建议。");
      const data = await postJson(`/api/papers/${encodeURIComponent(paperId)}/innovation-advice`, { limit: 8 });
      const paper = state.papers.find((item) => item.arxiv_id === paperId);
      if (paper) {
        paper.related = data.related || paper.related || [];
        paper.innovationAdvice = data.advice || [];
      }
      render();
      showMessage(`已生成 ${data.advice?.length || 0} 条创新建议。`);
      return;
    }
    if (action === "delete-paper") {
      if (!confirm("确定要删除这篇论文吗？此操作不可撤销。")) return;
      const response = await fetch(`/api/papers/${encodeURIComponent(paperId)}`, { method: "DELETE" });
      const data = await parseResponse(response);
      state.papers = state.papers.filter((item) => item.arxiv_id !== paperId);
      state.selectedId = null;
      render();
      showMessage(`已删除论文：${data.deleted}`);
    }
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

function renderExpertPanel() {
  if (!state.expertSessionsLoaded && !state.expertSessionsLoading) {
    loadExpertSessions();
  }
  const paper = state.papers.find((item) => item.arxiv_id === state.selectedId);
  el.paperDetail.className = "paper-detail expert-detail expert-chat-mode";
  if (!paper) {
    el.paperDetail.innerHTML = `
      <section id="expertChatPanel" class="expert-chat-stage expert-chat-only">
        <div class="expert-chat-layout no-paper">
          <aside class="expert-history-panel">
            <div class="expert-history-heading">
              <strong>历史对话</strong>
            </div>
            <p class="panel-note">选择一篇咨询论文后即可开始新对话。</p>
          </aside>
          <main class="expert-chat-main">
            <div class="expert-center-prompt">
              <h2>我们先从哪里开始呢？</h2>
              <p>先从咨询论文列表选择一篇论文，再向论文专家提问。</p>
            </div>
          </main>
        </div>
      </section>
    `;
    bindExpertChatEvents(null);
    return;
  }

  const session = currentExpertSessionForPaper(paper);
  const chats = session?.messages || [];
  const quickQuestions = [
    {
      label: "解释方法",
      question: "请详细解释这篇论文的方法思想：输入是什么，中间模块怎么处理，输出是什么，为什么这样设计。",
    },
    {
      label: "创新对比",
      question: "请说明这篇论文相对已有方法的核心创新点，并逐条对比它解决了之前方法的什么不足。",
    },
    {
      label: "实验结果",
      question: "请梳理这篇论文的实验设置、数据集、baseline、主要指标和结果提升，告诉我哪些结果最关键。",
    },
    {
      label: "阅读路线",
      question: "请按精读顺序告诉我这篇论文应该先看哪些章节、表格和图，并说明每一部分要看什么。",
    },
  ];
  el.paperDetail.innerHTML = `
    <section id="expertChatPanel" class="expert-chat-stage expert-chat-only">
      <div class="expert-chat-layout">
        ${renderExpertHistoryPanel()}
        <main class="expert-chat-main">
          ${renderAgentRunningStatus()}
          <div class="expert-thread ${chats.length ? "" : "empty"}">
            ${chats.length ? chats.map(renderExpertTurn).join("") : `
              <div class="expert-empty-chat">
                <strong>还没有对话</strong>
                <p>你可以直接问概念、方法流程、创新点、实验结论，专家会围绕当前论文回答。</p>
              </div>
            `}
          </div>

          <section class="expert-center-prompt">
            <h2>我们先从哪里开始呢？</h2>
            <form class="expert-askbar" data-expert-form>
              <button class="askbar-icon" data-expert-suggestion="请先用一句话告诉我这篇论文解决了什么问题，然后再展开方法细节。" type="button" title="填入推荐问题">+</button>
              <textarea data-expert-question rows="1" placeholder="有问题，尽管问"></textarea>
              <label class="askbar-icon image-button" data-expert-image title="添加图片">
                图
                <input data-expert-image-input type="file" accept="image/*" multiple hidden />
              </label>
              <button class="askbar-send" data-expert-submit type="submit" title="发送问题">提问</button>
            </form>
            ${renderExpertImageAttachments()}
            <div class="expert-quick-actions">
              ${quickQuestions.map((item) => `
                <button data-expert-suggestion="${escapeAttribute(item.question)}" type="button">${escapeHtml(item.label)}</button>
              `).join("")}
              <button data-expert-github type="button">查找资料</button>
            </div>
          </section>
        </main>
      </div>
    </section>
  `;
  bindExpertChatEvents(paper);
}

function openExpertForSelectedPaper() {
  state.activeView = "expert";
  selectNav("expert");
  render();
  loadExpertSessions();
  if (el.paperDetail) el.paperDetail.scrollTop = 0;
}

function toggleExpertPaperPanel() {
  state.expertPapersCollapsed = !state.expertPapersCollapsed;
  render();
}

function renderExpertHistoryPanel() {
  const sessions = state.expertSessions
    .filter((session) => session && session.paperId)
    .slice(0, MAX_EXPERT_SESSIONS);
  return `
    <aside class="expert-history-panel">
      <div class="expert-history-heading">
        <strong>历史对话</strong>
        <button data-expert-new-chat type="button">新对话</button>
      </div>
      <div class="expert-session-list">
        ${state.expertSessionsLoading ? `<p class="panel-note">正在加载历史对话...</p>` : ""}
        ${sessions.length ? sessions.map(renderExpertSessionItem).join("") : `<p class="panel-note">还没有历史对话。</p>`}
      </div>
    </aside>
  `;
}

function renderExpertSessionItem(session) {
  const active = session.id === state.activeExpertSessionId;
  const count = (session.messages || []).length;
  return `
    <button class="expert-session-item ${active ? "active" : ""}" data-expert-session="${escapeAttribute(session.id)}" type="button">
      <span>${escapeHtml(session.title || "新的论文对话")}</span>
      <small>${escapeHtml(shortDateTime(session.updatedAt || session.createdAt))} · ${count} 问</small>
    </button>
  `;
}

function currentExpertSessionForPaper(paper) {
  let session = state.expertSessions.find((item) => item.id === state.activeExpertSessionId && item.paperId === paper.arxiv_id);
  if (!session) {
    session = state.expertSessions.find((item) => item.paperId === paper.arxiv_id);
  }
  if (session) {
    session.paperTitle = paper.title;
    session.messages = session.messages || [];
    state.activeExpertSessionId = session.id;
    paper.expertChat = session.messages;
  }
  return session || null;
}

async function ensureExpertSession(paper) {
  const existing = currentExpertSessionForPaper(paper);
  if (existing) return existing;
  return createExpertSession(paper);
}

async function createExpertSession(paper) {
  const data = await postJson("/api/agent/sessions", {
    paper_id: paper.arxiv_id,
    title: expertSessionTitle(paper, []),
  });
  const session = normalizeExpertSession(data.session || {});
  upsertExpertSession(session);
  state.activeExpertSessionId = session.id;
  paper.expertChat = session.messages;
  return session;
}

async function startNewExpertSession(paper) {
  try {
    const session = await createExpertSession(paper);
    state.activeExpertSessionId = session.id;
    paper.expertChat = [];
    render();
  } catch (error) {
    showMessage(error.message, true);
  }
}

function openExpertSession(sessionId) {
  const session = state.expertSessions.find((item) => item.id === sessionId);
  if (!session) return;
  const paper = state.papers.find((item) => item.arxiv_id === session.paperId);
  if (!paper) {
    showMessage("这条历史对话对应的论文当前不在列表中，请先重新收集或搜索到它。", true);
    return;
  }
  state.selectedId = paper.arxiv_id;
  state.activeExpertSessionId = session.id;
  syncPaperExpertChat(paper, session);
  state.activeView = "expert";
  selectNav("expert");
  render();
}

function updateExpertSessionAfterAnswer(paper, turn) {
  const normalizedTurn = normalizeExpertTurn(turn);
  let session = state.expertSessions.find((item) => item.id === normalizedTurn.session_id);
  if (!session) {
    session = {
      id: normalizedTurn.session_id,
      paperId: paper.arxiv_id,
      paperTitle: paper.title,
      title: expertSessionTitle(paper, [normalizedTurn]),
      createdAt: normalizedTurn.created_at,
      updatedAt: normalizedTurn.created_at,
      messages: [],
    };
  }
  session.messages = [...(session.messages || []), normalizedTurn];
  session.updatedAt = new Date().toISOString();
  session.paperTitle = paper.title;
  session.title = expertSessionTitle(paper, session.messages);
  syncPaperExpertChat(paper, session);
  upsertExpertSession(session);
  state.activeExpertSessionId = session.id;
}

function expertSessionTitle(paper, messages = []) {
  const firstQuestion = messages.find((message) => message.question)?.question || "";
  const seed = firstQuestion || paper.title || "新的论文对话";
  return seed.length > 28 ? `${seed.slice(0, 28)}...` : seed;
}

function upsertExpertSession(session) {
  if (!session?.id) return;
  state.expertSessions = [
    session,
    ...state.expertSessions.filter((item) => item.id !== session.id),
  ].slice(0, MAX_EXPERT_SESSIONS);
}

async function loadExpertSessions() {
  if (state.expertSessionsLoading) return;
  state.expertSessionsLoading = true;
  try {
    const data = await getJson(`/api/agent/sessions?limit=${MAX_EXPERT_SESSIONS}`);
    state.expertSessions = (data.sessions || []).map(normalizeExpertSession);
    state.expertSessionsLoaded = true;
    const paper = state.papers.find((item) => item.arxiv_id === state.selectedId);
    if (paper) {
      syncPaperExpertChat(paper, currentExpertSessionForPaper(paper));
    }
  } catch (error) {
    state.expertSessionsLoaded = true;
    showMessage(`历史对话加载失败：${error.message}`, true);
  } finally {
    state.expertSessionsLoading = false;
    if (state.activeView === "expert") {
      render();
    }
  }
}

function normalizeExpertSession(session) {
  const messages = (session.turns || session.messages || []).map(normalizeExpertTurn);
  return {
    id: session.id || "",
    paperId: session.paper_id || session.paperId || "",
    paperTitle: session.paper_title || session.paperTitle || "",
    title: session.title || "新的论文对话",
    createdAt: session.created_at || session.createdAt || "",
    updatedAt: session.updated_at || session.updatedAt || "",
    messages,
  };
}

function normalizeExpertTurn(turn) {
  return {
    id: turn.id || turn.turn_id || "",
    session_id: turn.session_id || "",
    paper_id: turn.paper_id || "",
    question: turn.question || "",
    answer: turn.answer || "",
    used_llm: Boolean(turn.used_llm),
    llm_error: turn.llm_error || "",
    github_error: turn.github_error || "",
    github_repositories: turn.github_repositories || [],
    plan: turn.plan || [],
    tool_calls: turn.tool_calls || [],
    reflection: turn.reflection || null,
    memory_used: turn.memory_used || [],
    image_attachments: turn.image_attachments || turn.imageAttachments || [],
    created_at: turn.created_at || new Date().toISOString(),
  };
}

function syncPaperExpertChat(paper, session) {
  if (!paper) return;
  paper.expertChat = session?.messages || [];
}

function renderAgentRunningStatus() {
  if (!state.agentStatus) return "";
  return `
    <div class="agent-status running">
      <strong>Agent 正在执行</strong>
      <span>${escapeHtml(state.agentStatus)}</span>
    </div>
  `;
}

function renderExpertImageAttachments() {
  const images = state.expertImageAttachments || [];
  if (!images.length) return "";
  return `
    <div class="expert-attachment-preview">
      <div class="expert-attachment-strip">
        ${images.map((image, index) => `
          <figure>
            <img src="${escapeAttribute(image.data_url)}" alt="${escapeAttribute(image.name || `图片 ${index + 1}`)}" />
            <figcaption>${escapeHtml(image.name || `图片 ${index + 1}`)}</figcaption>
          </figure>
        `).join("")}
      </div>
      <button data-expert-clear-images type="button">清除图片</button>
    </div>
  `;
}

function renderExpertChat(paper) {
  const chats = paper.expertChat || [];
  return `
    <section id="expertChatPanel" class="expert-chat">
      <div class="spotlight-heading">
        <div>
          <h3>论文专家 Agent</h3>
          <p>围绕当前论文提问，它会结合站内摘要、全文片段、实验字段和 GitHub 候选代码给出解释。</p>
        </div>
        <span>${chats.length ? `${chats.length} 问` : "可提问"}</span>
      </div>
      <form class="expert-form" data-expert-form>
        <textarea data-expert-question rows="3" placeholder="例如：这篇论文的方法到底怎么做？创新点是什么？实验比哪些 baseline 强？有没有 GitHub 代码可以参考？"></textarea>
        <div class="expert-actions">
          <button class="recommendation-link primary" data-expert-submit type="submit">提问</button>
          <button class="recommendation-link" data-expert-github type="button">找代码/复现</button>
        </div>
      </form>
      <div class="expert-thread">
        ${chats.length ? chats.map(renderExpertTurn).join("") : `<p class="panel-note">你可以直接问不懂的概念、方法流程、创新点、实验结果，或者让它帮你找 GitHub 复现仓库。</p>`}
      </div>
    </section>
  `;
}

function bindExpertChatEvents(paper) {
  el.paperDetail.querySelectorAll("[data-expert-toggle-papers]").forEach((button) => {
    button.addEventListener("click", toggleExpertPaperPanel);
  });
  if (!paper) return;
  el.paperDetail.querySelectorAll("[data-expert-new-chat]").forEach((button) => {
    button.addEventListener("click", () => startNewExpertSession(paper));
  });
  el.paperDetail.querySelectorAll("[data-expert-session]").forEach((button) => {
    button.addEventListener("click", () => openExpertSession(button.dataset.expertSession));
  });
  el.paperDetail.querySelectorAll("[data-expert-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitExpertQuestion(paper.arxiv_id, false);
    });
  });
  el.paperDetail.querySelectorAll("[data-expert-suggestion]").forEach((button) => {
    button.addEventListener("click", () => {
      const textarea = el.paperDetail.querySelector("[data-expert-question]");
      if (!textarea) return;
      textarea.value = button.dataset.expertSuggestion || "";
      textarea.focus();
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    });
  });
  el.paperDetail.querySelectorAll("[data-expert-github]").forEach((button) => {
    button.addEventListener("click", () => submitExpertQuestion(paper.arxiv_id, true));
  });
  el.paperDetail.querySelectorAll("[data-expert-image-input]").forEach((input) => {
    input.addEventListener("change", () => handleExpertImageInput(input.files));
  });
  el.paperDetail.querySelectorAll("[data-expert-clear-images]").forEach((button) => {
    button.addEventListener("click", () => {
      state.expertImageAttachments = [];
      render();
    });
  });
  el.paperDetail.querySelectorAll("[data-agent-feedback]").forEach((button) => {
    button.addEventListener("click", () => submitAgentFeedback(button));
  });
}

function renderExpertTurn(turn) {
  const repositories = turn.github_repositories || [];
  return `
    <article class="expert-turn">
      <div class="expert-question">
        <strong>你问：</strong>
        <p>${escapeHtml(turn.question)}</p>
      </div>
      ${renderExpertTurnImages(turn.image_attachments || [])}
      ${renderAgentStatusSummary(turn)}
      <div class="expert-answer">
        <strong>专家回答${turn.used_llm ? "（LLM）" : "（本地兜底）"}：</strong>
        <p>${escapeHtml(turn.answer).replaceAll("\n", "<br>")}</p>
      </div>
      ${turn.llm_error ? `<p class="panel-note warning">LLM 失败，已切换本地回答：${escapeHtml(turn.llm_error)}</p>` : ""}
      ${turn.github_error ? `<p class="panel-note warning">${escapeHtml(turn.github_error)}</p>` : ""}
      ${repositories.length ? `
        <div class="expert-repos">
          <strong>GitHub 候选仓库</strong>
          ${repositories.map((repo) => `
            <a href="${escapeAttribute(repo.html_url)}" target="_blank" rel="noopener">
              <span>${escapeHtml(repo.full_name)}</span>
              <small>${escapeHtml(repo.language || "未知语言")} · ${escapeHtml(repo.stars || 0)} stars · ${escapeHtml(repo.reason || "关键词匹配")}</small>
            </a>
          `).join("")}
        </div>
      ` : ""}
      ${renderAgentFeedback(turn)}
    </article>
  `;
}

function renderExpertTurnImages(images = []) {
  if (!images.length) return "";
  return `
    <div class="expert-turn-images">
      ${images.map((image, index) => `
        <a href="${escapeAttribute(image.data_url)}" target="_blank" rel="noopener" title="${escapeAttribute(image.name || `图片 ${index + 1}`)}">
          <img src="${escapeAttribute(image.data_url)}" alt="${escapeAttribute(image.name || `图片 ${index + 1}`)}" />
        </a>
      `).join("")}
    </div>
  `;
}

function renderAgentStatusSummary(turn) {
  const plan = turn.plan || [];
  const tool_calls = turn.tool_calls || [];
  const reflection = turn.reflection || {};
  if (!plan.length && !tool_calls.length && reflection.score === undefined) return "";
  const steps = plan.map((step) => `${agentStepLabel(step.type)}：${agentStatusLabel(step.status)}`).join(" · ");
  const tools = tool_calls.map((call) => `${agentStepLabel(call.tool)} ${agentStatusLabel(call.status)}`).join(" · ");
  const score = reflection.score !== undefined ? `反思评分 ${Math.round(Number(reflection.score) * 100)}%` : "";
  const missing = (reflection.missing || []).length ? `缺口：${reflection.missing.join("、")}` : "反思通过";
  return `
    <div class="agent-status">
      <strong>Agent 执行摘要</strong>
      ${steps ? `<span>${escapeHtml(steps)}</span>` : ""}
      ${tools ? `<span>${escapeHtml(tools)}</span>` : ""}
      ${score ? `<span>${escapeHtml(score)} · ${escapeHtml(missing)}</span>` : ""}
    </div>
  `;
}

function renderAgentFeedback(turn) {
  if (!turn.id || !turn.session_id) return "";
  const options = [
    ["helpful", "有帮助"],
    ["too_general", "太泛"],
    ["missing_experiments", "缺实验"],
    ["missing_innovation", "缺创新"],
    ["wrong", "回答错了"],
  ];
  return `
    <div class="expert-feedback">
      ${options.map(([category, label]) => `
        <button data-agent-feedback="${category}" data-turn-id="${escapeAttribute(turn.id)}" data-session-id="${escapeAttribute(turn.session_id)}" type="button">${escapeHtml(label)}</button>
      `).join("")}
    </div>
  `;
}

function agentStepLabel(type) {
  const labels = {
    read_context: "读取论文",
    read_fulltext: "读取全文",
    search_github: "检索代码",
    analyze_citations: "引用分析",
    find_related: "相似论文",
    compare_methods: "方法对比",
    reflect: "反思回答",
    synthesize: "生成回答",
  };
  return labels[type] || type || "步骤";
}

function agentStatusLabel(status) {
  const labels = {
    pending: "等待",
    running: "进行中",
    completed: "完成",
    missing: "缺失",
    empty: "无结果",
  };
  return labels[status] || status || "完成";
}

async function handleExpertImageInput(fileList) {
  const files = Array.from(fileList || []).filter((file) => file.type.startsWith("image/"));
  if (!files.length) {
    showMessage("请选择图片文件。", true);
    return;
  }
  const availableSlots = Math.max(0, 4 - state.expertImageAttachments.length);
  if (!availableSlots) {
    showMessage("一次最多附加 4 张图片。", true);
    return;
  }
  try {
    const attachments = [];
    for (const file of files.slice(0, availableSlots)) {
      if (file.size > 1_800_000) {
        showMessage(`图片 ${file.name} 超过 1.8MB，已跳过。`, true);
        continue;
      }
      attachments.push(await readImageAttachment(file));
    }
    state.expertImageAttachments = [...state.expertImageAttachments, ...attachments];
    render();
  } catch (error) {
    showMessage(`图片读取失败：${error.message}`, true);
  }
}

function readImageAttachment(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      resolve({
        name: file.name,
        mime_type: file.type,
        size: file.size,
        data_url: String(reader.result || ""),
      });
    });
    reader.addEventListener("error", () => reject(reader.error || new Error("FileReader failed")));
    reader.readAsDataURL(file);
  });
}

async function submitAgentFeedback(button) {
  const category = button.dataset.agentFeedback || "";
  const rating = category === "helpful" ? "good" : "bad";
  button.disabled = true;
  try {
    await postJson("/api/agent/feedback", {
      turn_id: button.dataset.turnId,
      session_id: button.dataset.sessionId,
      rating,
      category,
      note: "",
    });
    showMessage("反馈已记录，后续回答会参考这个偏好。");
  } catch (error) {
    button.disabled = false;
    showMessage(error.message, true);
  }
}

async function submitExpertQuestion(paperId, includeGithub) {
  const paper = state.papers.find((item) => item.arxiv_id === paperId);
  if (!paper) return;
  const textarea = el.paperDetail.querySelector("[data-expert-question]");
  let question = (textarea?.value || "").trim();
  const imageAttachments = state.expertImageAttachments.slice();
  if (!question && includeGithub) {
    question = "请帮我找这篇论文相关的 GitHub 代码或复现仓库，并说明这些代码可以参考什么。";
  }
  if (!question && imageAttachments.length) {
    question = "请结合我上传的图片和当前论文内容进行解释。";
  }
  if (!question) {
    showMessage("先输入你想问论文专家的问题。", true);
    return;
  }

  setBusy(true);
  state.agentStatus = "连接中…";
  render();
  showMessage(includeGithub ? "论文专家正在结合 GitHub 检索回答。" : "论文专家正在阅读站内信息并回答。");

  try {
    const session = await ensureExpertSession(paper);
    const payload = {
      question,
      include_github: includeGithub,
      github_limit: 5,
      session_id: session.id,
      history: expertHistoryForPayload(paper),
      image_attachments: imageAttachments,
    };

    let response;
    try {
      response = await fetch(`/api/papers/${encodeURIComponent(paperId)}/expert-chat-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (err) {
      throw new Error(`请求被中断：${err.message}`);
    }

    if (!response.ok) {
      let msg = `服务返回错误 (${response.status})`;
      try {
        const errData = await response.json();
        msg = errData.error || msg;
      } catch {}
      throw new Error(msg);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let finalData = null;
    let streamError = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let eventType = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const raw = line.slice(6);
          try {
            const data = JSON.parse(raw);
            if (eventType === "status") {
              state.agentStatus = data.message || "处理中…";
              render();
            } else if (eventType === "step") {
              state.agentStatus = data.message || data.step || "执行中…";
              render();
            } else if (eventType === "tool") {
              state.agentStatus = `工具调用 · ${data.tool || data.message || "…"}`;
              render();
            } else if (eventType === "answer") {
              finalData = data;
            } else if (eventType === "complete") {
              finalData = finalData || data;
            } else if (eventType === "error") {
              streamError = data.error || data.message || "未知错误";
            }
          } catch {}
          eventType = "";
        }
      }
    }

    if (streamError) {
      throw new Error(streamError);
    }

    if (!finalData) {
      throw new Error("未收到回答数据。");
    }

    updateExpertSessionAfterAnswer(paper, {
      id: finalData.turn_id,
      session_id: finalData.session_id,
      paper_id: finalData.paper_id,
      question,
      answer: finalData.answer,
      used_llm: finalData.used_llm,
      llm_error: finalData.llm_error,
      github_error: finalData.github_error,
      github_repositories: finalData.github_repositories || [],
      plan: finalData.plan || [],
      tool_calls: finalData.tool_calls || [],
      reflection: finalData.reflection || null,
      memory_used: finalData.memory_used || [],
      image_attachments: finalData.image_attachments || imageAttachments,
    });
    state.expertImageAttachments = [];
    state.agentStatus = "";
    render();
    loadExpertSessions();
    scrollToDetailTarget("expertChatPanel");
    showMessage(finalData.used_llm ? "论文专家已用 LLM 回答。" : "论文专家已用本地结构化信息回答。");
  } catch (error) {
    state.agentStatus = "";
    render();
    showMessage(error.message, true);
  } finally {
    setBusy(false);
  }
}

function expertHistoryForPayload(paper) {
  const session = currentExpertSessionForPaper(paper);
  return (session?.messages || paper.expertChat || []).slice(-6).map((turn) => ({
    question: turn.question || "",
    answer: turn.answer || "",
  }));
}

function renderRecommendationSpotlight(paper) {
  const items = paper.related || [];
  if (!items.length) {
    return `
      <section id="recommendationSpotlight" class="recommendation-spotlight empty-recommendation">
        <div>
          <h3>相似论文推荐</h3>
          <p>还没有生成推荐。点击上方“相似推荐”，系统会基于当前论文从本地论文库里找相近论文。</p>
        </div>
      </section>
    `;
  }
  return `
    <section id="recommendationSpotlight" class="recommendation-spotlight">
      <div class="spotlight-heading">
        <div>
          <h3>相似论文推荐</h3>
          <p>这些是系统根据当前论文匹配出的候选论文，适合拿来做相关工作和创新对比。</p>
        </div>
        <span>${items.length} 条</span>
      </div>
      <div class="recommendation-grid">
        ${items.slice(0, 8).map((item, index) => renderRecommendationCard(item, index)).join("")}
      </div>
    </section>
  `;
}

function renderRecommendationCard(item, index) {
  const localPaper = findLocalPaperForRecommendation(item);
  const sourceAction = item.url
    ? `<a class="recommendation-link" href="${escapeAttribute(item.url)}" target="_blank" rel="noopener">打开出处</a>`
    : "";
  const resolvePayload = recommendationResolvePayload(item, localPaper);
  const stationAction = `<button class="recommendation-link primary" data-open-related="${escapeAttribute(resolvePayload)}" type="button">展开总结</button>`;
  const title = `<button class="recommendation-title-button" data-open-related="${escapeAttribute(resolvePayload)}" type="button">${escapeHtml(item.title)}</button>`;

  return `
    <article class="recommendation-card ${localPaper ? "local-recommendation" : ""}">
      <span class="recommendation-rank">R${index + 1}</span>
      <h4>${title}</h4>
      <p>${escapeHtml(item.reason || item.source || "基于本地标签、标题和摘要相似度推荐。")}</p>
      <div class="recommendation-actions">
        ${stationAction}
        ${sourceAction}
      </div>
      ${item.score ? `<small>相似分：${escapeHtml(item.score)}</small>` : ""}
    </article>
  `;
}

async function openRelatedPaper(rawPayload) {
  if (!rawPayload) return;
  const payload = parseRecommendationPayload(rawPayload);
  let paper = payload.paper_id ? state.papers.find((item) => item.arxiv_id === payload.paper_id) : null;
  if (!paper) {
    paper = findLocalPaperForRecommendation(payload);
  }
  if (!paper) {
    try {
      const params = new URLSearchParams();
      if (payload.paper_id) params.set("paper_id", payload.paper_id);
      if (payload.title) params.set("title", payload.title);
      if (payload.url) params.set("url", payload.url);
      const data = await getJson(`/api/papers/resolve?${params.toString()}`);
      paper = data.paper;
      const index = state.papers.findIndex((item) => item.arxiv_id === paper.arxiv_id);
      if (index >= 0) {
        state.papers[index] = paper;
      } else {
        state.papers.unshift(paper);
      }
    } catch (error) {
      showMessage("这篇推荐论文还没有收录到本地库，暂时只能打开出处。", true);
      return;
    }
  }
  const current = state.papers.find((item) => item.arxiv_id === state.selectedId);
  if (current) {
    pushDetailHistory({
      label: "返回推荐列表",
      relatedPreviewId: null,
      scrollTarget: "recommendationSpotlight",
    });
    current.relatedPreview = paper;
  }
  render();
  scrollToDetailTarget("relatedSummaryPreview");
  showMessage(`已展开推荐论文总结：${paper.title}`);
}

function promoteRelatedPaper(paperId) {
  const paper = state.papers.find((item) => item.arxiv_id === paperId);
  if (!paper) return;
  pushDetailHistory({
    label: "返回原论文推荐列表",
    relatedPreviewId: null,
    scrollTarget: "recommendationSpotlight",
  });
  state.selectedId = paperId;
  state.activeView = "library";
  state.keyword = "";
  el.searchInput.value = "";
  selectNav("library");
  render();
  if (el.paperDetail) el.paperDetail.scrollTop = 0;
  showMessage(`已切换为当前论文：${paper.title}`);
}

function closeRelatedPreview() {
  const current = state.papers.find((item) => item.arxiv_id === state.selectedId);
  if (current) current.relatedPreview = null;
  render();
}

function returnToRecommendationList() {
  const current = state.papers.find((item) => item.arxiv_id === state.selectedId);
  if (current) current.relatedPreview = null;
  render();
  scrollToDetailTarget("recommendationSpotlight");
}

function pushDetailHistory(options = {}) {
  if (!state.selectedId) return;
  const current = state.papers.find((item) => item.arxiv_id === state.selectedId);
  const relatedPreviewId = Object.prototype.hasOwnProperty.call(options, "relatedPreviewId")
    ? options.relatedPreviewId
    : current?.relatedPreview?.arxiv_id || null;
  state.detailHistory.push({
    selectedId: state.selectedId,
    activeView: state.activeView,
    keyword: state.keyword,
    detailScrollTop: el.paperDetail?.scrollTop || 0,
    relatedPreviewId,
    scrollTarget: options.scrollTarget || "",
    label: options.label || "",
  });
  if (state.detailHistory.length > 20) {
    state.detailHistory.shift();
  }
}

function restoreDetailHistory() {
  const previous = state.detailHistory.pop();
  if (!previous) return;
  state.selectedId = previous.selectedId;
  state.activeView = previous.activeView || "library";
  state.keyword = previous.keyword || "";
  el.searchInput.value = state.keyword;
  selectNav(state.activeView);

  const paper = state.papers.find((item) => item.arxiv_id === previous.selectedId);
  if (paper) {
    paper.relatedPreview = previous.relatedPreviewId
      ? state.papers.find((item) => item.arxiv_id === previous.relatedPreviewId) || null
      : null;
  }

  render();
  if (previous.scrollTarget) {
    scrollToDetailTarget(previous.scrollTarget);
  } else if (el.paperDetail) {
    window.setTimeout(() => {
      el.paperDetail.scrollTop = previous.detailScrollTop || 0;
    }, 0);
  }
}

function scrollToDetailTarget(targetId) {
  window.setTimeout(() => {
    document.querySelector(`#${targetId}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 0);
}

function findLocalPaperForRecommendation(item) {
  if (item.paper_id) {
    const byId = state.papers.find((paper) => paper.arxiv_id === item.paper_id);
    if (byId) return byId;
  }
  const itemUrl = String(item.url || "").trim();
  if (itemUrl) {
    const byUrl = state.papers.find((paper) => paper.entry_url === itemUrl || paper.pdf_url === itemUrl);
    if (byUrl) return byUrl;
  }
  const itemTitle = normalizePaperTitle(item.title);
  if (!itemTitle) return null;
  return state.papers.find((paper) => {
    const paperTitle = normalizePaperTitle(paper.title);
    return paperTitle === itemTitle || titlesLookSimilar(paperTitle, itemTitle);
  }) || null;
}

function recommendationResolvePayload(item, localPaper) {
  return JSON.stringify({
    paper_id: localPaper?.arxiv_id || item.paper_id || "",
    title: item.title || "",
    url: item.url || "",
  });
}

function parseRecommendationPayload(value) {
  try {
    const parsed = JSON.parse(value);
    return {
      paper_id: String(parsed.paper_id || ""),
      title: String(parsed.title || ""),
      url: String(parsed.url || ""),
    };
  } catch (error) {
    return { paper_id: String(value || ""), title: "", url: "" };
  }
}

function renderRelatedSummaryPreview(paper) {
  if (!paper) return "";
  const summary = paper.summary || {};
  return `
    <section id="relatedSummaryPreview" class="related-summary-preview">
      <div class="spotlight-heading">
        <div>
          <h3>推荐论文站内总结</h3>
          <p>这里直接展示推荐论文的站内信息，不会跳到外部网页。</p>
        </div>
        <button class="recommendation-link" data-close-related-preview type="button">收起</button>
      </div>
      <h4>${escapeHtml(paper.title)}</h4>
      <div class="paper-meta">
        <span>${escapeHtml(sourceLabel[paper.source] || paper.source || "未知来源")}</span>
        <span>${escapeHtml((paper.published || "").slice(0, 10) || "未知日期")}</span>
        <span>引用 ${paper.citation_count || 0}</span>
      </div>
      <div class="tag-row">
        <span class="tag priority-${summary.reading_priority || "medium"}">${escapeHtml(priorityLabel[summary.reading_priority] || summary.reading_priority || "中优先级")}</span>
        ${(paper.tags || summary.method_tags || []).slice(0, 6).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
      </div>
      <div class="related-summary-grid">
        <section>
          <h5>摘要速览</h5>
          <p>${escapeHtml(summary.short_summary || paper.abstract || "暂无摘要。")}</p>
        </section>
        <section>
          <h5>相关性判断</h5>
          <p>${escapeHtml(summary.relevance || "暂无相关性判断。")}</p>
        </section>
      </div>
      <section class="related-summary-points">
        <h5>关键要点</h5>
        ${renderListItems((summary.key_points || []).slice(0, 5))}
      </section>
      ${summary.deep_summary ? `
        <section class="related-summary-points">
          <h5>深度解读</h5>
          <p>${escapeHtml(summary.deep_summary)}</p>
        </section>
      ` : ""}
      <div class="recommendation-actions">
        <button class="recommendation-link" data-return-recommendations type="button">返回推荐列表</button>
        <button class="recommendation-link primary" data-promote-related="${escapeAttribute(paper.arxiv_id)}" type="button">作为当前论文打开</button>
        ${paper.entry_url ? `<a class="recommendation-link" href="${escapeAttribute(paper.entry_url)}" target="_blank" rel="noopener">打开出处</a>` : ""}
      </div>
    </section>
  `;
}

function normalizePaperTitle(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/在线\s*\(?\d*\)?/g, "")
    .replace(/\bpdf\b/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function titlesLookSimilar(left, right) {
  if (!left || !right) return false;
  const shorter = left.length < right.length ? left : right;
  const longer = left.length < right.length ? right : left;
  if (shorter.length >= 24 && longer.includes(shorter)) return true;
  const leftWords = new Set(left.split(" ").filter((word) => word.length > 3));
  const rightWords = right.split(" ").filter((word) => word.length > 3);
  if (!leftWords.size || !rightWords.length) return false;
  const overlap = rightWords.filter((word) => leftWords.has(word)).length;
  return overlap >= Math.min(6, Math.ceil(rightWords.length * 0.72));
}

function renderInnovationAdvice(items = []) {
  if (!items.length) return "";
  return `
    <section class="innovation-advice">
      <div class="spotlight-heading">
        <div>
          <h3>基于上传论文和推荐论文的创新建议</h3>
          <p>这是系统给你的研究切入点，不是最终结论，建议再结合正文实验和导师方向筛选。</p>
        </div>
      </div>
      <div class="advice-list">
        ${items.map((item, index) => `
          <article class="advice-card">
            <span class="recommendation-rank">I${index + 1}</span>
            <h4>${escapeHtml(item.title)}</h4>
            <p><strong>为什么值得做：</strong>${escapeHtml(item.why)}</p>
            <p><strong>可以怎么做：</strong>${escapeHtml(item.how)}</p>
            ${(item.evidence || []).length ? `<div class="tag-row">${item.evidence.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderReportPanel(lastReport) {
  el.paperDetail.className = "paper-detail";
  const reportUrl = lastReport?.url || "/reports/papers.md";
  el.paperDetail.innerHTML = `
    <h2 class="detail-title">阅读报告</h2>
    <p class="panel-note">这里会把当前论文库整理成 Markdown 阅读清单，包含优先级、中文摘要、关键要点、创新点和深度解读字段。</p>
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
    <section class="detail-block deep-reading-block">
      <h3>${summary.llm_model ? "LLM 深度解读" : "深度解读"} ${summary.llm_model ? `<span class="paper-meta">${escapeHtml(summary.llm_model)}</span>` : ""}</h3>
      <div class="deep-reading-grid">
        ${rows.map(([title, value]) => `
          <article class="deep-reading-card">
            <h4>${escapeHtml(title)}</h4>
            <p>${escapeHtml(value)}</p>
          </article>
        `).join("")}
      </div>
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
    state.papers[index] = {
      ...paper,
      related: state.papers[index].related,
      relatedPreview: state.papers[index].relatedPreview,
      innovationAdvice: state.papers[index].innovationAdvice,
      expertChat: state.papers[index].expertChat,
    };
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
  // 同时支持旧的 inline message 和 toast
  el.message.hidden = false;
  el.message.textContent = text;
  el.message.classList.toggle("error", isError);
  window.clearTimeout(showMessage._timer);
  showMessage._timer = window.setTimeout(() => { el.message.hidden = true; }, 4000);

  // Toast 通知
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast' + (isError ? ' error' : ' success');
  toast.textContent = text;
  container.appendChild(toast);
  toast.addEventListener('animationend', (e) => {
    if (e.animationName === 'fadeOut') toast.remove();
  });
}

function initToastContainer() {
  const container = document.createElement('div');
  container.id = 'toastContainer';
  container.className = 'toast-container';
  document.body.appendChild(container);
}

function confirmDialog(title, message) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "confirm-overlay";
    const dialog = document.createElement("div");
    dialog.className = "confirm-dialog";
    dialog.innerHTML = `
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(message)}</p>
      <div class="confirm-actions">
        <button class="confirm-cancel">取消</button>
        <button class="confirm-ok">确认</button>
      </div>
    `;
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add("visible"));
    const cleanup = (result) => {
      overlay.classList.remove("visible");
      setTimeout(() => overlay.remove(), 200);
      resolve(result);
    };
    dialog.querySelector(".confirm-cancel").onclick = () => cleanup(false);
    dialog.querySelector(".confirm-ok").onclick = () => cleanup(true);
    overlay.onclick = (e) => { if (e.target === overlay) cleanup(false); };
  });
}

function setBusy(isBusy) {
  document.body.classList.toggle("loading", isBusy);
  [el.addPaperButton, el.uploadPaperButton, el.collectButton, el.exportButton, el.refreshButton].forEach((button) => {
    button.disabled = isBusy;
  });
}

function selectedSources() {
  return Array.from(document.querySelectorAll('input[name="source"]:checked')).map((input) => input.value);
}

function clampNumber(value, min, max, fallback) {
  const number = Number.parseInt(value, 10);
  if (Number.isNaN(number)) return fallback;
  return Math.min(max, Math.max(min, number));
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

// ========== 论文生成 ==========

function initGeneratorView() {
  loadTemplatePapers();
  if (initGeneratorView._initialized) return;
  initGeneratorView._initialized = true;
  el.generatePaperButton.addEventListener('click', generatePaper);
  el.exportMarkdownButton.addEventListener('click', exportMarkdown);
  el.exportPdfButton.addEventListener('click', exportPdf);
}

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

async function selectTemplatePaper(paperId) {
  document.querySelectorAll('.template-paper-item').forEach(item => {
    item.classList.toggle('selected', item.dataset.paperId === paperId);
  });

  state.generator.selectedTemplate = paperId;

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

function renderPaperPreview(content) {
  const html = content
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');

  el.paperPreview.innerHTML = html;
}

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

function exportPdf() {
  showMessage('PDF 导出功能开发中...');
}

document.addEventListener('DOMContentLoaded', () => {
  initStaggerAnimation();
  initSidebarToggle();
  initToastContainer();
});

function initSidebarToggle() {
  const toggle = document.querySelector('.side-toggle');
  if (!toggle) return;
  toggle.addEventListener('click', () => {
    const filters = toggle.nextElementSibling;
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', !expanded);
    filters.hidden = expanded;
  });
}
