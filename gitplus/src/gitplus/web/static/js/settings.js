(() => {
  const form = document.getElementById("settings-form");
  if (!form) return;

  let effective = null;
  let revision = "";
  let dirty = false;
  const previewButton = document.getElementById("preview-config");
  const dirtyState = document.getElementById("dirty-state");
  const dialog = document.getElementById("preview-dialog");

  const getPath = (value, path) => path.split(".").reduce((current, key) => current?.[key], value);
  const setPath = (value, path, next) => {
    const parts = path.split(".");
    let current = value;
    parts.slice(0, -1).forEach((part) => {
      current[part] ||= {};
      current = current[part];
    });
    current[parts.at(-1)] = next;
  };

  const parseValue = (input) => {
    const type = input.dataset.type;
    if (type === "boolean" || type === "nullable-boolean") return input.checked;
    if (type === "number") return Number(input.value);
    if (type === "integer") return Number.parseInt(input.value, 10);
    if (type === "nullable-integer") return input.value === "" ? null : Number.parseInt(input.value, 10);
    if (type === "lines") return input.value.split("\n").map((item) => item.trim()).filter(Boolean);
    return input.value;
  };

  const displayValue = (input, value) => {
    const type = input.dataset.type;
    if (type === "boolean" || type === "nullable-boolean") input.checked = Boolean(value);
    else if (type === "lines") input.value = Array.isArray(value) ? value.join("\n") : "";
    else input.value = value ?? "";
  };

  const markDirty = () => {
    dirty = true;
    dirtyState.textContent = "有未保存修改";
    dirtyState.classList.add("dirty");
    previewButton.disabled = false;
  };

  const applyScope = () => {
    form.querySelectorAll("[data-path]").forEach((input) => {
      const row = input.closest(".field-row");
      const override = row?.querySelector("[data-override]");
      if (!override) return;
      const fieldSource = effective.sources[input.dataset.path] || "default";
      override.checked = fieldSource === "user";
      input.disabled = !override.checked;
      const source = row.querySelector("[data-source]");
      if (source) source.textContent = `来源：${sourceLabel(fieldSource)}`;
    });
  };

  const sourceLabel = (value) => ({
    default: "默认配置",
    legacy_user: "兼容用户配置",
    user: "用户配置",
  })[value] || value;

  const load = async () => {
    try {
      const [config, sources] = await Promise.all([
        GitPlus.api("/api/config/effective"),
        GitPlus.api("/api/config/sources")
      ]);
      effective = config;
      revision = config.revision;
      form.querySelectorAll("[data-path]").forEach((input) => {
        displayValue(input, getPath(config.config, input.dataset.path));
      });
      document.getElementById("config-path").textContent = `${config.configuration.path} · Revision ${revision.slice(7, 19)}`;
      document.getElementById("ai-secret-status").textContent = config.secrets["ai.api_key"].configured ? "已配置" : "未配置";
      document.getElementById("feishu-app-secret-status").textContent = config.secrets["feishu.app_secret"].configured ? "已配置" : "未配置";
      renderSources(sources);
      applyScope();
      dirty = false;
      dirtyState.textContent = "没有未保存修改";
      dirtyState.classList.remove("dirty");
      previewButton.disabled = true;
    } catch (error) {
      GitPlus.toast(error.message, "error");
    }
  };

  const renderSources = (sources) => {
    const list = document.getElementById("source-list");
    list.replaceChildren();
    ["user", "secrets"].forEach((name) => {
      const data = sources[name];
      const item = document.createElement("div");
      item.innerHTML = `<strong>${sourceLabel(name)}</strong><span>${data.path}</span><small>${data.exists ? "文件存在" : "尚未创建"} · ${data.writable ? "可写" : "不可写"}</small>`;
      list.appendChild(item);
    });
  };

  const payload = (confirmed = false) => {
    const config = {};
    const inherit = [];
    form.querySelectorAll("[data-path]").forEach((input) => {
      const override = input.closest(".field-row")?.querySelector("[data-override]");
      if (!override) return;
      if (override.checked) setPath(config, input.dataset.path, parseValue(input));
      else if (effective.sources[input.dataset.path] === "user") inherit.push(input.dataset.path);
    });
    const secretUpdates = {};
    form.querySelectorAll("[data-secret-action]").forEach((action) => {
      const path = action.dataset.secretAction;
      const value = form.querySelector(`[data-secret-value="${path}"]`);
      secretUpdates[path] = {
        action: action.value,
        value: action.value === "replace" ? value.value : null
      };
    });
    return {config, inherit, secret_updates: secretUpdates, revision, confirmed};
  };

  const showValidation = (result) => {
    form.querySelectorAll(".field-error").forEach((item) => item.remove());
    if (result.valid) {
      GitPlus.toast(result.warnings.length ? result.warnings.join(" ") : "配置校验通过", result.warnings.length ? "warning" : "success");
      return true;
    }
    result.errors.forEach((error) => {
      const input = form.querySelector(`[data-path="${error.path}"]`);
      if (!input) return;
      const message = document.createElement("span");
      message.className = "field-error";
      message.textContent = error.message;
      input.closest(".field-row").appendChild(message);
    });
    GitPlus.toast("配置校验失败", "error");
    return false;
  };

  const preview = async () => {
    const result = await GitPlus.api("/api/config/preview", {method: "POST", body: JSON.stringify(payload())});
    if (!showValidation(result)) return;
    const changes = document.getElementById("preview-changes");
    changes.replaceChildren();
    result.changes.forEach((change) => {
      const item = document.createElement("div");
      item.innerHTML = `<strong>${change.path}</strong><span>${String(change.old ?? "未设置")}</span><b>→</b><span>${String(change.new ?? "继承")}</span>`;
      changes.appendChild(item);
    });
    const warnings = document.getElementById("preview-warnings");
    warnings.textContent = result.warnings.join(" ");
    warnings.className = result.warnings.length ? "warning-box" : "";
    if (!result.changes.length) {
      GitPlus.toast("没有需要保存的变更");
      return;
    }
    dialog.showModal();
  };

  form.addEventListener("change", (event) => {
    const target = event.target;
    if (target.matches("[data-override]")) {
      const input = target.closest(".field-row").querySelector("[data-path]");
      input.disabled = !target.checked;
    }
    if (target.matches("[data-secret-action]")) {
      const input = form.querySelector(`[data-secret-value="${target.dataset.secretAction}"]`);
      input.disabled = target.value !== "replace";
      if (input.disabled) input.value = "";
    }
    if (target.matches('[data-path="security.enabled"]')) {
      document.getElementById("security-warning").hidden = target.checked;
    }
    markDirty();
  });
  form.addEventListener("input", markDirty);
  window.addEventListener("beforeunload", (event) => {
    if (dirty) event.preventDefault();
  });

  document.getElementById("reload-config").addEventListener("click", load);
  document.getElementById("validate-config").addEventListener("click", async () => {
    try { showValidation(await GitPlus.api("/api/config/validate", {method: "POST", body: JSON.stringify(payload())})); }
    catch (error) { GitPlus.toast(error.message, "error"); }
  });
  previewButton.addEventListener("click", () => preview().catch((error) => GitPlus.toast(error.message, "error")));
  document.getElementById("confirm-save").addEventListener("click", async () => {
    try {
      effective = await GitPlus.api("/api/config", {method: "PUT", body: JSON.stringify(payload(true))});
      dialog.close();
      GitPlus.toast("配置保存成功，已重新加载", "success");
      await load();
    } catch (error) {
      GitPlus.toast(error.message, "error");
    }
  });
  document.getElementById("restore-backup").addEventListener("click", async () => {
    if (!window.confirm("恢复最近一次全局配置备份？")) return;
    try {
      await GitPlus.api("/api/config/restore", {method: "POST"});
      GitPlus.toast("备份恢复成功", "success");
      await load();
    } catch (error) { GitPlus.toast(error.message, "error"); }
  });
  [["test-ai", "test-ai"], ["test-feishu", "test-feishu"], ["test-storage", "test-storage"]].forEach(([id, endpoint]) => {
    document.getElementById(id).addEventListener("click", async () => {
      try {
        const result = await GitPlus.api(`/api/config/${endpoint}`, {method: "POST", body: JSON.stringify(payload())});
        GitPlus.toast(result.message, result.success ? "success" : "error");
      } catch (error) { GitPlus.toast(error.message, "error"); }
    });
  });

  load();
})();
