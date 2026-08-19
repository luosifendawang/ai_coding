(() => {
  const byId = (id) => document.getElementById(id);
  const state = {status: "", current: null};
  async function loadReports(selectId = null) {
    try {
      const suffix = state.status ? `?status=${state.status}` : "";
      const data = await GitPlus.api(`/api/smart-weekly/reports${suffix}`);
      renderList(data.items);
      if (selectId && data.items.some((item) => item.id === selectId)) await openReport(selectId);
    } catch (error) { GitPlus.toast(error.message, "error"); }
  }
  function renderList(items) {
    const host = byId("report-list"); host.replaceChildren(); byId("report-empty").hidden = items.length > 0;
    items.forEach((item) => {
      const button = document.createElement("button"); button.className = `report-list-item${state.current?.id === item.id ? " active" : ""}`; button.type = "button";
      const top = document.createElement("span"); top.className = "report-list-top";
      const status = document.createElement("small"); status.className = `report-pill ${item.status}`; status.textContent = item.status === "confirmed" ? "正式" : "草稿";
      const time = document.createElement("small"); time.textContent = new Date(item.updated_at).toLocaleString("zh-CN", {hour12: false}); top.append(status, time);
      const title = document.createElement("strong"); title.textContent = item.title;
      const meta = document.createElement("small"); meta.textContent = `${item.date_from} 至 ${item.date_to} · ${item.source_count} 个来源`;
      button.append(top, title, meta); button.addEventListener("click", () => openReport(item.id)); host.append(button);
    });
  }
  async function openReport(id) {
    try {
      state.current = await GitPlus.api(`/api/smart-weekly/reports/${id}`);
      byId("report-placeholder").hidden = true; byId("report-editor").hidden = false;
      byId("report-title").value = state.current.title; byId("report-markdown").value = state.current.markdown;
      byId("report-status").textContent = state.current.status === "confirmed" ? "正式周报" : "草稿";
      byId("report-status").className = `report-status ${state.current.status}`;
      byId("report-meta").textContent = `${state.current.date_from} 至 ${state.current.date_to} · ${state.current.source_count} 个来源 · 版本 ${state.current.version} · ${state.current.generator}`;
      byId("toggle-status").textContent = state.current.status === "confirmed" ? "重新转为草稿" : "确认为正式周报";
      loadReports();
    } catch (error) { GitPlus.toast(error.message, "error"); }
  }
  async function save() {
    if (!state.current) return;
    try {
      await GitPlus.api(`/api/smart-weekly/reports/${state.current.id}`, {method: "PUT", body: JSON.stringify({title: byId("report-title").value, markdown: byId("report-markdown").value, expected_version: state.current.version})});
      GitPlus.toast("周报修改已保存", "success"); await loadReports(state.current.id);
    } catch (error) { GitPlus.toast(error.message, "error"); }
  }
  async function toggleStatus() {
    if (!state.current) return; const action = state.current.status === "confirmed" ? "reopen" : "confirm";
    try { await GitPlus.api(`/api/smart-weekly/reports/${state.current.id}/${action}`, {method: "POST"}); GitPlus.toast(action === "confirm" ? "已确认为正式周报" : "已重新转为草稿", "success"); await loadReports(state.current.id); }
    catch (error) { GitPlus.toast(error.message, "error"); }
  }
  async function remove() {
    if (!state.current || !window.confirm(`确定删除“${state.current.title}”吗？此操作不可撤销。`)) return;
    try { await GitPlus.api(`/api/smart-weekly/reports/${state.current.id}`, {method: "DELETE"}); state.current = null; byId("report-editor").hidden = true; byId("report-placeholder").hidden = false; byId("report-status").textContent = "请选择周报"; GitPlus.toast("周报已删除", "success"); await loadReports(); }
    catch (error) { GitPlus.toast(error.message, "error"); }
  }
  function exportReport() {
    if (!state.current) return; const blob = new Blob([byId("report-markdown").value], {type: "text/markdown;charset=utf-8"}); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = `smart-weekly-${state.current.date_from}-${state.current.date_to}.md`; link.click(); URL.revokeObjectURL(link.href);
  }
  byId("refresh-reports").addEventListener("click", () => loadReports()); byId("save-report").addEventListener("click", save); byId("toggle-status").addEventListener("click", toggleStatus); byId("delete-report").addEventListener("click", remove); byId("export-report").addEventListener("click", exportReport);
  document.querySelectorAll("#report-filters button").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll("#report-filters button").forEach((item) => item.classList.remove("active")); button.classList.add("active"); state.status = button.dataset.status; loadReports(); }));
  loadReports();
})();
