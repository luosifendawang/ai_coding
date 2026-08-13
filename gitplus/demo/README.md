# gitplus Demo

This folder contains repeatable offline demo helpers. Demo data uses fictional users, domains, and test-only tokens.

```bash
python demo/create_demo_repo.py --output /tmp/gitplus-demo
python demo/reset_demo.py --path /tmp/gitplus-demo --yes
```

The reset script only works on directories containing `.gitplus-demo`.
