# 腾讯云抢购脚本 项目整理实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有腾讯云抢购脚本整理成一个带正式 README、致谢、免责声明和 MIT 许可证的可发布仓库，并推送到 `avelli` 的远程仓库。

**Architecture:** 保持当前单文件脚本 `snap_up.py` 不做功能重构，只补齐仓库级文档和发布文件。README 负责项目名称、用途、安装运行、参考来源、致谢与免责声明；`LICENSE` 提供 MIT 协议文本；`.gitignore` 只忽略脚本运行时生成的 Cookie 和 Token 文件，避免敏感数据被提交。

**Tech Stack:** Python 3.8+, Playwright, requests, Git, GitHub CLI 或 Git 远程推送。

---

### Task 1: 盘点现有脚本与参考项目

**Files:**
- Read: `snap_up.py`
- Read: `https://github.com/zhouyifan007/tencentyun-snake-up`

- [ ] **Step 1: 检查脚本当前能力和运行产物**

```bash
rtk sed -n "1,260p" snap_up.py
rtk sed -n "261,520p" snap_up.py
```

- [ ] **Step 2: 读取参考项目 README，确认致谢和参考说明写法**

```bash
rtk sh -lc 'tmp=$(mktemp -d); git clone --depth 1 https://github.com/zhouyifan007/tencentyun-snake-up.git "$tmp/ref" >/dev/null 2>&1; sed -n "1,220p" "$tmp/ref/README.md"'
```

- [ ] **Step 3: 确认脚本会生成的本地文件清单**

```bash
rtk sh -lc 'printf "%s\n" cookies.json csrf_token.txt __pycache__/'
```

### Task 2: 编写 README

**Files:**
- Create: `README.md`

- [ ] **Step 1: 写入项目说明、安装、使用、致谢、免责声明**

```markdown
# 腾讯云抢购脚本

基于 Playwright 的腾讯云活动抢购辅助脚本。

## 特性

- 扫码登录并自动保存 Cookie
- 抓取实时 `x-csrf-token`
- 按时等待并循环发起抢购
- 支持多个地域并发尝试

## 环境要求

- Python 3.8+
- Playwright
- requests

## 安装

```bash
pip install playwright requests
playwright install chromium
```

## 使用

```bash
python snap_up.py
```

## 项目结构

- `snap_up.py`：主程序
- `cookies.json`：登录态缓存
- `csrf_token.txt`：Token 缓存

## 致谢

感谢 [zhouyifan007/tencentyun-snake-up](https://github.com/zhouyifan007/tencentyun-snake-up) 提供的思路和参考。

## 免责声明

本项目仅供学习、研究与个人自动化实验使用，不保证可用性、时效性或抢购结果。使用者需自行确保行为符合所在地法律法规、平台规则与活动规则；由使用本项目引起的任何账号风险、财产损失、封禁、纠纷或其他后果，均由使用者自行承担。

## 协议

本项目采用 MIT License。
```

- [ ] **Step 2: 校对 README 的项目名、链接和免责声明措辞**

```bash
rtk sed -n '1,240p' README.md
```

### Task 3: 添加许可证和忽略规则

**Files:**
- Create: `LICENSE`
- Create: `.gitignore`

- [ ] **Step 1: 写入 MIT 许可证**

```text
MIT License

Copyright (c) 2026 avelli

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

- [ ] **Step 2: 忽略运行时敏感文件**

```gitignore
cookies.json
csrf_token.txt
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 3: 检查忽略规则是否覆盖脚本运行产物**

```bash
rtk git status --short --ignored
```

### Task 4: 初始化 Git 并准备推送

**Files:**
- Create: `.git/` (Git 元数据)

- [ ] **Step 1: 初始化仓库并设置本地提交身份**

```bash
rtk git init
rtk git config user.name "avelli"
rtk git config user.email "avelli@users.noreply.github.com"
```

- [ ] **Step 2: 确认远端 `avelli` 的目标地址可用**

```bash
rtk gh auth status || true
rtk git remote -v
```

- [ ] **Step 3: 绑定远端并检查分支名**

```bash
rtk git branch -M main
rtk git remote add avelli git@github.com:avelli/tencentyun-qianggou.git
```

### Task 5: 验证、提交并推送

**Files:**
- Modify: tracked files only

- [ ] **Step 1: 做最终校验**

```bash
rtk python -m py_compile snap_up.py
rtk git diff --check
rtk git status --short
```

- [ ] **Step 2: 提交到本地 Git 历史**

```bash
rtk git add README.md LICENSE .gitignore snap_up.py
rtk git commit -m "docs: add project README and license"
```

- [ ] **Step 3: 推送到 `avelli` 远端**

```bash
rtk git push -u avelli main
```

- [ ] **Step 4: 复核远端结果**

```bash
rtk git ls-remote --heads avelli main
```
