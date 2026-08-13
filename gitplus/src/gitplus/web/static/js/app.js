(() => {
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');

  window.GitPlus = {
    csrf: csrfMeta ? csrfMeta.content : "",
    toast(message, kind = "info") {
      const region = document.getElementById("toast-region");
      if (!region) return;
      const item = document.createElement("div");
      item.className = `toast ${kind}`;
      item.textContent = message;
      region.appendChild(item);
      setTimeout(() => item.remove(), 4200);
    },
    async api(path, options = {}) {
      const headers = new Headers(options.headers || {});
      if (options.body) headers.set("Content-Type", "application/json");
      if (options.method && options.method !== "GET") headers.set("X-CSRF-Token", window.GitPlus.csrf);
      const response = await fetch(path, {credentials: "same-origin", ...options, headers});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const error = body.error || {};
        throw new Error(error.message || "请求失败");
      }
      return body;
    }
  };
})();
