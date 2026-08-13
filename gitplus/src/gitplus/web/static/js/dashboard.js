(() => {
  const heading = document.querySelector(".dashboard-heading");
  if (!heading) return;
  gitplus.api("/api/dashboard")
    .then((data) => {
      heading.dataset.repositoryRevision = data.repository_revision || "";
    })
    .catch((error) => {
      gitplus.toast(error.message, "error");
    });
})();
