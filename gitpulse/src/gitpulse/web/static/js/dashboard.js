(() => {
  const heading = document.querySelector(".dashboard-heading");
  if (!heading) return;
  GitPulse.api("/api/dashboard")
    .then((data) => {
      heading.dataset.repositoryRevision = data.repository_revision || "";
    })
    .catch((error) => {
      GitPulse.toast(error.message, "error");
    });
})();
