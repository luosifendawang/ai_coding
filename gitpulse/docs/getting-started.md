# Getting Started

This 10 minute path uses only local data and mock AI.

```bash
pip install -e ".[dev]"
gitpulse --version
gitpulse doctor
gitpulse init
git add <files>
gitpulse check
gitpulse commit --provider mock
gitpulse worklog add --yes --type debug --title "排查问题"
gitpulse weekly --current --no-ai --confirm --output weekly.md
```

GitPulse does not run `git commit`, `git add`, `git push`, or Feishu delivery unless you explicitly ask for the corresponding command.
