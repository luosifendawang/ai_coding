(() => {
  const heading = document.querySelector(".dashboard-heading");
  if (!heading) return;
  GitPlus.api("/api/dashboard")
    .then((data) => {
      heading.dataset.repositoryRevision = data.repository_revision || "";
    })
    .catch((error) => {
      GitPlus.toast(error.message, "error");
    });
})();
