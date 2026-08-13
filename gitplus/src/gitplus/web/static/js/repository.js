(() => {
  const state = {
    status: null,
    revision: null,
    selected: new Set(),
    activePath: null,
    activeSource: "unstaged",
    scan: null,
    generation: null,
    candidate: "standard",
    busy: false,
  };

  const byId = (id) => document.getElementById(id);
  const buttons = {
    refresh: byId("refresh-repository"),
    scan: byId("scan-repository"),
    generate: byId("generate-commit"),
    stage: byId("stage-selected"),
    unstage: byId("unstage-selected"),
    commit: byId("open-commit-confirm"),
  };

  async function loadStatus({quiet = false} = {}) {
    setBusy(true, quiet ? "" : "正在读取仓库状态");
    try {
      const previous = state.revision;
      state.status = await gitplus.api("/api/repository/status");
      state.revision = state.status.revision;
      if (previous && previous !== state.revision) invalidateGenerated();
      state.selected.clear();
      renderStatus();
    } catch (error) {
      showAlert(error.message);
    } finally {
      setBusy(false);
    }
  }

  function renderStatus() {
    const status = state.status;
    const repo = status.repository;
    byId("repo-name").textContent = repo.name;
    byId("repo-meta").textContent = repo.root;
    byId("repo-branch").textContent = repo.branch || "Detached HEAD";
    byId("repo-head").textContent = repo.head || "尚无 Commit";
    byId("repo-identity").textContent = repo.identity_configured
      ? `${repo.git_user_name} <${repo.git_user_email}>`
      : "未配置";
    for (const key of ["staged", "unstaged", "untracked", "conflicted"]) {
      byId(`count-${key}`).textContent = status.summary[key];
    }
    const alert = byId("repository-alert");
    if (repo.has_conflicts) {
      showAlert("当前仓库存在未解决的合并冲突。请先在编辑器中解决冲突。");
    } else if (repo.detached_head) {
      showAlert("当前为 Detached HEAD。可以查看和暂存，但 Web Commit 已禁用。");
    } else if (!repo.identity_configured) {
      showAlert("未配置有效 Git 用户身份。请配置全局 user.name 和 user.email。");
    } else {
      alert.hidden = true;
    }
    renderFiles();
    updateActions();
  }

  function renderFiles() {
    const host = byId("file-groups");
    const query = byId("file-filter").value.trim().toLowerCase();
    host.replaceChildren();
    const groups = [
      ["conflicted", "冲突文件"],
      ["staged", "已暂存文件"],
      ["unstaged", "未暂存文件"],
      ["untracked", "未跟踪文件"],
    ];
    let rendered = 0;
    for (const [group, label] of groups) {
      const files = state.status.files.filter((file) => {
        const inGroup =
          group === "conflicted" ? file.conflicted :
          group === "staged" ? file.staged && !file.conflicted :
          group === "unstaged" ? file.unstaged && !file.untracked && !file.conflicted :
          file.untracked;
        return inGroup && file.display_path.toLowerCase().includes(query);
      });
      if (!files.length) continue;
      const section = document.createElement("section");
      section.className = "file-group";
      const heading = document.createElement("h3");
      heading.textContent = `${label} ${files.length}`;
      section.appendChild(heading);
      for (const file of files) section.appendChild(fileRow(file, group));
      host.appendChild(section);
      rendered += files.length;
    }
    if (!rendered) {
      const empty = document.createElement("div");
      empty.className = "pane-empty";
      empty.textContent = state.status.files.length ? "没有匹配的文件" : "当前工作区没有修改";
      host.appendChild(empty);
    }
  }

  function fileRow(file, group) {
    const row = document.createElement("div");
    row.className = "file-row";
    if (state.activePath === file.path && state.activeSource === sourceForGroup(group)) row.classList.add("active");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = state.selected.has(file.path);
    input.setAttribute("aria-label", `选择 ${file.display_path}`);
    input.addEventListener("change", () => {
      input.checked ? state.selected.add(file.path) : state.selected.delete(file.path);
      updateActions();
    });
    const open = document.createElement("button");
    open.type = "button";
    open.className = "file-open";
    open.title = file.display_path;
    const status = document.createElement("span");
    status.className = `file-status status-${file.conflicted ? "conflict" : group}`;
    status.textContent = file.conflicted ? "!" : `${file.index_status}${file.worktree_status}`;
    const path = document.createElement("span");
    path.textContent = file.display_path;
    open.append(status, path);
    open.addEventListener("click", () => openDiff(file.path, sourceForGroup(group)));
    row.append(input, open);
    return row;
  }

  const sourceForGroup = (group) => group === "staged" ? "staged" : "unstaged";

  async function openDiff(path, source) {
    state.activePath = path;
    state.activeSource = source;
    byId("diff-path").textContent = path;
    byId("diff-source").hidden = false;
    document.querySelectorAll("#diff-source button").forEach((button) => {
      button.classList.toggle("active", button.dataset.source === source);
    });
    byId("diff-viewer").textContent = "正在加载 Diff";
    renderFiles();
    try {
      const params = new URLSearchParams({path, source});
      const result = await gitplus.api(`/api/repository/diff?${params}`);
      if (result.binary) {
        byId("diff-viewer").textContent = "二进制文件不显示原始内容";
      } else {
        renderDiff(result.diff || "当前来源没有可显示的 Diff");
      }
      const notice = byId("diff-notice");
      notice.hidden = !result.truncated;
      notice.textContent = result.truncated ? `Diff 已截断，原始字符数 ${result.original_chars}` : "";
    } catch (error) {
      byId("diff-viewer").textContent = error.message;
    }
  }

  function renderDiff(text) {
    const viewer = byId("diff-viewer");
    viewer.replaceChildren();
    for (const line of text.split("\n")) {
      const item = document.createElement("span");
      item.className =
        line.startsWith("+") && !line.startsWith("+++") ? "diff-add" :
        line.startsWith("-") && !line.startsWith("---") ? "diff-delete" :
        line.startsWith("@@") ? "diff-hunk" : "diff-context";
      item.textContent = line || " ";
      viewer.appendChild(item);
    }
  }

  async function mutate(action) {
    const selected = [...state.selected];
    const paths = selected.filter((path) => state.status.files.some((file) => {
      if (file.path !== path) return false;
      return action === "stage" ? file.unstaged : file.staged;
    }));
    if (!paths.length) return;
    setBusy(true, action === "stage" ? "正在暂存文件" : "正在取消暂存");
    try {
      state.status = await gitplus.api(`/api/repository/${action}`, {
        method: "POST",
        body: JSON.stringify({paths, revision: state.revision}),
      });
      state.revision = state.status.revision;
      state.selected.clear();
      invalidateGenerated();
      renderStatus();
      gitplus.toast(action === "stage" ? "文件已暂存" : "文件已取消暂存", "success");
    } catch (error) {
      gitplus.toast(error.message, "error");
      await loadStatus({quiet: true});
    } finally {
      setBusy(false);
    }
  }

  async function scan() {
    setBusy(true, "正在执行安全扫描");
    try {
      state.scan = await gitplus.api("/api/repository/security-scan", {
        method: "POST",
        body: JSON.stringify({source: "staged", revision: state.revision}),
      });
      state.generation = null;
      renderSecurity();
      updateActions();
    } catch (error) {
      gitplus.toast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function renderSecurity() {
    const host = byId("security-result");
    host.replaceChildren();
    const title = document.createElement("h3");
    title.textContent = "安全扫描";
    host.appendChild(title);
    const summary = document.createElement("div");
    summary.className = `scan-summary ${state.scan.remote_ai_allowed ? "passed" : "blocked"}`;
    const counts = state.scan.summary;
    summary.textContent = state.scan.remote_ai_allowed
      ? `扫描通过 · Medium ${counts.medium} · Low ${counts.low}`
      : `已阻断 · Critical ${counts.critical} · High ${counts.high}`;
    host.appendChild(summary);
    for (const finding of state.scan.findings) {
      const item = document.createElement("div");
      item.className = `finding finding-${finding.severity}`;
      const strong = document.createElement("strong");
      strong.textContent = `${finding.path || "未知文件"}${finding.line ? `:${finding.line}` : ""}`;
      const message = document.createElement("span");
      message.textContent = `${finding.rule_name} · ${finding.masked_preview}`;
      item.append(strong, message);
      host.appendChild(item);
    }
    byId("assistant-state").textContent = state.scan.remote_ai_allowed ? "扫描通过" : "高风险阻断";
  }

  async function generate() {
    setBusy(true, "正在调用 AI");
    try {
      state.generation = await gitplus.api("/api/repository/commit/generate", {
        method: "POST",
        body: JSON.stringify({
          source: "staged",
          context: byId("commit-context").value || null,
          scan_id: state.scan.scan_id,
          revision: state.revision,
        }),
      });
      renderGeneration();
      gitplus.toast("Commit Message 已生成", "success");
    } catch (error) {
      gitplus.toast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function renderGeneration() {
    byId("candidate-section").hidden = false;
    const host = byId("commit-candidates");
    host.replaceChildren();
    for (const candidate of state.generation.candidates) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "candidate";
      const label = document.createElement("strong");
      label.textContent = candidate.label;
      const subject = document.createElement("span");
      subject.textContent = candidate.subject;
      button.append(label, subject);
      button.addEventListener("click", () => selectCandidate(candidate));
      host.appendChild(button);
    }
    const standard = state.generation.candidates.find((item) => item.id === "standard") || state.generation.candidates[0];
    selectCandidate(standard);
    byId("assistant-state").textContent = `${state.generation.confidence} 置信度`;
  }

  function selectCandidate(candidate) {
    state.candidate = candidate.id;
    byId("commit-subject").value = candidate.subject;
    byId("commit-body").value = candidate.body.join("\n");
    document.querySelectorAll(".candidate").forEach((button) => {
      button.classList.toggle("active", button.querySelector("strong").textContent === candidate.label);
    });
    validateDraft();
  }

  function validateDraft() {
    const subject = byId("commit-subject").value.trim();
    const valid = /^[a-z]+(?:\([A-Za-z0-9_-]+\))?: .+/.test(subject) && !subject.includes("\n");
    byId("message-validation").textContent = valid ? "Message 格式有效" : "请输入有效的 Conventional Commit Subject";
    byId("message-validation").className = valid ? "valid" : "invalid";
    buttons.commit.disabled = state.busy || !state.generation || !valid;
    return valid;
  }

  function openConfirm() {
    if (!validateDraft()) return;
    byId("confirm-repository").textContent = state.status.repository.name;
    byId("confirm-branch").textContent = state.status.repository.branch || "-";
    byId("confirm-files").textContent = state.status.summary.staged;
    byId("confirm-message").textContent = draftMessage();
    byId("commit-confirm-dialog").showModal();
  }

  const lines = (id) => byId(id).value.split("\n").map((line) => line.trim()).filter(Boolean);
  const draftMessage = () => [
    byId("commit-subject").value.trim(),
    ...lines("commit-body"),
    ...lines("commit-footer"),
  ].join("\n\n");

  async function commit() {
    setBusy(true, "正在创建 Commit");
    try {
      const result = await gitplus.api("/api/repository/commit", {
        method: "POST",
        body: JSON.stringify({
          generation_id: state.generation.generation_id,
          repository_revision: state.revision,
          selected_candidate: state.candidate,
          subject: byId("commit-subject").value.trim(),
          body: lines("commit-body"),
          footer: lines("commit-footer"),
          confirmed: true,
        }),
      });
      byId("commit-confirm-dialog").close();
      state.status = result.repository_status;
      state.revision = result.repository_revision;
      invalidateGenerated();
      renderStatus();
      gitplus.toast(`Commit ${result.commit.hash.slice(0, 8)} 创建成功，未执行 Push`, "success");
    } catch (error) {
      gitplus.toast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function invalidateGenerated() {
    state.scan = null;
    state.generation = null;
    byId("candidate-section").hidden = true;
    byId("commit-subject").value = "";
    byId("commit-body").value = "";
    byId("security-result").innerHTML = "<h3>安全扫描</h3><div class=\"pane-empty\">尚未扫描暂存区</div>";
    byId("assistant-state").textContent = "等待安全扫描";
  }

  function updateActions() {
    const selected = [...state.selected];
    const selectedFiles = state.status ? state.status.files.filter((file) => selected.includes(file.path)) : [];
    byId("selection-count").textContent = `已选择 ${selected.length} 个文件`;
    buttons.stage.disabled = state.busy || !selectedFiles.some((file) => file.unstaged);
    buttons.unstage.disabled = state.busy || !selectedFiles.some((file) => file.staged);
    const canUseStaged = state.status && state.status.summary.staged > 0 && !state.status.repository.has_conflicts;
    buttons.scan.disabled = state.busy || !canUseStaged;
    buttons.generate.disabled = state.busy || !(state.scan && state.scan.remote_ai_allowed);
    validateDraft();
  }

  function setBusy(busy, label = "") {
    state.busy = busy;
    buttons.refresh.disabled = busy;
    if (busy) {
      for (const button of Object.values(buttons)) button.disabled = true;
    }
    if (label) byId("assistant-state").textContent = label;
    if (!busy && state.status) updateActions();
  }

  function showAlert(message) {
    const alert = byId("repository-alert");
    alert.textContent = message;
    alert.hidden = false;
  }

  buttons.refresh.addEventListener("click", () => loadStatus());
  buttons.stage.addEventListener("click", () => mutate("stage"));
  buttons.unstage.addEventListener("click", () => mutate("unstage"));
  buttons.scan.addEventListener("click", scan);
  buttons.generate.addEventListener("click", generate);
  buttons.commit.addEventListener("click", openConfirm);
  byId("confirm-commit").addEventListener("click", commit);
  byId("commit-subject").addEventListener("input", validateDraft);
  byId("file-filter").addEventListener("input", renderFiles);
  byId("select-all-files").addEventListener("click", () => {
    state.status.files.filter((file) => !file.conflicted).forEach((file) => state.selected.add(file.path));
    renderFiles();
    updateActions();
  });
  document.querySelectorAll("#diff-source button").forEach((button) => {
    button.addEventListener("click", () => openDiff(state.activePath, button.dataset.source));
  });
  window.addEventListener("focus", async () => {
    if (!state.revision || state.busy) return;
    try {
      const result = await gitplus.api(`/api/repository/revision?current=${encodeURIComponent(state.revision)}`);
      if (result.changed) {
        gitplus.toast("仓库状态已变化，正在刷新", "warning");
        loadStatus({quiet: true});
      }
    } catch (_) {
      // The next explicit operation will surface connectivity errors.
    }
  });

  loadStatus();
})();
