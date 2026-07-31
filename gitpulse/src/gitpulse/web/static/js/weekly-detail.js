(() => {
  const root = document.querySelector(".weekly-editor-layout");
  const reportId = root.dataset.reportId;
  const state = {report: null, removed: [], dirty: false};
  const byId = (id) => document.getElementById(id);
  const sectionLabels = {
    completed: "本周完成",
    debugging: "问题与解决",
    testing: "测试与质量",
    risks: "补充说明",
    next_week: "下周计划",
  };

  async function load() {
    try {
      state.report = await GitPulse.api(`/api/weekly/${encodeURIComponent(reportId)}`);
      state.removed = [];
      state.dirty = false;
      render();
      const warnings = JSON.parse(sessionStorage.getItem("gitpulse-weekly-warnings") || "[]");
      sessionStorage.removeItem("gitpulse-weekly-warnings");
      if (warnings.length) {
        byId("weekly-warnings").textContent = warnings.join("；");
        byId("weekly-warnings").hidden = false;
      }
    } catch (error) {
      GitPulse.toast(error.message, "error");
    }
  }

  function render() {
    const report = state.report;
    byId("weekly-report-heading").textContent = report.title;
    byId("weekly-report-title").value = report.title;
    byId("weekly-report-meta").textContent = `${report.date_range.date_from} 至 ${report.date_range.date_to}`;
    byId("weekly-status").textContent = statusLabel(report.status);
    byId("weekly-coverage").textContent = `来源覆盖率 ${Math.round(report.source_coverage * 100)}%`;
    byId("weekly-version").textContent = `版本 ${report.version}`;
    const editable = report.status === "draft";
    byId("weekly-report-title").disabled = !editable;
    byId("save-weekly").hidden = !editable;
    byId("confirm-weekly").hidden = !editable;
    byId("reopen-weekly").hidden = editable;
    byId("add-manual-item").disabled = !editable;
    byId("manual-item-title").disabled = !editable;
    byId("manual-item-section").disabled = !editable;
    const host = byId("weekly-sections");
    host.replaceChildren();
    report.completed.forEach((topic, index) => host.appendChild(topicSection(topic, index, editable)));
    for (const name of ["debugging", "testing", "risks", "next_week"]) {
      host.appendChild(plainSection(name, report[name], editable));
    }
    byId("restore-item").disabled = !editable || !state.removed.length;
    updateSaveState();
  }

  function topicSection(topic, topicIndex, editable) {
    const section = sectionShell("completed");
    const title = document.createElement("input");
    title.value = topic.title;
    title.maxLength = 300;
    title.disabled = !editable;
    title.setAttribute("aria-label", "分组标题");
    title.addEventListener("input", () => { topic.title = title.value; markDirty(); });
    section.querySelector("header").prepend(title);
    topic.items.forEach((item, index) => section.appendChild(itemEditor(item, {section: "completed", topicIndex, index}, editable)));
    return section;
  }

  function plainSection(name, items, editable) {
    const section = sectionShell(name);
    const heading = document.createElement("strong");
    heading.textContent = sectionLabels[name];
    section.querySelector("header").prepend(heading);
    items.forEach((item, index) => section.appendChild(itemEditor(item, {section: name, index}, editable)));
    return section;
  }

  function sectionShell(name) {
    const section = document.createElement("section");
    section.className = "weekly-section";
    section.dataset.section = name;
    section.appendChild(document.createElement("header"));
    return section;
  }

  function itemEditor(item, location, editable) {
    const node = document.createElement("article");
    node.className = "weekly-item";
    node.addEventListener("click", () => {
      document.querySelectorAll(".weekly-item.selected").forEach((value) => value.classList.remove("selected"));
      node.classList.add("selected");
      renderSources(item);
    });
    const grid = document.createElement("div");
    grid.className = "weekly-item-grid";
    const title = field("工作项标题", item.title || item.content, "input");
    const description = field("工作描述", item.description || "", "textarea");
    const result = field("工作结果", item.result || "", "textarea");
    description.label.classList.add("wide");
    result.label.classList.add("wide");
    for (const control of [title.control, description.control, result.control]) control.disabled = !editable;
    const sync = () => {
      item.title = title.control.value.trim() || null;
      item.description = description.control.value.trim() || null;
      item.result = result.control.value.trim() || null;
      item.content = composeContent(item);
      markDirty();
    };
    title.control.addEventListener("input", sync);
    description.control.addEventListener("input", sync);
    result.control.addEventListener("input", sync);
    grid.append(title.label, description.label, result.label);
    const controls = document.createElement("div");
    controls.className = "item-controls";
    const group = document.createElement("select");
    for (const [value, label] of Object.entries(sectionLabels)) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      option.selected = value === location.section;
      group.appendChild(option);
    }
    group.disabled = !editable;
    group.addEventListener("change", () => moveItem(item, location, group.value));
    controls.append(group);
    controls.append(iconButton("上移", "↑", () => reorder(location, -1), !editable));
    controls.append(iconButton("下移", "↓", () => reorder(location, 1), !editable));
    controls.append(iconButton("删除", "×", () => removeItem(item, location), !editable));
    if (item.confidence === "medium") {
      const confirm = document.createElement("label");
      confirm.className = "confidence-toggle";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = item.confirmed_by_user;
      checkbox.disabled = !editable;
      checkbox.addEventListener("change", () => { item.confirmed_by_user = checkbox.checked; markDirty(); });
      confirm.append(checkbox, document.createTextNode("确认中可信内容"));
      controls.append(confirm);
    }
    node.append(grid, controls);
    return node;
  }

  function field(labelText, value, tag) {
    const label = document.createElement("label");
    label.appendChild(document.createTextNode(labelText));
    const control = document.createElement(tag);
    control.value = value;
    if (tag === "textarea") control.rows = 2;
    label.appendChild(control);
    return {label, control};
  }

  function iconButton(title, label, handler, disabled) {
    const button = document.createElement("button");
    button.type = "button";
    button.title = title;
    button.setAttribute("aria-label", title);
    button.textContent = label;
    button.disabled = disabled;
    button.addEventListener("click", (event) => { event.stopPropagation(); handler(); });
    return button;
  }

  function container(location) {
    return location.section === "completed"
      ? state.report.completed[location.topicIndex].items
      : state.report[location.section];
  }

  function reorder(location, direction) {
    const items = container(location);
    const target = location.index + direction;
    if (target < 0 || target >= items.length) return;
    [items[location.index], items[target]] = [items[target], items[location.index]];
    markDirty();
    render();
  }

  function removeItem(item, location) {
    const items = container(location);
    state.removed.push({item, section: location.section, topicIndex: location.topicIndex, index: location.index});
    items.splice(location.index, 1);
    markDirty();
    render();
  }

  function moveItem(item, location, destination) {
    container(location).splice(location.index, 1);
    destinationContainer(destination).push(item);
    markDirty();
    render();
  }

  function destinationContainer(section) {
    if (section !== "completed") return state.report[section];
    if (!state.report.completed.length) {
      state.report.completed.push({
        id: `topic_manual_${Date.now()}`, title: "用户补充", summary: null,
        category: "completed", items: [], sources: [], confidence: "high",
        confirmed_by_user: true,
      });
    }
    return state.report.completed[0].items;
  }

  function restore() {
    const removed = state.removed.pop();
    if (!removed) return;
    const target = removed.section === "completed" && state.report.completed[removed.topicIndex]
      ? state.report.completed[removed.topicIndex].items
      : destinationContainer(removed.section);
    target.splice(Math.min(removed.index, target.length), 0, removed.item);
    markDirty();
    render();
  }

  function addManual() {
    const title = byId("manual-item-title").value.trim();
    if (!title) return;
    destinationContainer(byId("manual-item-section").value).push({
      id: `manual_${Date.now().toString(36)}`,
      content: title, title, description: null, result: null,
      confidence: "high", sources: [], confirmed_by_user: true,
      needs_confirmation: false, notes: [],
    });
    byId("manual-item-title").value = "";
    markDirty();
    render();
  }

  function renderSources(item) {
    const host = byId("weekly-source-detail");
    host.replaceChildren();
    item.sources.forEach((source) => {
      const node = document.createElement("div");
      node.className = "source-entry";
      const title = document.createElement("strong");
      title.textContent = source.title || source.source_id;
      const meta = document.createElement("span");
      meta.textContent = `${source.source_type} · ${source.repository_name || source.repository_id || "用户补充"} · ${source.confidence}`;
      node.append(title, meta);
      if (source.commit_hash) node.append(text("span", `Commit ${source.commit_hash}`));
      if (source.files?.length) node.append(text("span", `文件：${source.files.join(", ")}`));
      host.appendChild(node);
    });
  }

  function text(tag, value) {
    const node = document.createElement(tag);
    node.textContent = value;
    return node;
  }

  function composeContent(item) {
    const title = item.title || "";
    const detail = item.result || item.description || "";
    return detail ? `${title}：${detail}` : title;
  }

  function payload() {
    const topic = (value) => ({
      id: value.id, title: value.title, summary: value.summary, category: value.category,
      items: value.items.map(itemPayload), confidence: value.confidence,
      confirmed_by_user: value.confirmed_by_user,
    });
    return {
      title: byId("weekly-report-title").value.trim(),
      completed: state.report.completed.map(topic),
      debugging: state.report.debugging.map(itemPayload),
      testing: state.report.testing.map(itemPayload),
      risks: state.report.risks.map(itemPayload),
      next_week: state.report.next_week.map(itemPayload),
    };
  }

  function itemPayload(item) {
    return {
      id: item.id, content: item.content, title: item.title,
      description: item.description, result: item.result,
      confidence: item.confidence, sources: item.sources,
      confirmed_by_user: item.confirmed_by_user, notes: item.notes || [],
    };
  }

  async function save() {
    try {
      state.report = await GitPulse.api(`/api/weekly/${encodeURIComponent(reportId)}`, {
        method: "PUT",
        body: JSON.stringify({version: state.report.version, report: payload()}),
      });
      state.dirty = false;
      GitPulse.toast("周报草稿已保存", "success");
      render();
    } catch (error) {
      GitPulse.toast(error.message, "error");
    }
  }

  async function action(name) {
    try {
      state.report = await GitPulse.api(`/api/weekly/${encodeURIComponent(reportId)}/${name}`, {
        method: "POST",
        body: JSON.stringify({version: state.report.version}),
      });
      state.dirty = false;
      GitPulse.toast(name === "confirm" ? "周报已确认" : "周报已重新打开", "success");
      render();
    } catch (error) {
      GitPulse.toast(error.message, "error");
    }
  }

  async function removeReport() {
    if (!window.confirm("确认删除这份周报？此操作无法撤销。")) return;
    try {
      await GitPulse.api(`/api/weekly/${encodeURIComponent(reportId)}?version=${state.report.version}&confirmed=true`, {method: "DELETE"});
      window.location.assign("/weekly");
    } catch (error) {
      GitPulse.toast(error.message, "error");
    }
  }

  async function exportReport() {
    const format = byId("weekly-export-format").value;
    try {
      const response = await fetch(`/api/weekly/${encodeURIComponent(reportId)}/export?format=${format}`, {credentials: "same-origin"});
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error?.message || "导出失败");
      }
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="([^"]+)"/);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = match ? match[1] : `gitpulse-weekly.${format}`;
      link.click();
      URL.revokeObjectURL(link.href);
      await load();
    } catch (error) {
      GitPulse.toast(error.message, "error");
    }
  }
  function statusLabel(status) { return {draft: "草稿", confirmed: "已确认", exported: "已导出", sent: "已发送"}[status] || status; }
  function markDirty() { state.dirty = true; updateSaveState(); }
  function updateSaveState() { byId("weekly-save-state").textContent = state.dirty ? "有未保存修改" : "已保存"; }

  byId("weekly-report-title").addEventListener("input", markDirty);
  byId("add-manual-item").addEventListener("click", addManual);
  byId("restore-item").addEventListener("click", restore);
  byId("save-weekly").addEventListener("click", save);
  byId("confirm-weekly").addEventListener("click", () => action("confirm"));
  byId("reopen-weekly").addEventListener("click", () => action("reopen"));
  byId("delete-weekly").addEventListener("click", removeReport);
  byId("weekly-export").addEventListener("click", exportReport);
  load();
})();
