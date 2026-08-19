(() => {
  const byId = (id) => document.getElementById(id);
  const state = {sources: [], draft: null};

  function iso(date) { return date.toISOString().slice(0, 10); }
  function initialDates() {
    const today = new Date();
    const day = today.getDay() || 7;
    const monday = new Date(today); monday.setDate(today.getDate() - day + 1);
    byId("date-from").value = iso(monday);
    byId("date-to").value = iso(today);
  }
  function selectedIds() {
    return [...document.querySelectorAll('.source-item input:checked')].map((node) => node.value);
  }
  function setBusy(button, busy, label) {
    button.disabled = busy;
    if (!button.dataset.label) button.dataset.label = button.textContent;
    button.textContent = busy ? label : button.dataset.label;
  }
  async function loadSources() {
    const button = byId("load-sources"); setBusy(button, true, "正在读取...");
    try {
      const query = new URLSearchParams({date_from: byId("date-from").value, date_to: byId("date-to").value});
      const data = await GitPlus.api(`/api/smart-weekly/sources?${query}`);
      state.sources = data.items; renderSources();
    } catch (error) { GitPlus.toast(error.message, "error"); }
    finally { setBusy(button, false); }
  }
  function renderSources() {
    const host = byId("source-list"); host.replaceChildren();
    const labels = {git_commit: "Git", commit_record: "确认记录", worklog: "日志"};
    state.sources.forEach((source) => {
      const label = document.createElement("label"); label.className = "source-item";
      const input = document.createElement("input"); input.type = "checkbox"; input.value = source.id; input.checked = true;
      const body = document.createElement("span");
      const meta = document.createElement("small"); meta.textContent = `${labels[source.kind] || source.kind} · ${source.occurred_at.slice(0, 10)}`;
      const title = document.createElement("strong"); title.textContent = source.title;
      body.append(meta, title); label.append(input, body); host.append(label);
    });
    byId("source-count").textContent = `${state.sources.length} 项`;
    byId("source-status").textContent = state.sources.length ? "已自动选择全部依据" : "当前周期没有记录";
  }
  async function generate() {
    const button = byId("generate"); setBusy(button, true, "正在生成...");
    try {
      const data = await GitPlus.api("/api/smart-weekly/generate", {method: "POST", body: JSON.stringify({
        date_from: byId("date-from").value, date_to: byId("date-to").value,
        source_ids: selectedIds(), use_ai: byId("use-ai").checked, extra_context: byId("extra-context").value
      })});
      setDraft(data.draft); GitPlus.toast("周报草稿已生成", "success");
    } catch (error) { GitPlus.toast(error.message, "error"); }
    finally { setBusy(button, false); }
  }
  function setDraft(draft) {
    state.draft = draft; byId("markdown").value = draft.markdown;
    byId("generator-label").textContent = draft.generator === "rule_based" ? "本地规则生成" : `${draft.generator} 生成`;
    const warnings = byId("warnings"); warnings.replaceChildren();
    (draft.warnings || []).forEach((warning) => { const p = document.createElement("p"); p.textContent = warning; warnings.append(p); });
  }
  function syncMarkdown() { if (state.draft) state.draft.markdown = byId("markdown").value; }
  async function refine() {
    if (!state.draft) return GitPlus.toast("请先生成周报", "error");
    const instruction = byId("instruction").value.trim(); if (!instruction) return GitPlus.toast("请输入调整要求", "error");
    syncMarkdown(); const button = byId("refine"); setBusy(button, true, "正在调整...");
    try {
      const data = await GitPlus.api("/api/smart-weekly/refine", {method: "POST", body: JSON.stringify({draft: state.draft, instruction})});
      setDraft(data.draft); GitPlus.toast("已应用智能调整", "success");
    } catch (error) { GitPlus.toast(error.message, "error"); }
    finally { setBusy(button, false); }
  }
  async function save() {
    if (!state.draft) return GitPlus.toast("请先生成周报", "error"); syncMarkdown();
    try { const data = await GitPlus.api("/api/smart-weekly/save", {method: "POST", body: JSON.stringify({draft: state.draft})}); GitPlus.toast(`草稿已保存：${data.id}`, "success"); }
    catch (error) { GitPlus.toast(error.message, "error"); }
  }
  function exportDraft() {
    if (!state.draft) return GitPlus.toast("请先生成周报", "error"); syncMarkdown();
    const blob = new Blob([state.draft.markdown], {type: "text/markdown;charset=utf-8"});
    const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = `smart-weekly-${state.draft.date_from}-${state.draft.date_to}.md`; link.click(); URL.revokeObjectURL(link.href);
  }
  byId("load-sources").addEventListener("click", loadSources);
  byId("select-all").addEventListener("click", () => { const boxes = [...document.querySelectorAll('.source-item input')]; const checked = boxes.some((box) => !box.checked); boxes.forEach((box) => { box.checked = checked; }); });
  byId("generate").addEventListener("click", generate); byId("refine").addEventListener("click", refine); byId("save").addEventListener("click", save); byId("export").addEventListener("click", exportDraft);
  byId("copy").addEventListener("click", async () => { await navigator.clipboard.writeText(byId("markdown").value); GitPlus.toast("已复制 Markdown", "success"); });
  document.querySelectorAll(".quick-prompts button").forEach((button) => button.addEventListener("click", () => { byId("instruction").value = button.textContent; }));
  initialDates(); loadSources();
})();
