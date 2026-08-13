(() => {
  const state = { reports: [], records: [], selectedReportId: null, lastPreview: null };
  const reportList = document.getElementById("report-list");
  const recordList = document.getElementById("notification-list");
  const statusList = document.getElementById("config-status");
  const previewBox = document.getElementById("message-preview");
  const messageType = document.getElementById("message-type");
  const allowDuplicate = document.getElementById("allow-duplicate");

  const item = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const renderMeta = (target, entries) => {
    target.replaceChildren();
    entries.forEach(([label, value]) => {
      target.append(item("dt", "", label), item("dd", "", value || "-"));
    });
  };

  const load = async () => {
    try {
      const [config, reports, records] = await Promise.all([
        gitplus.api("/api/notifications/config-status"),
        gitplus.api("/api/weekly?status=confirmed&page_size=50"),
        gitplus.api("/api/notifications?page_size=12"),
      ]);
      state.reports = reports.items || [];
      state.records = records.items || [];
      renderStatus(config);
      renderReports();
      renderRecords();
    } catch (error) {
      gitplus.toast(error.message, "error");
    }
  };

  const renderStatus = (config) => {
    renderMeta(statusList, [
      ["状态", config.valid ? "可发送" : "不可发送"],
      ["模式", config.mode === "webhook" ? "Webhook" : "应用机器人"],
      ["目标", config.target],
      ["接收类型", config.receive_id_type],
      ["消息类型", config.message_type],
      ["问题", (config.issues || []).join("；")],
    ]);
  };

  const renderReports = () => {
    reportList.replaceChildren();
    if (!state.reports.length) {
      reportList.append(item("p", "empty-state", "暂无已确认周报。"));
      return;
    }
    state.reports.forEach((report) => {
      const button = item("button", "record-card", "");
      button.type = "button";
      if (report.id === state.selectedReportId) button.classList.add("selected");
      button.append(
        item("strong", "", report.title),
        item("small", "", `${report.date_from} 至 ${report.date_to}`),
        item("span", "", `版本 ${report.version} · 来源 ${Math.round((report.source_coverage || 0) * 100)}%`)
      );
      button.addEventListener("click", () => {
        state.selectedReportId = report.id;
        state.lastPreview = null;
        previewBox.textContent = "已选择周报，请生成预览。";
        renderReports();
      });
      reportList.append(button);
    });
  };

  const renderRecords = () => {
    recordList.replaceChildren();
    if (!state.records.length) {
      recordList.append(item("p", "empty-state", "暂无发送记录。"));
      return;
    }
    state.records.forEach((record) => {
      const link = item("a", "record-card", "");
      link.href = `/notifications/${encodeURIComponent(record.id)}`;
      link.append(
        item("strong", "", record.id),
        item("span", "status", record.status),
        item("small", "", `${record.provider_mode} · ${record.message_type} · ${record.created_at}`)
      );
      recordList.append(link);
    });
  };

  const preview = async () => {
    if (!state.selectedReportId) {
      gitplus.toast("请先选择周报。", "error");
      return;
    }
    try {
      const result = await gitplus.api("/api/notifications/preview", {
        method: "POST",
        body: JSON.stringify({
          report_id: state.selectedReportId,
          message_type: messageType.value,
        }),
      });
      state.lastPreview = result;
      previewBox.textContent = result.preview;
      if (result.duplicate && result.duplicate.is_duplicate) {
        gitplus.toast(result.duplicate.message, "error");
      } else if (result.truncated) {
        gitplus.toast("消息内容已自动压缩。", "info");
      }
    } catch (error) {
      gitplus.toast(error.message, "error");
    }
  };

  const send = async () => {
    if (!state.selectedReportId) {
      gitplus.toast("请先选择周报。", "error");
      return;
    }
    const report = state.reports.find((entry) => entry.id === state.selectedReportId);
    const ok = window.confirm(
      `确认发送周报：${(report && report.title) || state.selectedReportId}\n目标：${(state.lastPreview && state.lastPreview.target) || "当前飞书配置"}\n消息类型：${messageType.value}`
    );
    if (!ok) return;
    try {
      const result = await gitplus.api("/api/notifications/send", {
        method: "POST",
        body: JSON.stringify({
          report_id: state.selectedReportId,
          message_type: messageType.value,
          confirmed: true,
          allow_duplicate: allowDuplicate.checked,
        }),
      });
      if (result.message) {
        gitplus.toast(result.message, "error");
      } else {
        gitplus.toast(result.ok ? "周报已发送。" : "发送失败，已记录。", result.ok ? "success" : "error");
      }
      await load();
    } catch (error) {
      gitplus.toast(error.message, "error");
    }
  };

  const test = async () => {
    if (!window.confirm("确认向当前飞书目标发送测试消息？")) return;
    try {
      const result = await gitplus.api("/api/notifications/test", {
        method: "POST",
        body: JSON.stringify({ confirmed: true }),
      });
      const success = result.response && result.response.success;
      gitplus.toast(success ? "测试消息已发送。" : "测试失败。", success ? "success" : "error");
    } catch (error) {
      gitplus.toast(error.message, "error");
    }
  };

  const previewButton = document.getElementById("preview-button");
  const sendButton = document.getElementById("send-button");
  const testButton = document.getElementById("test-button");
  if (previewButton) previewButton.addEventListener("click", preview);
  if (sendButton) sendButton.addEventListener("click", send);
  if (testButton) testButton.addEventListener("click", test);
  if (messageType) messageType.addEventListener("change", () => {
    state.lastPreview = null;
    previewBox.textContent = "消息类型已变更，请重新生成预览。";
  });
  load();
})();
