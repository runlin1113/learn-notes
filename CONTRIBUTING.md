# 贡献指南（Contributing Guide）

感谢你有兴趣参与共建这份学习笔记 🎉 这正是本站存在的意义之一：**知识在开放中生长**。

无论是纠错别字、补充推导、完善示例、提出建议，都欢迎。

## 快速参与：给作者提建议（最简单）

- 在任意笔记页面右下角点「编辑此页」的铅笔图标；
- 或在 [Issues](https://github.com/runlin1113/learn-notes/issues) 提出你的想法 / 勘误；
- 也可直接 `Fork` 本仓库后提交 Pull Request。

## 想直接贡献一篇笔记？

### 方式一：网页端（适合小改动，如改错字）

1. 打开你想修改的笔记页，点击右上角 ✏️「编辑此页」；
2. 在 GitHub 网页编辑器中改完，点击 **Commit changes**；
3. 选择 **Create a new branch and start a pull request**，填上说明后创建 PR。

### 方式二：克隆到本地（适合新增/批量修改）

```bash
# 1. Fork 后克隆你自己的仓库
git clone https://github.com/<你的用户名>/learn-notes.git
cd learn-notes

# 2. 安装依赖
pip install -r requirements.txt

# 3. 新建一篇笔记（会自动套用模板与 frontmatter）
python tools/note.py new "数学/线性代数" 矩阵初探

# 4. 用任意编辑器修改 docs 下的 .md 文件
# 5. 本地预览检查效果
python tools/note.py serve

# 6. 提交并推送
git add .
git commit -m "新增：线性代数·矩阵初探"
git push
```

然后在 GitHub 上从你的分支向 `main` 发起 Pull Request。

## 写作规范

一篇笔记是一个 `.md` 文件，顶部带 YAML frontmatter：

```yaml
---
title: 矩阵初探
date: 2026-09-05
tags: [线性代数, 笔记]
status: published   # 草稿写作时可填 draft，未发布不会对外（后续可按需过滤）
---
```

建议：

- 文件名用「科目/主题.md」，一个主题一个小节标题（`##`），方便目录跳转；
- 代码块注明语言以启用高亮，数学公式用 `$...$`（行内）或 `$$...$$`（独立行）；
- 引用他人内容务必注明出处；
- 尽量用中文写作，术语首次出现可附英文。

## PR 检查清单

- [ ] 内容真实，无占位/虚构
- [ ] 标题、frontmatter 完整
- [ ] 本地 `note serve` 预览无报错
- [ ] 若新增科目，已同步更新 `mkdocs.yml` 的 `nav` 与 `docs/科目/index.md`

## 许可

你对本站的贡献，将默认遵循本站的许可协议发布：
文字内容 CC BY-NC 4.0，代码 MIT。详见 [LICENSE](LICENSE)。

如对贡献方式有疑问，欢迎开 [Issue](https://github.com/runlin1113/learn-notes/issues) 交流。
