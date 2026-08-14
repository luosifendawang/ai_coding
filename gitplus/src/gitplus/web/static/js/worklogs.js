(() => {
  const state = {page: 1, pages: 1, source: "manual", loading: false};
  const byId = (id) => document.getElementById(id);
  const form = byId("worklog-form");
  const dialog = byId("worklog-dialog");
  const filters = byId("worklog-filters");
  const typeLabels = {
    development: "开发", debug: "调试", review: "评审", research: "调研",
    meeting: "会议", support: "支持", test: "测试", document: "文档",
    setup: "环境", learning: "学习", other: "其他",
  };

  function query() {
    const params = new URLSearchParams(new FormData(filters));
    for (const [key, value] of [...params]) if (!value) params.delete(key);
    params.set("page", state.page);
    params.set("page_size", "20");
    return params;
  }

  async function load() {
    state.loading = true;
    byId("worklog-loading").hidden = false;
    try {
      const data = await GitPlus.api(`/api/worklogs?${query()}`);
      state.pages = data.pages;
      render(data);
    } catch (error) {
      GitPlus.toast(error.message, "error");
    } finally {
      state.loading = false;
      byId("worklog-loading").hidden = true;
    }
  }

  function render(data) {
    const host = byId("worklog-list");
    host.replaceChildren();
    data.items.forEach((item) => host.appendChild(row(item)));
    byId("worklog-empty").hidden = data.items.length > 0;
    byId("worklog-total").textContent = `${data.total} 条记录`;
    byId("worklog-page").textContent = `第 ${data.page} / ${data.pages} 页`;
    byId("worklog-prev").disabled = data.page <= 1;
    byId("worklog-next").disabled = data.page >= data.pages;
  }

  function row(item) {
    const node = document.createElement("div");
    node.className = "record-row";
    node.setAttribute("role", "row");
    const occurred = document.createElement("time");
    occurred.dateTime = item.occurred_at;
    occurred.textContent = new Date(item.occurred_at).toLocaleString("zh-CN", {hour12: false});
    const type = document.createElement("span");
    type.className = "type-chip";
    type.textContent = typeLabels[item.type] || item.type;
    const title = document.createElement("div");
    title.className = "record-title";
    const strong = document.createElement("strong");
    strong.textContent = item.title;
    const summary = document.createElement("small");
    summary.textContent = item.result || item.description || "暂无补充内容";
    title.append(strong, summary);
    const duration = document.createElement("span");
    duration.textContent = item.duration_minutes ? `${item.duration_minutes} 分钟` : "-";
    const tags = document.createElement("div");
    item.tags.forEach((tag) => {
      const chip = document.createElement("span");
      chip.className = "tag-chip";
      chip.textContent = tag;
      tags.appendChild(chip);
    });
    if (!item.tags.length) tags.textContent = "-";
    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(action("查看", () => openExisting(item.id)), action("复制", () => copyExisting(item.id)));
    node.append(occurred, type, title, duration, tags, actions);
    return node;
  }

  function action(label, handler) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", handler);
    return button;
  }

  function openNew() {
    form.reset();
    byId("worklog-id").value = "";
    byId("worklog-dialog-title").textContent = "新增工作日志";
    byId("delete-worklog").hidden = true;
    byId("worklog-occurred-at").value = localDateTime(new Date());
    state.source = "manual";
    byId("worklog-metadata").hidden = true;
    clearError();
    dialog.showModal();
  }

  async function openExisting(id) {
    try {
      fill(await GitPlus.api(`/api/worklogs/${encodeURIComponent(id)}`), false);
    } catch (error) {
      GitPlus.toast(error.message, "error");
    }
  }

  async function copyExisting(id) {
    try {
      fill(await GitPlus.api(`/api/worklogs/${encodeURIComponent(id)}`), true);
    } catch (error) {
      GitPlus.toast(error.message, "error");
    }
  }

  function fill(item, copied) {
    form.reset();
    byId("worklog-id").value = copied ? "" : item.id;
    byId("worklog-dialog-title").textContent = copied ? "复制工作日志" : "编辑工作日志";
    byId("worklog-occurred-at").value = localDateTime(copied ? new Date() : new Date(item.occurred_at));
    byId("worklog-type").value = item.type;
    byId("worklog-title").value = copied ? `${item.title}（副本）` : item.title;
    byId("worklog-description").value = item.description || "";
    byId("worklog-result").value = item.result || "";
    byId("worklog-duration").value = item.duration_minutes || "";
    byId("worklog-commit").value = item.related_commit_hash || "";
    byId("worklog-tags").value = item.tags.join(", ");
    byId("delete-worklog").hidden = copied;
    state.source = copied ? "copy" : item.source;
    byId("worklog-metadata").hidden = copied;
    byId("worklog-repository").textContent = item.repository_id || "未关联";
    byId("worklog-source").textContent = item.source;
    byId("worklog-created").textContent = new Date(item.created_at).toLocaleString("zh-CN", {hour12: false});
    byId("worklog-updated").textContent = new Date(item.updated_at).toLocaleString("zh-CN", {hour12: false});
    clearError();
    dialog.showModal();
  }

  function payload() {
    const value = byId("worklog-occurred-at").value;
    return {
      occurred_at: new Date(value).toISOString(),
      type: byId("worklog-type").value,
      title: byId("worklog-title").value.trim(),
      description: nullable(byId("worklog-description").value),
      result: nullable(byId("worklog-result").value),
      duration_minutes: byId("worklog-duration").value ? Number(byId("worklog-duration").value) : null,
      related_commit_hash: nullable(byId("worklog-commit").value),
      tags: byId("worklog-tags").value.split(",").map((tag) => tag.trim()).filter(Boolean),
      source: state.source,
    };
  }

  async function save(event) {
    event.preventDefault();
    const id = byId("worklog-id").value;
    const body = payload();
    if (id) delete body.source;
    try {
      await GitPlus.api(id ? `/api/worklogs/${encodeURIComponent(id)}` : "/api/worklogs", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(body),
      });
      dialog.close();
      GitPlus.toast(id ? "工作日志已更新" : "工作日志已创建", "success");
      await load();
    } catch (error) {
      showError(error.message);
    }
  }

  async function remove() {
    const id = byId("worklog-id").value;
    if (!id || !window.confirm("确认删除这条工作日志？此操作无法撤销。")) return;
    try {
      await GitPlus.api(`/api/worklogs/${encodeURIComponent(id)}?confirmed=true`, {method: "DELETE"});
      dialog.close();
      GitPlus.toast("工作日志已删除", "success");
      await load();
    } catch (error) {
      showError(error.message);
    }
  }

  function localDateTime(date) {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
  }
  function nullable(value) { return value.trim() || null; }
  function showError(message) {
    byId("worklog-form-error").textContent = message;
    byId("worklog-form-error").hidden = false;
  }
  function clearError() { byId("worklog-form-error").hidden = true; }

  filters.addEventListener("submit", (event) => { event.preventDefault(); state.page = 1; load(); });
  let searchTimer;
  filters.elements.keyword.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { state.page = 1; load(); }, 300);
  });
  byId("new-worklog").addEventListener("click", openNew);
  byId("delete-worklog").addEventListener("click", remove);
  byId("worklog-prev").addEventListener("click", () => { if (state.page > 1) { state.page -= 1; load(); } });
  byId("worklog-next").addEventListener("click", () => { if (state.page < state.pages) { state.page += 1; load(); } });
  form.addEventListener("submit", save);
  dialog.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => dialog.close()));
  load();
})();
