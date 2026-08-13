# Getting Started

This 10 minute path uses only local data and mock AI.

```bash
pip install -e ".[dev]"
gitplus --version
gitplus doctor
gitplus init
git add <files>
gitplus check
gitplus commit --provider mock
gitplus worklog add --yes --type debug --title "排查问题"
gitplus weekly --current --no-ai --confirm --output weekly.md
```

gitplus does not run `git commit`, `git add`, `git push`, or Feishu delivery unless you explicitly ask for the corresponding command.
