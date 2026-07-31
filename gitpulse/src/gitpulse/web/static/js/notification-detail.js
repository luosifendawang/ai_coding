(() => {
  const root = document.querySelector(".notification-shell");
  const notificationId = root && root.dataset ? root.dataset.notificationId || "" : "";
  const detail = document.getElementById("record-detail");
  const retryButton = document.getElementById("retry-button");
  const allowDuplicate = document.getElementById("retry-duplicate");
  let record = null;

  const item = (tag, text) => {
    const node = document.createElement(tag);
    node.textContent = text || "-";
    return node;
  };

  const render = () => {
    detail.replaceChildren();
    const entries = [
      ["通知 ID", record.id],
      ["周报 ID", record.report_id],
      ["报告版本", String(record.report_version)],
      ["机器人模式", record.provider_mode],
      ["消息类型", record.message_type],
      ["目标摘要", record.target_digest],
      ["内容指纹", record.content_hash],
      ["状态", record.status],
      ["尝试次数", String(record.attempt_count)],
      ["HTTP 状态", record.http_status ? String(record.http_status) : ""],
      ["响应码", record.response_code],
      ["响应消息", record.response_message || record.error_message],
      ["飞书消息 ID", record.feishu_message_id],
      ["创建时间", record.created_at],
      ["更新时间", record.updated_at],
    ];
    entries.forEach(([label, value]) => detail.append(item("dt", label), item("dd", value)));
    retryButton.disabled = !["failed", "unknown"].includes(record.status);
  };

  const load = async () => {
    try {
      const result = await GitPulse.api(`/api/notifications/${encodeURIComponent(notificationId)}`);
      record = result.record;
      render();
    } catch (error) {
      GitPulse.toast(error.message, "error");
    }
  };

  const retry = async () => {
    if (!record || !["failed", "unknown"].includes(record.status)) return;
    if (!window.confirm("确认重试发送这条飞书通知？")) return;
    try {
      const result = await GitPulse.api(`/api/notifications/${encodeURIComponent(notificationId)}/retry`, {
        method: "POST",
        body: JSON.stringify({
          confirmed: true,
          allow_duplicate: allowDuplicate.checked,
        }),
      });
      record = result.record;
      render();
      GitPulse.toast(result.ok ? "重试发送成功。" : "重试失败，记录已更新。", result.ok ? "success" : "error");
    } catch (error) {
      GitPulse.toast(error.message, "error");
    }
  };

  if (retryButton) retryButton.addEventListener("click", retry);
  load();
})();
