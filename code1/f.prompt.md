# GitPulse Web 控制台第六阶段：集成验收与正式发布

继续开发现有 GitPulse 项目。

当前已经完成：

* Web 系统配置中心
* Git 工作台与 Commit 助手
* Worklog 与工作历史
* 周报管理中心
* 飞书通知中心
* Webhook 与应用机器人模式

本阶段不再新增大型业务功能，重点完成：

```text
统一仪表盘
全流程集成
性能优化
安全回归
安装打包
发布验收
```

## 一、目标

用户能够通过一次全局安装，在任意 Git 仓库中运行：

```bash
gitpulse web
```

并完成：

```text
配置系统
→ 查看 Git 状态
→ 暂存文件
→ 安全扫描
→ 生成 Commit Message
→ 创建 Commit
→ 添加 Worklog
→ 生成周报
→ 编辑并确认
→ 发送飞书
```

## 二、仪表盘

完善首页：

```text
/
```

展示：

* 当前仓库
* 当前分支
* 工作区状态
* 已暂存和未暂存文件数
* 本周 Commit 数
* 本周 Worklog 数
* 当前周报状态
* 最近一次飞书发送状态
* AI 配置状态
* 数据库状态
* 系统警告

提供快捷入口：

```text
打开 Git 工作台
添加 Worklog
生成本周周报
查看通知记录
打开系统配置
```

仪表盘只展示统计，不允许自动执行 Git 写操作。

## 三、统一导航与界面

导航统一为：

```text
仪表盘
Git 工作台
Worklog
工作历史
周报
飞书通知
系统配置
```

统一处理：

* 页面布局
* 按钮样式
* 表单样式
* 加载状态
* 空状态
* 错误提示
* 确认对话框
* 分页
* 时间和时区显示
* 移动端基础布局

不得依赖公共 CDN。

## 四、全流程端到端测试

实现完整 E2E 场景：

```text
创建临时 Git 仓库
→ 修改文件
→ Web 暂存
→ 安全扫描
→ Mock AI 生成 Message
→ 创建 Commit
→ 新增 Worklog
→ 生成周报
→ 编辑周报
→ 确认周报
→ Mock 飞书发送
→ 验证数据库记录
```

同时覆盖：

* 敏感信息阻断
* AI 超时
* AI 非法 JSON
* Git Hook 失败
* 周报无数据
* 飞书发送失败
* 重复发送阻断
* 仓库 Revision 冲突
* 配置文件并发修改
* Session 过期
* CSRF 失败

所有外部服务必须 Mock。

## 五、性能优化

重点检查：

* 大仓库状态读取
* 大量未跟踪文件
* 大 Diff
* 5000 条历史记录
* 200 条周报数据
* 长时间 AI 请求
* 多页面重复数据库查询

建议目标：

```text
仪表盘加载：2 秒以内
仓库状态：2 秒以内
普通 Diff：1 秒以内
历史查询：1 秒以内
周报数据预览：3 秒以内
```

要求：

* Diff 按需加载
* 历史记录分页
* 数据库字段建立必要索引
* 避免页面加载时调用 AI
* 避免重复读取完整 Git Log
* 外部请求设置超时
* 写操作使用仓库级锁

## 六、安全回归

重新检查：

* Web 只监听 `127.0.0.1`
* Host 校验
* Origin 校验
* Session
* CSRF
* 路径逃逸
* 符号链接逃逸
* Git 参数注入
* SQL 注入
* HTML 注入
* Secret 脱敏
* 日志脱敏
* 配置文件权限
* 临时文件权限
* Webhook Host 校验
* 任意 URL 请求
* 任意 Shell 命令

禁止使用：

```python
shell=True
```

禁止开放：

```text
任意命令输入框
任意工作目录
任意请求地址
```

## 七、错误处理

所有 Web API 使用统一错误结构：

```json
{
  "error": {
    "code": "repository_changed",
    "message": "仓库状态已变化，请刷新后重试。",
    "details": []
  }
}
```

页面不得直接显示 Python Traceback。

Debug 日志仍然必须脱敏。

增加统一错误页面：

```text
403
404
409
500
```

## 八、健康检查

实现：

```http
GET /api/health
GET /api/health/details
```

基础健康检查返回：

* GitPulse 版本
* Web 服务状态
* 数据库状态

详细检查需要 Session，返回：

* 当前仓库
* Git 状态
* 配置状态
* AI 配置状态
* 飞书配置状态
* 数据库 Schema 版本
* 可写目录状态

不得返回 Secret。

## 九、诊断命令

完善：

```bash
gitpulse doctor
```

至少检查：

* Python 版本
* Git 版本
* 当前仓库
* Git 用户身份
* 用户级配置
* 项目级配置
* Secret 文件权限
* 数据库
* AI 配置
* 飞书配置
* Web 端口
* 报告目录
* 配置 Schema 版本

同时支持：

```bash
gitpulse doctor --json
```

## 十、全局安装

项目必须支持通过 `pipx` 全局安装。

开发模式：

```bash
pipx install --editable .
```

正式安装：

```bash
pipx install gitpulse
```

检查 `pyproject.toml`：

```toml
[project.scripts]
gitpulse = "gitpulse.cli:main"
```

安装后应能在任意仓库中运行：

```bash
cd ~/projects/example
gitpulse doctor
gitpulse commit
gitpulse weekly
gitpulse web
```

GitPulse 必须根据当前目录自动识别仓库：

```bash
git rev-parse --show-toplevel
```

不能依赖 GitPulse 源码目录。

## 十一、打包

构建：

```bash
python -m build
```

生成：

```text
dist/*.whl
dist/*.tar.gz
```

确保以下资源被打包：

* Jinja2 Templates
* CSS
* JavaScript
* 默认配置
* Prompt 模板
* 数据库迁移
* 周报模板

不得依赖源码目录中的相对路径。

资源读取优先使用：

```python
importlib.resources
```

## 十二、版本与迁移

设置正式版本，例如：

```text
0.1.0
```

支持：

```bash
gitpulse --version
```

数据库必须具有 Schema Version。

升级时：

* 自动检测旧版本
* 备份数据库
* 执行迁移
* 迁移失败回滚
* 不静默删除数据

## 十三、发布检查

增加：

```bash
gitpulse release-check
```

检查：

* 测试是否通过
* Ruff 是否通过
* Mypy 是否通过
* 构建是否成功
* Wheel 是否可安装
* CLI 是否可运行
* Web 静态资源是否存在
* 包内是否存在 Secret
* README 是否完整
* 版本号是否一致
* 数据库迁移是否完整

命令只检查，不执行：

```text
git commit
git tag
git push
上传 PyPI
```

## 十四、CI

增加基础 CI：

```text
安装依赖
运行 Pytest
运行 Ruff
运行 Mypy
构建 Wheel
安装 Wheel
执行 gitpulse --version
执行 gitpulse --help
```

至少覆盖项目当前支持的 Python 版本。

## 十五、测试

必须执行：

```bash
pytest
ruff check .
mypy src
python -m build
```

再使用全新临时环境验证：

```bash
pipx install dist/*.whl
gitpulse --version
gitpulse --help
gitpulse doctor
```

测试中不得使用用户真实 HOME、数据库、仓库或凭证。

## 十六、文档

更新：

```text
README.md
docs/installation.md
docs/web-console.md
docs/configuration.md
docs/git-workbench.md
docs/worklogs.md
docs/weekly.md
docs/feishu.md
docs/security.md
docs/troubleshooting.md
```

README 至少包含：

```bash
pipx install gitpulse
cd your-project
gitpulse init
gitpulse web
```

说明：

* 默认只监听本机
* 不会自动 Push
* High 和 Critical 风险会阻止远程 AI
* Git 操作需要用户确认
* Webhook 和 App 机器人配置方式不同

## 十七、验收标准

完成后必须满足：

1. `pipx install` 后全局可用。
2. 任意 Git 仓库中可以运行。
3. `gitpulse web` 可以打开完整控制台。
4. 完整 Commit 流程可用。
5. Worklog 流程可用。
6. 周报流程可用。
7. 飞书发送流程可用。
8. 仪表盘数据正确。
9. 所有写操作有确认和安全校验。
10. 外部服务测试全部使用 Mock。
11. Wheel 包含所有 Web 资源。
12. Pytest、Ruff、Mypy 和 Build 全部通过。
13. 不泄露 Secret。
14. 不执行自动 Push。
15. 不包含危险 Git 操作。

## 十八、开发顺序

```text
1. 完善统一仪表盘
2. 统一导航和页面组件
3. 完成完整 E2E 流程
4. 修复跨模块集成问题
5. 优化 Git 和数据库性能
6. 完成安全回归
7. 完善 doctor 和 health API
8. 完成 pipx 全局安装支持
9. 完成 Wheel 和资源打包
10. 完成数据库迁移验证
11. 增加 release-check
12. 增加 CI
13. 执行全部测试
14. 在全新环境安装 Wheel 验证
15. 完善全部文档
```

本阶段不要新增 Push、Pull、Reset、Rebase、云端账号系统或远程 Web 部署。

完成后输出：

```text
完成内容
仪表盘功能
完整流程验证
性能测试结果
安全检查结果
安装方式
构建产物
CI 结果
测试结果
已知限制
发布建议
```

本阶段完成后，GitPulse Web 控制台达到 MVP 正式发布标准。
