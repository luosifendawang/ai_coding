(() => {
  const state = {page: 1, pages: 1};
  const byId = (id) => document.getElementById(id);
  const filters = byId("history-filters");
  const kindLabels = {git_commit: "Git Commit", commit_record: "确认记录", worklog: "工作日志"};

  function params() {
    const result = new URLSearchParams(new FormData(filters));
    for (const [key, value] of [...result]) if (!value) result.delete(key);
    return result;
  }

  async function load() {
    const query = params();
    query.set("page", state.page);
    query.set("page_size", "30");
    byId("history-loading").hidden = false;
    try {
      const data = await GitPulse.api(`/api/history?${query}`);
      state.pages = data.pages;
      render(data);
    } catch (error) {
      GitPulse.toast(error.message, "error");
    } finally {
      byId("history-loading").hidden = true;
    }
  }

  function render(data) {
    const host = byId("history-list");
    host.replaceChildren();
    data.items.forEach((item) => host.appendChild(timelineItem(item)));
    byId("history-empty").hidden = data.items.length > 0;
    byId("history-total").textContent = `${data.total} 条记录`;
    byId("history-page").textContent = `第 ${data.page} / ${data.pages} 页`;
    byId("history-prev").disabled = data.page <= 1;
    byId("history-next").disabled = data.page >= data.pages;
    byId("stat-commits").textContent = data.stats.git_commits;
    byId("stat-records").textContent = data.stats.commit_records;
    byId("stat-worklogs").textContent = data.stats.worklogs;
    byId("stat-duration").textContent = duration(data.stats.development_minutes);
    byId("stat-repositories").textContent = data.stats.repositories.length;
    byId("stat-tags").textContent = data.stats.tags.length;
  }

  function timelineItem(item) {
    const node = document.createElement("article");
    node.className = "timeline-item";
    node.dataset.kind = item.record_type;
    const meta = document.createElement("div");
    meta.className = "timeline-meta";
    meta.append(text("span", kindLabels[item.record_type] || item.record_type));
    meta.append(text("time", new Date(item.occurred_at).toLocaleString("zh-CN", {hour12: false})));
    if (item.short_hash) meta.append(text("code", item.short_hash));
    if (item.type) meta.append(text("span", item.type));
    const heading = text("h3", item.title);
    node.append(meta, heading);
    if (item.summary) node.append(text("p", item.summary));
    const details = [];
    if (item.duration_minutes) details.push(duration(item.duration_minutes));
    if (item.changed_files !== undefined) details.push(`${item.changed_files} 个文件`);
    if (item.insertions !== undefined || item.deletions !== undefined) {
      details.push(`+${item.insertions || 0} / -${item.deletions || 0}`);
    }
    if (item.branch) details.push(item.branch);
    if (item.ai_provider) details.push(`${item.ai_provider} / ${item.ai_model || "-"}`);
    if (item.tags?.length) details.push(item.tags.join(", "));
    if (details.length) node.append(text("p", details.join(" · ")));
    const detailLines = [];
    const body = Array.isArray(item.body) ? item.body.join("\n") : item.body;
    if (body) detailLines.push(body);
    if (item.ai_called !== undefined) detailLines.push(`AI 调用：${item.ai_called ? "是" : "否"}`);
    if (item.message_edited_by_user !== undefined) detailLines.push(`用户修改 Message：${item.message_edited_by_user ? "是" : "否"}`);
    if (item.security_summary) {
      const scan = item.security_summary;
      detailLines.push(`安全扫描：critical ${scan.critical || 0} / high ${scan.high || 0} / medium ${scan.medium || 0} / low ${scan.low || 0}`);
    }
    if (detailLines.length) {
      const disclosure = document.createElement("details");
      disclosure.className = "timeline-details";
      disclosure.append(text("summary", "查看详情"), text("pre", detailLines.join("\n")));
      node.append(disclosure);
    }
    return node;
  }

  function text(tag, value) {
    const node = document.createElement(tag);
    node.textContent = value;
    return node;
  }
  function duration(minutes) {
    if (!minutes) return "0h";
    const hours = Math.floor(minutes / 60);
    const remaining = minutes % 60;
    return hours ? `${hours}h ${remaining ? `${remaining}m` : ""}`.trim() : `${remaining}m`;
  }

  filters.addEventListener("submit", (event) => { event.preventDefault(); state.page = 1; load(); });
  let searchTimer;
  filters.elements.keyword.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { state.page = 1; load(); }, 300);
  });
  byId("history-prev").addEventListener("click", () => { if (state.page > 1) { state.page -= 1; load(); } });
  byId("history-next").addEventListener("click", () => { if (state.page < state.pages) { state.page += 1; load(); } });
  byId("history-export").addEventListener("click", () => {
    const query = params();
    query.set("format", byId("history-export-format").value);
    window.location.assign(`/api/history/export?${query}`);
  });
  load();
})();
