# 凌润林的学习笔记

> **记录学习 · 传播知识 · 开源协作**
> 一个由 MkDocs Material 驱动的静态学习笔记站：你只负责写 Markdown，剩下的排版、搜索、部署全自动。

## 这个项目的三个目标

1. **记录学习** —— 以 Markdown 形式沉淀自己的学习过程，按科目组织，方便回顾与检索；
2. **传播知识** —— 发布为免费、开放的静态网页，任何人都能阅读、搜索；
3. **传播开源合作精神** —— 仓库公开在 GitHub，欢迎他人 fork、提 Issue、改错别字、共建知识。

## 目录结构

```
learn-notes/
├── mkdocs.yml              # 站点配置（主题/插件）
├── requirements.txt        # Python 依赖
├── docs/                   # 你的全部笔记都在这里（目录即导航）
│   ├── index.md            # 首页
│   ├── 使用指南/           # 本站使用方法（可删除）
│   ├── 数学/               # 科目（示例）：文件夹 = 科目
│   │   ├── index.md        # 科目的「入口页」
│   │   ├── 微积分/
│   │   └── 线性代数/
│   ├── 人工智能/           # 科目（示例）
│   └── ...                 # 想加科目就新建一个文件夹
├── tools/
│   ├── note.py             # note 命令行工具（建笔记/预览/发布/gui）
│   ├── gui_server.py       # 可视化后台的本地服务（标准库实现）
│   └── dashboard.html      # 可视化后台的网页界面
├── .venv/                  # 项目自带 Python 虚拟环境（已装好依赖，无需 pip install）
├── note.bat                # Windows 快捷入口
├── note                    # macOS / Linux 快捷入口
└── .github/workflows/
    └── deploy.yml          # push 后自动部署到 GitHub Pages
```

> 导航规则：`docs/` 下的每个文件夹是一个「科目」，每个 `.md` 文件是一篇笔记。
> 新增一篇笔记 = 在对应科目文件夹里放一个 `.md` 文件，无需修改任何配置。

## 方式一：可视化后台（推荐，不用敲命令）

双击 `note.bat`，选择「gui」，或直接运行：

```bash
note.bat gui
```

会自动打开浏览器 `http://127.0.0.1:8777`，提供网页界面：

- 左侧**笔记树**，点一下即可打开任意笔记；
- 中间**编辑器 + 实时预览**（改完即刷新，公式/代码/表格都即时渲染）；
- **新建笔记**：填科目 / 章节 / 标题 / 标签即可；
- **保存**（Ctrl+S）、**构建**、**发布**（提交并推送到 GitHub）、**整站预览**；
- **插入图片**：点按钮选择，或直接把图片拖拽到编辑区。

> 后台是一个纯标准库写的本地服务，零额外依赖；依赖已随项目打包在 `.venv/` 里。

## 方式二：命令行（可选）

```bash
# 1. 安装依赖（只需一次，note.bat gui 已自带 .venv，可跳过）
pip install -r requirements.txt

# 2. 本地实时预览 → 打开 http://127.0.0.1:8000
note serve
```

### 日常用法（你只需要记住 3 条命令）

```bash
note new "人工智能/机器学习" 线性回归入门    # 新建一篇笔记
note serve                                  # 本地预览（改完自动刷新）
note publish "更新说明"                     # 一键发布上线
```

也可以用 `note stat` 查看各科目笔记数量统计。

## 如何发布到线上（GitHub Pages）

1. 在 GitHub 新建**公开仓库** `learn-notes`，把本目录推上去；
2. 仓库 **Settings → Pages → Source 选择「GitHub Actions」**；
3. 以后每次 `note publish`（即 push 到 main），都会自动构建并更新站点；
4. 访问 `https://<你的用户名>.github.io/learn-notes/`。

> 详细的分步截图指引见站内「[使用指南/发布流程](docs/00-使用指南/发布流程.md)」。

## 如何贡献（开源协作）

你的纠错、补充、翻译都是宝贵的贡献。请看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可

- 笔记文字：**CC BY-NC 4.0**（署名-非商业）
- 工具代码：**MIT License**

详情见 [LICENSE](LICENSE)。
