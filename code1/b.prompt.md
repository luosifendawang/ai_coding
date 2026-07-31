# GitPulse 本地 Web 控制台第二阶段开发提示词：Git 工作台与 Commit 助手

你正在继续开发 **GitPulse——代码工作成果助手**。

当前项目已经完成：

* GitPulse CLI 基础能力
* Git 仓库读取
* Git Diff 与 Git Log
* 敏感信息扫描
* AI Commit Message
* SQLite 数据存储
* CommitRecord
* Worklog
* 周报生成
* 飞书 Webhook 通知
* 本地 Web 控制台基础框架
* Web 系统配置中心
* 本地 Session、CSRF 与 Host 校验
* 配置读取、验证、预览、备份与原子保存
* AI 和飞书连接测试

现在开始开发本地 Web 控制台第二阶段：

```text
Git 工作台
+
文件 Diff
+
暂存与取消暂存
+
安全扫描
+
AI Commit Message
+
用户确认 Commit
```

请直接在现有仓库中继续开发。

不要重新初始化项目。

不要重写现有 CLI、GitService、SecurityService、CommitService、Provider、Config Loader 或数据库模型。

Web 层必须复用现有业务 Service。

---

# 一、本阶段目标

用户能够在浏览器中完成以下完整流程：

```text
打开 GitPulse Web
    ↓
查看当前仓库和分支
    ↓
查看未暂存、已暂存、未跟踪和冲突文件
    ↓
选择文件查看 Diff
    ↓
勾选文件进行暂存
    ↓
取消暂存指定文件
    ↓
执行敏感信息扫描
    ↓
查看风险文件和风险等级
    ↓
调用 AI 生成 Commit Message
    ↓
查看多个候选 Message
    ↓
编辑最终 Message
    ↓
确认执行 git commit
    ↓
保存 CommitRecord
    ↓
刷新仓库状态
```

本阶段必须完成：

1. Git 工作台页面
2. 仓库状态 API
3. 文件状态分类
4. 文件 Diff API
5. 二进制文件处理
6. 大文件 Diff 截断
7. 文件暂存
8. 文件取消暂存
9. 批量暂存
10. 批量取消暂存
11. 安全扫描
12. 风险详情展示
13. AI Commit Message
14. AI 生成进度展示
15. AI 错误处理
16. 多候选 Commit Message
17. Message 编辑
18. Message 校验
19. 用户确认 Commit
20. CommitRecord 保存
21. Commit 后状态刷新
22. 操作审计
23. 单元测试
24. API 集成测试
25. 页面端到端测试

---

# 二、本阶段明确不实现

本阶段暂不实现：

* `git push`
* `git pull`
* `git fetch`
* `git reset --hard`
* `git clean`
* `git rebase`
* `git cherry-pick`
* `git commit --amend`
* 强制 Push
* 删除分支
* 删除 Tag
* 修改远程地址
* 合并分支
* 解决复杂冲突
* 任意 Shell 命令
* Web 终端
* Worklog 管理页面
* 周报管理页面
* 飞书发送页面
* 多仓库工作空间
* GitHub 或 GitLab 登录
* 云端部署
* 多用户协作

本阶段完成后，再开发 Worklog、周报、飞书和历史记录页面。

---

# 三、核心安全原则

所有 Git 写操作必须遵守：

```text
命令白名单
参数数组调用
禁止 shell=True
仓库范围校验
文件路径校验
写操作需要 CSRF
重要操作需要用户确认
操作后重新读取状态
错误时不隐藏真实结果
```

禁止：

```python
subprocess.run(
    user_command,
    shell=True,
)
```

禁止接受前端提交的完整 Git 命令。

前端只能提交结构化参数，例如：

```json
{
  "paths": [
    "src/gitpulse/web/app.py",
    "tests/unit/web/test_app.py"
  ]
}
```

后端负责构造固定命令：

```python
[
    "git",
    "add",
    "--",
    "src/gitpulse/web/app.py",
    "tests/unit/web/test_app.py",
]
```

---

# 四、建议目录结构

新增或扩展：

```text
src/gitpulse/web/
├── routes/
│   ├── repository_api.py
│   ├── diff_api.py
│   ├── staging_api.py
│   ├── security_api.py
│   └── commit_api.py
├── schemas/
│   ├── repository.py
│   ├── diff.py
│   ├── staging.py
│   ├── security.py
│   └── commit.py
├── services/
│   ├── repository_web_service.py
│   ├── diff_web_service.py
│   ├── staging_service.py
│   ├── commit_web_service.py
│   └── operation_audit_service.py
├── templates/
│   ├── repository.html
│   ├── commit_assistant.html
│   └── components/
│       ├── repository_summary.html
│       ├── file_status_list.html
│       ├── diff_viewer.html
│       ├── security_findings.html
│       ├── commit_candidates.html
│       ├── commit_preview.html
│       └── confirmation_dialog.html
└── static/
    ├── css/
    │   ├── repository.css
    │   └── diff.css
    └── js/
        ├── repository.js
        ├── diff-viewer.js
        ├── staging.js
        ├── security.js
        └── commit-assistant.js
```

测试：

```text
tests/unit/web/
├── test_repository_web_service.py
├── test_diff_web_service.py
├── test_staging_service.py
├── test_commit_web_service.py
└── test_repository_path_validation.py
```

```text
tests/integration/web/
├── test_repository_status_api.py
├── test_repository_diff_api.py
├── test_repository_stage_api.py
├── test_repository_unstage_api.py
├── test_repository_security_api.py
├── test_repository_commit_generate_api.py
└── test_repository_commit_api.py
```

```text
tests/e2e/web/
├── test_repository_workbench.py
└── test_commit_flow.py
```

---

# 五、页面路由

新增页面：

```text
/repository
/repository/commit
```

也可以合并为一个工作台页面：

```text
/repository
```

推荐使用单页工作台布局：

```text
仓库信息
文件状态
Diff 预览
安全扫描
Commit 助手
```

左侧导航增加：

```text
仪表盘
Git 工作台
系统配置
```

---

# 六、仓库信息区域

页面顶部显示：

```text
仓库：ai_coding
路径：/home/user/projects/ai_coding
分支：master
HEAD：43e1f1c
工作区：有修改
上次刷新：2026-07-29 13:30:00
```

同时显示统计：

```text
未暂存：12
已暂存：4
未跟踪：3
冲突：0
忽略：不展示
```

页面按钮：

```text
刷新
执行安全扫描
生成 Commit Message
```

本阶段不提供：

```text
Pull
Push
Reset
Clean
Rebase
```

---

# 七、仓库状态 API

实现：

```http
GET /api/repository/status
```

返回：

```json
{
  "repository": {
    "name": "ai_coding",
    "root": "/home/user/projects/ai_coding",
    "branch": "master",
    "head": "43e1f1c0",
    "detached_head": false,
    "is_clean": false,
    "has_conflicts": false
  },
  "summary": {
    "staged": 4,
    "unstaged": 12,
    "untracked": 3,
    "conflicted": 0
  },
  "files": [
    {
      "path": "src/gitpulse/web/app.py",
      "display_path": "src/gitpulse/web/app.py",
      "index_status": "M",
      "worktree_status": "M",
      "category": "partially_staged",
      "staged": true,
      "unstaged": true,
      "untracked": false,
      "conflicted": false,
      "binary": false
    }
  ],
  "revision": "sha256:..."
}
```

状态读取优先使用：

```bash
git status --porcelain=v2 -z
```

必须正确处理：

* 修改文件
* 新增文件
* 删除文件
* 重命名文件
* 未跟踪文件
* 已暂存文件
* 部分暂存文件
* 冲突文件
* 文件名包含空格
* 文件名包含中文
* 文件名包含换行等特殊字符

使用 `-z` 解析，不要依赖按行简单分割。

---

# 八、文件分类

页面按照以下分组显示：

```text
冲突文件
已暂存文件
未暂存文件
未跟踪文件
```

部分暂存文件同时具有：

```text
staged=true
unstaged=true
```

页面需要明确标识：

```text
部分暂存
```

不要简单把它只放在一个分组中而隐藏另一种状态。

可以在文件列表中显示双状态：

```text
M / M
```

或：

```text
已暂存修改 + 未暂存修改
```

---

# 九、仓库路径固定

Web 服务启动时确定当前仓库根目录。

例如：

```bash
gitpulse web --project /home/user/projects/ai_coding
```

之后所有 Git 操作都必须在该仓库中完成。

前端不得传入：

```text
repository_root
cwd
working_directory
```

API 请求中只传相对文件路径。

禁止前端临时切换到任意系统目录。

---

# 十、路径校验

实现统一路径校验器：

```python
class RepositoryPathValidator:
    def validate_relative_path(
        self,
        repository_root: Path,
        relative_path: str,
    ) -> Path:
        ...
```

要求：

1. 必须是字符串。
2. 不允许空字符串。
3. 不允许绝对路径。
4. 不允许路径包含空字节。
5. 解析后必须仍在仓库根目录内。
6. 不允许访问 `.git` 内部文件。
7. 不允许通过符号链接逃逸仓库。
8. 文件必须存在于当前 Git 状态中，删除文件除外。
9. 不允许路径被解释为 Git 参数。
10. Git 命令中必须在路径前加入 `--`。

拒绝：

```text
../../etc/passwd
/home/user/.ssh/id_rsa
.git/config
--force
```

支持：

```text
docs/需求设计.md
src/file with spaces.py
```

---

# 十一、文件 Diff API

实现：

```http
GET /api/repository/diff
```

参数：

```text
path
source=staged|unstaged
context=3
```

示例：

```http
GET /api/repository/diff?path=src/app.py&source=unstaged
```

返回：

```json
{
  "path": "src/app.py",
  "source": "unstaged",
  "binary": false,
  "truncated": false,
  "additions": 12,
  "deletions": 4,
  "diff": "diff --git ..."
}
```

暂存 Diff：

```bash
git diff --cached --no-ext-diff --unified=3 -- <path>
```

未暂存 Diff：

```bash
git diff --no-ext-diff --unified=3 -- <path>
```

未跟踪文件不能直接依赖普通 `git diff`。

未跟踪文本文件可以生成只读预览：

```text
新文件全文预览
```

但必须遵守：

* 最大字符数
* 敏感信息遮盖
* 二进制检测
* 编码错误处理

---

# 十二、Diff 限制

配置增加：

```yaml
web:
  diff:
    max_file_bytes: 1048576
    max_diff_chars: 200000
    default_context_lines: 3
```

规则：

* 大于限制时返回截断结果。
* 不将完整大文件加载到浏览器。
* 不将二进制内容返回浏览器。
* 不自动尝试 OCR。
* 不读取 `.git` 文件。
* 不展开超大生成文件。
* 不把 Secret 原文展示在 Diff 中。

响应可以返回：

```json
{
  "truncated": true,
  "truncation_reason": "diff_too_large",
  "original_chars": 532100,
  "returned_chars": 200000
}
```

---

# 十三、Diff 页面展示

Diff 视图至少支持：

* 文件路径
* 暂存或未暂存状态
* 新增行
* 删除行
* 上下文行
* 行号
* 二进制提示
* 截断提示
* 安全风险标记

建议样式：

```text
新增行：+
删除行：-
上下文：普通样式
风险行：额外警告图标
```

禁止从公共 CDN 加载代码高亮库。

可以使用本地 CSS 实现基础 Diff 样式。

---

# 十四、暂存文件 API

实现：

```http
POST /api/repository/stage
```

请求：

```json
{
  "paths": [
    "src/gitpulse/web/app.py",
    "tests/test_web.py"
  ],
  "revision": "sha256:..."
}
```

处理顺序：

```text
校验 Session
    ↓
校验 CSRF
    ↓
校验仓库 Revision
    ↓
校验所有路径
    ↓
检查文件是否处于可暂存状态
    ↓
执行 git add -- <paths>
    ↓
重新读取 Git 状态
    ↓
返回新状态和 Revision
```

命令：

```python
[
    "git",
    "add",
    "--",
    *validated_paths,
]
```

不得使用：

```bash
git add .
```

不得在后端拼接 Shell 字符串。

---

# 十五、批量暂存限制

一次批量暂存建议限制：

```text
最多 500 个文件
```

超过限制返回错误：

```json
{
  "error": {
    "code": "too_many_paths",
    "message": "一次最多暂存 500 个文件。"
  }
}
```

如果路径中有一个非法文件：

* 整个请求失败
* 不执行部分暂存
* 返回具体非法路径
* 不泄露仓库外路径信息

---

# 十六、“暂存全部”设计

页面可以提供：

```text
选择全部可暂存文件
```

但按钮不能直接执行：

```bash
git add .
```

必须先：

1. 读取当前状态。
2. 获取所有可暂存文件。
3. 排除 GitPulse 本地文件。
4. 排除配置中的默认忽略目录。
5. 展示即将暂存的文件数量。
6. 用户确认。
7. 发送明确路径数组。
8. 后端逐项校验。
9. 执行一次参数化 `git add -- <paths>`。

默认警告以下路径：

```text
.env
.env.*
.venv/
venv/
node_modules/
dist/
build/
*.db
*.sqlite
*.pem
*.key
*.p12
*.pfx
```

注意：

* `.gitignore` 中的文件通常不会出现在 Git 状态里。
* 已经被 Git 跟踪的敏感文件仍可能出现。
* 路径警告不能替代敏感信息扫描。

---

# 十七、取消暂存 API

实现：

```http
POST /api/repository/unstage
```

请求：

```json
{
  "paths": [
    "src/gitpulse/web/app.py"
  ],
  "revision": "sha256:..."
}
```

优先命令：

```bash
git restore --staged -- <paths>
```

需要兼容没有初始 Commit 的仓库。

对于还没有 `HEAD` 的仓库，`git restore --staged` 可能不可用，应使用安全兼容方式，例如：

```bash
git rm --cached -- <path>
```

但必须保证：

* 不删除工作区文件
* 不执行 `git rm` 的工作区删除行为
* 只从 Index 移除
* 有完整测试覆盖

不要使用：

```bash
git reset --hard
```

---

# 十八、冲突文件

检测到冲突文件时：

* 页面顶部显示明显警告。
* 禁止生成 Commit Message。
* 禁止执行 Commit。
* 允许查看冲突 Diff。
* 允许刷新状态。
* 不在本阶段提供自动解决冲突。

提示：

```text
当前仓库存在未解决的合并冲突。请先在编辑器中解决冲突，再继续生成 Commit Message。
```

---

# 十九、仓库 Revision

Git 状态页面也需要 Revision 防止并发状态变化。

Revision 可以基于：

```text
HEAD
Index 文件修改时间
Git 状态规范化结果
当前分支
```

生成 SHA-256。

写操作请求必须带 Revision。

Revision 不一致返回：

```http
409 Conflict
```

```json
{
  "error": {
    "code": "repository_changed",
    "message": "仓库状态已发生变化，请刷新后重试。"
  }
}
```

不能在用户查看页面后，静默对已经变化的仓库执行暂存或 Commit。

---

# 二十、安全扫描 API

实现：

```http
POST /api/repository/security-scan
```

请求：

```json
{
  "source": "staged",
  "revision": "sha256:..."
}
```

本阶段主要扫描暂存区。

必须复用现有安全扫描 Service。

不要在 Web 层重新实现正则规则。

响应：

```json
{
  "scan_id": "scan_xxx",
  "source": "staged",
  "status": "blocked",
  "summary": {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 0
  },
  "remote_ai_allowed": false,
  "findings": [
    {
      "id": "finding_xxx",
      "rule_id": "private_key",
      "severity": "critical",
      "path": "config/test.pem",
      "line": 1,
      "message": "检测到私钥内容",
      "masked_preview": "-----BEGIN *** KEY-----"
    }
  ]
}
```

禁止返回完整敏感值。

---

# 二十一、安全扫描展示

页面按照风险级别展示：

```text
Critical
High
Medium
Low
```

每项显示：

* 文件路径
* 行号
* 规则名称
* 风险等级
* 脱敏预览
* 处理建议

例如：

```text
config/dev.yml:12
疑似 API Token
sk-****-abcd
```

不要显示足够还原凭证的信息。

建议只显示固定遮盖：

```text
********
```

不要显示真实前后缀。

---

# 二十二、AI 调用条件

只有满足以下条件才能调用远程 AI：

1. 存在暂存文件。
2. 不存在冲突。
3. 安全扫描已完成。
4. 没有阻断级风险。
5. AI 配置有效。
6. 仓库 Revision 未变化。
7. Diff 大小没有超过系统安全上限。
8. 用户明确点击生成按钮。

出现 Critical 或 High 风险时：

```text
禁止远程 AI 调用
```

页面显示：

```text
检测到高风险敏感信息，已阻止远程 AI 调用。
```

不得提供普通用户可点击的“忽略并发送”按钮。

---

# 二十三、生成 Commit Message API

实现：

```http
POST /api/repository/commit/generate
```

请求：

```json
{
  "source": "staged",
  "context": "新增本地 Web Git 工作台",
  "scan_id": "scan_xxx",
  "revision": "sha256:..."
}
```

处理顺序：

```text
验证 Session 和 CSRF
    ↓
重新读取仓库状态
    ↓
校验 Revision
    ↓
确认存在暂存内容
    ↓
确认没有冲突
    ↓
验证安全扫描结果
    ↓
重新执行必要安全校验
    ↓
调用现有 CommitService
    ↓
解析结构化结果
    ↓
执行 Commit Message 校验
    ↓
返回候选项
```

不要完全信任前端传来的 `scan_id`。

服务端必须确认：

* Scan 对应当前仓库
* Scan 对应 staged
* Scan 对应当前 Revision
* Scan 未过期
* Scan 没有阻断项

---

# 二十四、AI 响应兼容性

当前项目已经出现过以下返回形式：

```json
{
  "answer": {
    "type": "feat",
    "subject": "..."
  }
}
```

响应解析器应兼容安全的单层包装：

```text
answer
result
data
output
```

但只有内部对象包含目标 Schema 字段时才能解包。

不得无条件接受任意嵌套结果。

---

# 二十五、推理模型处理

部分 OpenAI-compatible 模型可能返回：

```json
{
  "message": {
    "content": "",
    "reasoning_content": "..."
  },
  "finish_reason": "length"
}
```

此时不得把 `reasoning_content` 当作 Commit Message。

必须返回可理解错误：

```text
模型在生成最终 JSON 前达到输出长度上限。
请减少暂存内容、提高最大输出 Token，或关闭 Thinking 模式。
```

页面展示建议：

```text
AI 输出达到长度上限

当前暂存文件：223
新增行：13294
建议：
1. 按功能拆分暂存文件
2. 使用非推理模型
3. 提高 max_output_tokens
```

不得在页面显示 Python Traceback。

---

# 二十六、AI 生成响应

响应示例：

```json
{
  "generation_id": "generation_xxx",
  "repository_revision": "sha256:...",
  "primary_purpose": "新增本地 Web Git 工作台",
  "type": "feat",
  "scope": "web",
  "subject": "feat(web): 增加 Git 工作台",
  "body": [
    "增加仓库状态和 Diff 查看",
    "支持文件暂存与取消暂存",
    "增加安全扫描和提交确认"
  ],
  "confidence": "high",
  "should_split": false,
  "split_suggestions": [],
  "needs_confirmation": [],
  "candidates": [
    {
      "id": "concise",
      "label": "简洁",
      "subject": "feat(web): 增加 Git 工作台",
      "body": []
    },
    {
      "id": "standard",
      "label": "标准",
      "subject": "feat(web): 增加 Git 工作台",
      "body": [
        "支持文件 Diff、暂存和安全扫描"
      ]
    },
    {
      "id": "detailed",
      "label": "详细",
      "subject": "feat(web): 增加本地 Git 工作台",
      "body": [
        "增加仓库状态和文件 Diff 查看",
        "支持文件暂存与取消暂存",
        "接入安全扫描与 AI Commit Message"
      ]
    }
  ],
  "validation_warnings": [],
  "evidence": [
    {
      "path": "src/gitpulse/web/routes/repository_api.py",
      "reason": "新增仓库 API"
    }
  ]
}
```

---

# 二十七、Commit Message 页面

页面显示：

```text
生成结果
├── 主要目的
├── 类型
├── Scope
├── 置信度
├── 是否建议拆分
├── 待确认项
└── 依据文件
```

候选区：

```text
简洁
标准
详细
```

用户选择候选后，可以编辑：

* Subject
* Body
* Footer

页面必须明确：

```text
AI 生成内容仅供建议，提交前需要用户确认。
```

---

# 二十八、Commit Message 校验

保存或提交前校验：

1. Subject 不得为空。
2. Subject 不得包含换行。
3. Subject 最大长度遵循配置。
4. Type 必须符合配置允许值。
5. Scope 字符合法。
6. Body 使用统一换行。
7. 整体长度设定合理上限。
8. 禁止空 Commit Message。
9. 禁止控制字符。
10. 不允许把 Secret 扫描结果原文写入 Message。

警告可以包括：

```text
Subject 超过建议长度
缺少 Commit 类型
存在需要用户确认的信息
AI 建议拆分为多个 Commit
```

警告不一定全部阻止提交。

Critical 校验错误必须阻止提交。

---

# 二十九、执行 Commit API

实现：

```http
POST /api/repository/commit
```

请求：

```json
{
  "generation_id": "generation_xxx",
  "repository_revision": "sha256:...",
  "subject": "feat(web): 增加 Git 工作台",
  "body": [
    "增加仓库状态和 Diff 查看",
    "支持文件暂存与取消暂存"
  ],
  "confirmed": true
}
```

服务端处理：

```text
验证 Session
    ↓
验证 CSRF
    ↓
确认 confirmed=true
    ↓
重新读取仓库状态
    ↓
校验 Revision
    ↓
确认仍存在暂存内容
    ↓
确认没有冲突
    ↓
确认安全扫描仍有效
    ↓
校验 Commit Message
    ↓
创建临时 Message 文件
    ↓
执行 git commit -F <file>
    ↓
删除临时文件
    ↓
读取新 Commit Hash
    ↓
保存 CommitRecord
    ↓
刷新仓库状态
    ↓
返回结果
```

---

# 三十、Commit 命令安全

推荐：

```python
with tempfile.NamedTemporaryFile(
    mode="w",
    encoding="utf-8",
    delete=False,
) as file:
    file.write(message)
    message_path = Path(file.name)

try:
    result = subprocess.run(
        ["git", "commit", "-F", str(message_path)],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
finally:
    message_path.unlink(missing_ok=True)
```

临时文件要求：

* 权限仅当前用户可读写
* Commit 后立即删除
* 错误时也删除
* 日志不记录完整 Message 文件路径
* 不放入仓库目录
* 不使用 Shell 拼接

---

# 三十一、Commit 前确认框

用户点击“提交”后必须显示：

```text
即将创建 Git Commit

仓库：ai_coding
分支：master
暂存文件：8
新增行：245
删除行：31

Commit Message：

feat(web): 增加 Git 工作台

- 增加仓库状态和 Diff 查看
- 支持文件暂存与取消暂存

GitPulse 将执行本地 git commit。
GitPulse 不会执行 git push。

[取消] [确认提交]
```

确认框必须展示：

* 仓库
* 分支
* 文件数量
* 行数统计
* 完整 Commit Message
* 不会 Push 的说明

---

# 三十二、Commit 结果

成功响应：

```json
{
  "success": true,
  "commit": {
    "hash": "abc1234",
    "subject": "feat(web): 增加 Git 工作台",
    "branch": "master",
    "files": 8,
    "additions": 245,
    "deletions": 31
  },
  "record_id": "record_xxx",
  "repository_status": {},
  "repository_revision": "sha256:..."
}
```

页面显示：

```text
Commit 创建成功

abc1234 feat(web): 增加 Git 工作台

GitPulse 没有执行 Push。
```

按钮：

```text
复制 Commit Hash
查看 Commit
返回工作台
```

---

# 三十三、CommitRecord 保存

必须复用现有 CommitRecord 数据模型和 Repository。

记录至少包括：

* Repository Root 或 Repository ID
* Branch
* Commit Hash
* Subject
* Body
* AI Provider
* Model
* AI 是否调用
* 用户是否编辑
* 暂存文件数量
* Additions
* Deletions
* 安全扫描结果摘要
* 生成时间
* 提交时间
* 证据文件
* Generation ID

不得保存：

* 原始 API Key
* 飞书 Secret
* Authorization Header
* 未脱敏敏感信息
* 完整原始 Diff，除非现有配置明确允许且已脱敏

---

# 三十四、用户编辑记录

记录 AI 原始建议和最终提交结果的差异，但不需要存完整 Diff。

例如：

```json
{
  "ai_subject": "feat(web): 增加 Git 工作台",
  "final_subject": "feat(web): 实现本地 Git 工作台",
  "edited_by_user": true
}
```

便于后续评估 AI 建议质量。

---

# 三十五、操作审计

本地数据库新增或复用操作记录：

```text
repository_status_read
diff_read
files_staged
files_unstaged
security_scan
commit_generated
commit_created
commit_failed
```

记录：

* 操作类型
* 时间
* 仓库标识
* 文件数量
* 成功或失败
* 错误码
* Session ID 摘要

禁止记录：

* Session Token
* CSRF Token
* Cookie
* API Key
* 飞书凭证
* 完整 Diff
* 敏感值
* 完整 Authorization Header

---

# 三十六、错误格式

统一使用：

```json
{
  "error": {
    "code": "repository_changed",
    "message": "仓库状态已变化，请刷新后重试。",
    "details": []
  }
}
```

错误码至少包括：

```text
not_a_git_repository
repository_unavailable
repository_changed
repository_has_conflicts
no_staged_changes
invalid_repository_path
path_outside_repository
path_not_in_status
too_many_paths
git_stage_failed
git_unstage_failed
diff_too_large
binary_diff
security_scan_failed
security_blocked
ai_not_configured
ai_authentication_failed
ai_rate_limited
ai_timeout
ai_output_length_exceeded
ai_response_invalid
commit_message_invalid
commit_failed
commit_record_failed
```

普通页面不得显示 Traceback。

---

# 三十七、页面刷新策略

仓库状态不会自动长期保持。

至少支持：

```text
手动刷新
写操作后自动刷新
页面重新获得焦点时检查 Revision
```

可以每 10 秒轻量检查 Revision，但本阶段不要求 WebSocket。

不要每秒读取完整 Diff。

推荐接口：

```http
GET /api/repository/revision
```

只返回：

```json
{
  "revision": "sha256:...",
  "changed": false
}
```

---

# 三十八、并发操作

同一浏览器快速点击多次时：

* Stage 按钮请求期间禁用。
* Commit 请求期间禁用所有 Git 写按钮。
* 后端仍必须有 Revision 校验。
* 同一仓库同一时间只允许一个 Git 写操作。

可以使用进程内锁：

```python
threading.Lock
```

或异步锁。

本阶段是单进程本地服务，进程内锁可以接受。

锁必须按仓库维度管理。

---

# 三十九、Git 命令超时

建议：

```text
status：10 秒
diff：20 秒
stage：30 秒
unstage：30 秒
commit：60 秒
```

超时后：

* 终止子进程
* 返回标准错误
* 记录脱敏日志
* 重新读取仓库状态
* 不假设操作一定失败或一定成功

Commit 超时时要进入“不确定状态”处理：

```text
重新读取 HEAD
检查是否产生了新 Commit
```

避免实际已经提交成功但页面显示失败后用户重复提交。

---

# 四十、Git Hook 处理

执行 `git commit` 时，仓库中的 Hook 可能：

* 修改文件
* 拒绝提交
* 输出错误
* 运行很久
* 创建新的暂存状态

页面应显示经过限制的 Hook 输出。

不能绕过 Hook：

```bash
git commit --no-verify
```

本阶段不提供跳过 Hook 的选项。

Hook 执行后无论成功失败，都重新读取仓库状态。

---

# 四十一、空 Commit

本阶段不允许通过 Web 创建空 Commit。

不要提供：

```bash
git commit --allow-empty
```

没有暂存变更时返回：

```text
当前没有已暂存变更。
```

---

# 四十二、Git Identity

提交前检查有效 Git 身份：

```bash
git config --get user.name
git config --get user.email
```

这里必须读取 Git 的有效配置，不应只读取 `--local`。

有效优先级由 Git 自己处理：

```text
仓库级
用户全局级
系统级
```

如果未配置，页面阻止 Commit，并提示：

```text
未配置 Git 用户身份。

可以执行：

git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

系统配置页面也可以显示 Git 身份状态，但本阶段不通过 Web 自动修改全局 Git 配置。

---

# 四十三、分支状态

支持：

* 普通分支
* Detached HEAD 只读展示
* 尚无 Commit 的新仓库

Detached HEAD 时：

* 允许查看状态和 Diff
* 允许暂存
* 默认阻止 Web Commit
* 显示明确警告

也可以允许提交，但首版建议阻止，降低误操作风险。

---

# 四十四、页面交互流程

页面加载：

```text
读取仓库状态
    ↓
显示文件分组
    ↓
用户选择文件
    ↓
加载对应 Diff
```

用户暂存：

```text
勾选未暂存文件
    ↓
点击暂存
    ↓
显示确认数量
    ↓
执行暂存
    ↓
刷新状态
```

用户生成 Message：

```text
确认已暂存文件
    ↓
执行安全扫描
    ↓
显示扫描结果
    ↓
扫描允许远程 AI
    ↓
生成 Commit Message
    ↓
显示候选项
```

用户提交：

```text
选择或编辑 Message
    ↓
校验
    ↓
显示最终确认框
    ↓
执行 Commit
    ↓
保存 CommitRecord
    ↓
刷新状态
```

---

# 四十五、页面状态管理

前端至少维护：

```text
repositoryRevision
selectedPaths
activeDiffPath
activeDiffSource
securityScanId
generationId
commitDraft
operationInProgress
```

仓库 Revision 变化时：

* 清除旧 Scan ID
* 清除旧 Generation ID
* 标记 AI Message 已过期
* 要求重新扫描和生成

不要允许使用旧 Diff 对新仓库状态执行 Commit。

---

# 四十六、界面布局

推荐：

```text
顶部：仓库摘要与操作状态

左侧：
├── 冲突文件
├── 已暂存文件
├── 未暂存文件
└── 未跟踪文件

中间：
└── Diff 查看器

右侧：
├── 安全扫描
├── AI Commit Message
├── 候选项
└── 提交确认
```

窄屏时改为上下布局。

---

# 四十七、空状态

必须设计以下空状态：

```text
仓库干净
没有已暂存文件
没有未暂存文件
没有 Git Commit
没有安全风险
AI 尚未配置
安全扫描尚未执行
AI Message 尚未生成
```

例如：

```text
当前工作区没有修改。
```

而不是显示空白页面。

---

# 四十八、加载状态

操作过程中显示：

```text
正在读取仓库状态
正在加载 Diff
正在暂存文件
正在执行安全扫描
正在生成 Commit Message
正在创建 Commit
```

按钮禁用并防止重复点击。

AI 调用时间较长时显示：

```text
正在调用云端 AI，请勿关闭页面。
```

但不要承诺固定完成时间。

---

# 四十九、日志

允许记录：

```text
repository status read
repository diff read path_hash=...
repository stage count=4
repository unstage count=2
security scan critical=0 high=0
commit generation success model=...
commit created hash=abc1234
```

路径可以记录仓库相对路径或不可逆摘要。

禁止记录：

* 完整 Diff
* 敏感扫描原文
* API Key
* Authorization Header
* Session Token
* CSRF Token
* Cookie
* 完整 AI Prompt
* 完整 AI Response
* 完整 Commit 临时文件路径

---

# 五十、测试环境

测试不得：

* 操作开发者真实仓库
* 操作用户真实 HOME
* 调用真实 AI
* 调用真实飞书
* 修改全局 Git 配置
* 执行真实 Push
* 启动对外监听端口

所有 Git 测试使用：

```text
tmp_path
临时 Git 仓库
临时 HOME
临时数据库
固定 Git 用户身份
Mock AI Provider
FastAPI TestClient
```

---

# 五十一、仓库状态测试

覆盖：

1. 干净仓库
2. 未暂存修改
3. 已暂存修改
4. 部分暂存
5. 未跟踪文件
6. 删除文件
7. 重命名文件
8. 中文路径
9. 空格路径
10. 无初始 Commit
11. Detached HEAD
12. 冲突状态
13. 非 Git 仓库
14. Git 命令超时

---

# 五十二、路径安全测试

覆盖：

```text
正常相对路径
绝对路径
../ 逃逸
.git/config
符号链接逃逸
以 - 开头的文件名
中文路径
空格路径
换行路径
删除文件路径
不存在路径
状态外文件
```

确认所有 Git 命令都使用：

```text
--
```

---

# 五十三、Diff 测试

覆盖：

* 暂存 Diff
* 未暂存 Diff
* 未跟踪文件预览
* 新文件
* 删除文件
* 重命名文件
* 二进制文件
* 大文件
* 截断
* 非 UTF-8
* 中文内容
* 敏感信息遮盖
* 文件状态变化导致 Revision 冲突

---

# 五十四、暂存测试

覆盖：

* 单文件暂存
* 多文件暂存
* 暂存未跟踪文件
* 暂存删除
* 暂存部分暂存文件剩余修改
* 非法路径
* Revision 冲突
* Git 命令失败
* Git 命令超时
* 超过最大文件数量
* 重复请求
* 操作锁

---

# 五十五、取消暂存测试

覆盖：

* 普通仓库取消暂存
* 无初始 Commit 仓库
* 多文件取消暂存
* 删除文件取消暂存
* 部分暂存文件
* Revision 冲突
* 非法路径
* Git 命令失败
* 确认工作区文件未被删除

---

# 五十六、安全扫描测试

覆盖：

* 无风险
* Low
* Medium
* High
* Critical
* 扫描失败
* 扫描超时
* 删除行扫描
* 未跟踪文件扫描
* Masked Preview
* 不返回完整 Secret
* High 阻止远程 AI
* Scan 与 Revision 不一致
* 过期 Scan

---

# 五十七、AI 生成测试

覆盖：

* 正常结构化响应
* `answer` 包装
* `result` 包装
* 非法 JSON
* Schema 缺字段
* Content 为空
* `reasoning_content` 存在但 Content 为空
* `finish_reason=length`
* 401
* 403
* 429
* 500
* 网络错误
* 超时
* High 风险阻断
* 无暂存文件
* 仓库冲突
* Revision 变化
* 多主题拆分建议

---

# 五十八、Commit 测试

覆盖：

* 正常 Commit
* 用户编辑 Message
* Subject 为空
* Subject 包含换行
* Subject 超长
* 没有暂存文件
* 存在冲突
* Revision 变化
* Scan 过期
* Generation 过期
* Git Identity 缺失
* Git Hook 成功
* Git Hook 拒绝
* Git Hook 超时
* Commit 成功后保存记录
* CommitRecord 保存失败
* 临时 Message 文件删除
* 不执行 Push
* 不允许空 Commit
* 重复点击防护
* Commit 超时后检查 HEAD

---

# 五十九、页面 E2E 测试

完整场景一：

```text
创建临时仓库
    ↓
修改一个文件
    ↓
打开 Web 工作台
    ↓
查看未暂存文件
    ↓
查看 Diff
    ↓
暂存文件
    ↓
执行安全扫描
    ↓
Mock AI 生成 Message
    ↓
选择候选
    ↓
编辑 Subject
    ↓
确认 Commit
    ↓
验证 Git Log
    ↓
验证 CommitRecord
```

场景二：

```text
创建含测试 Token 的文件
    ↓
暂存
    ↓
执行安全扫描
    ↓
显示 High 风险
    ↓
AI 按钮禁用
    ↓
Commit 按钮禁用
```

场景三：

```text
页面加载仓库
    ↓
外部修改仓库状态
    ↓
用户点击暂存
    ↓
API 返回 409
    ↓
页面提示刷新
```

---

# 六十、性能目标

建议目标：

* 仓库状态读取：2 秒以内
* 单文件普通 Diff：1 秒以内
* 暂存操作：3 秒以内
* 取消暂存：3 秒以内
* 本地安全扫描：10 秒以内
* Commit 创建：不含 Hook 时 5 秒以内
* 页面初次可交互：2 秒以内

对 5000 个状态文件要做到：

* 页面不一次渲染所有完整 Diff
* 文件列表支持过滤
* 文件列表支持分页或虚拟化
* Diff 按需加载
* 状态统计仍然准确

---

# 六十一、验收标准

## 仓库状态

* 能显示当前仓库。
* 能显示当前分支。
* 能显示 HEAD。
* 能区分已暂存、未暂存、未跟踪和冲突文件。
* 能识别部分暂存文件。
* 能正确处理中文和空格路径。
* 页面不会操作仓库外文件。

## Diff

* 能查看暂存 Diff。
* 能查看未暂存 Diff。
* 能预览未跟踪文本文件。
* 二进制文件不返回原始内容。
* 大 Diff 会截断。
* 风险内容经过遮盖。
* Diff 按需加载。

## 暂存

* 能暂存单个文件。
* 能批量暂存。
* 能取消暂存。
* 不使用 `git add .`。
* 不使用 `shell=True`。
* 所有路径前使用 `--`。
* Revision 变化会拒绝操作。
* 不会删除工作区文件。

## 安全扫描

* 能扫描暂存内容。
* 能展示风险等级。
* 不返回完整敏感值。
* High 和 Critical 可以阻止远程 AI。
* Scan 必须与当前 Revision 匹配。

## AI Commit Message

* 能调用现有 CommitService。
* 能展示多个候选。
* 能显示置信度和拆分建议。
* 能处理包装 JSON。
* 能处理 Thinking 模型空 Content。
* AI 错误不会显示 Traceback。
* 风险阻断时不会调用远程 AI。

## Commit

* 用户可以编辑 Message。
* 提交前必须确认。
* 能执行本地 `git commit`。
* 不执行 Push。
* 能处理 Git Hook。
* Commit 后保存 CommitRecord。
* Commit 后刷新仓库状态。
* 临时 Message 文件会删除。
* 不允许空 Commit。

## 安全

* 所有写 API 需要 Session。
* 所有写 API 需要 CSRF。
* 只允许固定仓库。
* 禁止任意命令。
* 禁止任意工作目录。
* 禁止路径逃逸。
* 日志不包含 Secret。
* 浏览器不接收完整 Secret。
* 并发写操作受到锁保护。

---

# 六十二、推荐开发顺序

严格按照以下顺序开发：

```text
1. 检查现有 GitService、CommitService 和 SecurityService
2. 运行现有完整测试
3. 定义仓库状态 Web Schema
4. 实现 porcelain v2 -z 状态解析
5. 编写仓库状态测试
6. 实现 RepositoryPathValidator
7. 编写路径安全测试
8. 实现仓库 Revision
9. 实现仓库状态 API
10. 实现 Diff Service
11. 实现 Diff 限制和二进制识别
12. 编写 Diff 测试
13. 实现暂存 Service
14. 实现暂存 API
15. 编写暂存测试
16. 实现取消暂存 Service
17. 实现取消暂存 API
18. 编写取消暂存测试
19. 实现仓库写操作锁
20. 实现安全扫描 API
21. 编写安全扫描测试
22. 实现 Scan 与 Revision 绑定
23. 实现 AI Commit 生成 API
24. 完善 AI 包装 JSON 解析
25. 完善 Thinking 模型错误处理
26. 编写 AI 生成测试
27. 实现 Commit Message 编辑和校验
28. 实现 Commit 确认 API
29. 实现临时 Message 文件
30. 实现 Git Hook 结果处理
31. 实现 CommitRecord 保存
32. 编写 Commit 测试
33. 创建 Git 工作台页面
34. 创建文件状态列表
35. 创建 Diff Viewer
36. 创建暂存和取消暂存交互
37. 创建安全扫描结果面板
38. 创建 AI Commit 助手
39. 创建最终提交确认框
40. 添加加载、错误和空状态
41. 编写页面 E2E 测试
42. 执行全部测试
43. 执行 Ruff
44. 执行 Mypy
45. 检查所有 Git 命令
46. 检查日志脱敏
47. 更新 README
48. 更新 Web 文档
49. 输出阶段总结
```

不要先完成页面，再补路径校验和安全控制。

必须先完成：

```text
状态解析
路径安全
Revision
Service
API
测试
```

最后才完成页面交互。

---

# 六十三、文档要求

新增：

```text
docs/web-repository.md
docs/web-commit-assistant.md
docs/web-git-security.md
```

`web-repository.md` 至少包括：

* 如何打开 Git 工作台
* 文件状态分类
* 部分暂存说明
* Diff 查看
* 暂存文件
* 取消暂存
* 仓库 Revision
* 冲突状态
* 当前不支持的 Git 操作

`web-commit-assistant.md` 至少包括：

* 安全扫描
* AI Message 生成
* 多候选 Message
* 用户编辑
* 拆分建议
* 最终确认
* 创建 Commit
* CommitRecord
* 为什么不会自动 Push

`web-git-security.md` 至少包括：

* Git 命令白名单
* 禁止 Shell 拼接
* 路径校验
* 仓库范围限制
* Revision 冲突
* CSRF
* 操作锁
* Secret 遮盖
* High 风险阻断
* 临时 Message 文件安全
* Git Hook 处理
* 不支持的危险命令

README 增加：

```text
本地 Web Git 工作台支持查看修改、文件 Diff、暂存、取消暂存、安全扫描、AI Commit Message 和用户确认 Commit。

GitPulse Web 不会自动执行 Push。
```

---

# 六十四、本阶段完成后的汇报格式

完成后必须按照以下格式输出：

```text
## 本阶段完成内容

- 新增的 Git 工作台模块
- 新增的 API
- 新增的页面
- 新增的 Service
- 新增的安全控制

## 仓库状态

- 状态解析方式
- 支持的文件状态
- 部分暂存
- 冲突状态
- Revision 机制

## Diff

- 暂存 Diff
- 未暂存 Diff
- 未跟踪文件
- 二进制处理
- 大文件截断
- 敏感信息遮盖

## 暂存操作

- 单文件暂存
- 批量暂存
- 取消暂存
- 初始仓库兼容
- 路径校验
- 操作锁

## 安全扫描

- 风险级别
- Scan ID
- Revision 绑定
- High 和 Critical 阻断
- 脱敏展示

## AI Commit Message

- 调用的现有 Service
- 候选 Message
- 拆分建议
- 包装 JSON 兼容
- Thinking 模型处理
- 错误提示

## Git Commit

- Message 编辑
- 最终确认
- Commit 命令
- Git Hook
- CommitRecord
- Commit 后状态刷新
- 是否执行 Push

## 测试结果

- 仓库状态测试
- 路径安全测试
- Diff 测试
- 暂存测试
- 安全扫描测试
- AI 生成测试
- Commit 测试
- 页面 E2E
- 原有回归测试
- Ruff
- Mypy

## 安全验证

- 是否禁止 shell=True
- 是否使用参数数组
- 是否使用 --
- 是否阻止路径逃逸
- 是否校验 Revision
- 是否启用操作锁
- 是否要求 Session 和 CSRF
- 是否确认日志不包含 Secret
- 是否确认 Web 不执行 Push

## 已知限制

- 当前不支持 Push
- 当前不支持 Pull
- 当前不支持分支管理
- 当前不支持冲突解决
- 当前没有 Worklog 页面
- 当前没有周报页面
- 当前没有飞书发送页面

## 下一阶段建议

下一阶段为：

本地 Web Worklog、历史记录和工作成果管理页面。
```

---

# 六十五、立即开始

现在开始开发 GitPulse 本地 Web 控制台第二阶段。

首先执行：

```bash
git status
pytest
```

然后：

1. 检查现有 Git、Security 和 Commit Service。
2. 列出计划新增和修改的文件。
3. 实现仓库状态解析和 Revision。
4. 实现路径安全校验。
5. 实现 Diff。
6. 实现暂存与取消暂存。
7. 实现安全扫描。
8. 实现 AI Commit Message。
9. 实现用户确认 Commit。
10. 保存 CommitRecord。
11. 完成 Git 工作台页面。
12. 编写完整测试。
13. 执行全部测试、Ruff 和 Mypy。
14. 更新文档。
15. 输出阶段总结。

本阶段完成前，不要开发 Push、Pull、Reset、Clean、Rebase、Worklog 页面、周报页面或飞书发送页面。
