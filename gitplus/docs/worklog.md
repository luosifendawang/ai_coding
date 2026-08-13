# Worklog

Worklog 用于记录非代码工作，例如排查、调研、会议、支持、环境配置、测试验证、学习和文档整理。

## 类型

- `debug`
- `research`
- `meeting`
- `support`
- `setup`
- `test`
- `learning`
- `document`
- `other`

## 添加

```bash
gitplus worklog add --yes --type debug --title "排查 ADB 问题" --duration 90 --tag adb
```

## 列表

```bash
gitplus worklog list
gitplus worklog list --from 2026-07-20 --to 2026-07-26 --type debug --tag adb
gitplus worklog list --json
```

## 查看

```bash
gitplus worklog show <id>
```

## 编辑

```bash
gitplus worklog edit <id> --yes --title "新的标题" --duration 120
```

## 删除

删除默认需要确认：

```bash
gitplus worklog delete <id>
gitplus worklog delete <id> --yes
```

## 敏感信息

保存 Worklog 前会进行安全扫描。高风险 Secret 会阻止保存，避免把凭证写入本地数据库。

## 周报

后续周报阶段会读取已确认的 Worklog 并聚合为周报内容。

