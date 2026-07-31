(() => {
  const state = {preview: null, loading: false};
  const byId = (id) => document.getElementById(id);
  const builder = byId("weekly-builder");
  const typeLabels = {
    commit: "Git Commit", record: "确认记录", worklog: "Worklog",
    uncommitted: "未提交", user_note: "用户补充",
  };

  function rangePayload() {
    const rangeKind = builder.elements.range_kind.value;
    return {
      range_kind: rangeKind,
      date_from: rangeKind === "custom" ? byId("weekly-date-from").value || null : null,
      date_to: rangeKind === "custom" ? byId("weekly-date-to").value || null : null,
      authors: byId("weekly-authors").value.split(",").map((value) => value.trim()).filter(Boolean),
      include_uncommitted: byId("weekly-uncommitted").checked,
    };
  }

  async function preview() {
    setBusy(true);
    try {
      state.preview = await GitPulse.api("/api/weekly/preview", {
        method: "POST",
        body: JSON.stringify(rangePayload()),
      });
      renderPreview();
    } catch (error) {
      GitPulse.toast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function renderPreview() {
    const data = state.preview;
    byId("weekly-preview").hidden = false;
    byId("preview-range").textContent = `${data.date_range.date_from} 至 ${data.date_range.date_to}`;
    byId("preview-commits").textContent = data.counts.commits;
    byId("preview-records").textContent = data.counts.commit_records;
    byId("preview-worklogs").textContent = data.counts.worklogs;
    byId("preview-usable").textContent = data.counts.usable;
    byId("preview-coverage").textContent = `${Math.round(data.source_coverage * 100)}%`;
    const alert = byId("preview-alert");
    const messages = [];
    if (data.duplicates.length) messages.push(`已识别 ${data.duplicates.length} 组重复来源`);
    if (data.templates.length) messages.push(`已过滤 ${data.templates.length} 条模板记录`);
    if (data.low_information.length) messages.push(`已过滤 ${data.low_information.length} 条低信息记录`);
    alert.textContent = messages.join("；");
    alert.hidden = messages.length === 0;
    const host = byId("preview-items");
    host.replaceChildren();
    data.items.forEach((item) => host.appendChild(previewRow(item)));
    byId("preview-empty").hidden = data.items.length > 0;
    byId("generate-weekly").disabled = data.items.length === 0;
  }

  function previewRow(item) {
    const row = document.createElement("label");
    row.className = "source-preview-row";
    const selected = document.createElement("input");
    selected.type = "checkbox";
    selected.checked = true;
    selected.dataset.sourceId = item.id;
    const kind = document.createElement("span");
    kind.className = "type-chip";
    kind.textContent = typeLabels[item.source_type] || item.source_type;
    const content = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = item.title;
    const detail = document.createElement("small");
    detail.textContent = item.result || item.description || "无补充内容";
    content.append(title, detail);
    const repository = document.createElement("span");
    repository.textContent = item.repository || "当前仓库";
    row.append(selected, kind, content, repository);
    return row;
  }

  async function generate(event) {
    event.preventDefault();
    if (!state.preview) return;
    const excluded = [...document.querySelectorAll("[data-source-id]")]
      .filter((input) => !input.checked)
      .map((input) => input.dataset.sourceId);
    const payload = {
      ...rangePayload(),
      use_ai: builder.elements.generation_mode.value === "ai",
      excluded_source_ids: excluded,
      user_context: byId("weekly-context").value,
    };
    setBusy(true);
    try {
      const data = await GitPulse.api("/api/weekly/generate", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      sessionStorage.setItem("gitpulse-weekly-warnings", JSON.stringify(data.warnings || []));
      window.location.assign(`/weekly/${encodeURIComponent(data.report.id)}`);
    } catch (error) {
      GitPulse.toast(error.message, "error");
      setBusy(false);
    }
  }

  async function loadReports() {
    const status = byId("weekly-status-filter").value;
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    try {
      const data = await GitPulse.api(`/api/weekly${query}`);
      const host = byId("weekly-report-list");
      host.replaceChildren();
      data.items.forEach((report) => host.appendChild(reportRow(report)));
      byId("weekly-report-empty").hidden = data.items.length > 0;
    } catch (error) {
      GitPulse.toast(error.message, "error");
    }
  }

  function reportRow(report) {
    const row = document.createElement("a");
    row.className = "report-list-row";
    row.href = `/weekly/${encodeURIComponent(report.id)}`;
    const title = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = report.title;
    const dates = document.createElement("small");
    dates.textContent = `${report.date_from} 至 ${report.date_to}`;
    title.append(strong, dates);
    const status = document.createElement("span");
    status.className = "report-status";
    status.textContent = {draft: "草稿", confirmed: "已确认", exported: "已导出", sent: "已发送"}[report.status] || report.status;
    const coverage = document.createElement("span");
    coverage.textContent = `${Math.round(report.source_coverage * 100)}% 来源`;
    const version = document.createElement("span");
    version.textContent = `v${report.version}`;
    row.append(title, status, coverage, version);
    return row;
  }

  function setBusy(value) {
    state.loading = value;
    byId("preview-weekly").disabled = value;
    byId("generate-weekly").disabled = value || !state.preview?.items.length;
  }

  builder.querySelectorAll('input[name="range_kind"]').forEach((input) => {
    input.addEventListener("change", () => {
      const custom = builder.elements.range_kind.value === "custom";
      byId("weekly-date-from").disabled = !custom;
      byId("weekly-date-to").disabled = !custom;
      state.preview = null;
      byId("weekly-preview").hidden = true;
      byId("generate-weekly").disabled = true;
    });
  });
  byId("preview-weekly").addEventListener("click", preview);
  byId("weekly-status-filter").addEventListener("change", loadReports);
  builder.addEventListener("submit", generate);
  loadReports();
})();

