#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
note —— 学习笔记站的一键工具
================================
用法（在项目根目录运行）：

  note new <科目/章节> <笔记名> [--topic] [--tags 标签1,标签2]
      新建一篇笔记。默认是普通笔记；加 --topic 则创建该章节的 index.md 入口页。

  note serve [--port 8000]
      本地实时预览，浏览器打开 http://127.0.0.1:8000

  note build
      只构建站点（用于检查有没有写错）。

  note publish "更新说明"
      构建 + git 提交 + 推送，触发 GitHub Actions 自动部署。

  note stat
      统计各科目的笔记数量。

需要先安装依赖（只需一次）：pip install -r requirements.txt
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

INVALID_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')
SLUG_SPACES = re.compile(r"\s+")


def slugify(name: str) -> str:
    """把笔记名转成安全的文件名（保留中文，去掉非法字符）。"""
    name = INVALID_CHARS.sub("-", name.strip())
    name = SLUG_SPACES.sub("-", name)
    return name.strip("-") or "untitled"


def frontmatter(title: str, tags: list[str], status: str = "published") -> str:
    today = date.today().isoformat()
    tag_str = "[" + ", ".join(tags) + "]" if tags else "[]"
    return (
        "---\n"
        f"title: {title}\n"
        f"date: {today}\n"
        f"tags: {tag_str}\n"
        f"status: {status}\n"
        "---\n"
    )


def cmd_new(args: argparse.Namespace) -> int:
    if not args.path:
        print("✗ 请指定路径，例如：note new 数学/微积分 极限与连续")
        return 1

    parts = [p for p in args.path.split("/") if p]

    # 解析：name 缺省时，默认把路径的最后一段当作笔记名
    if not args.topic:
        if not args.name and len(parts) < 2:
            print("✗ 请同时给出「科目/章节」和「笔记名」，例如：note new 数学/微积分 极限与连续")
            print("  如果是要新建一个科目的入口页，请加 --topic：note new 数学 --topic")
            return 1

        if args.name:
            folder_parts, raw_name = parts, args.name
        else:
            folder_parts, raw_name = parts[:-1], parts[-1]

        name = slugify(raw_name)
        title = raw_name.strip()
        filename = name if name.endswith(".md") else name + ".md"

        # 解析标签：逗号分隔 → 列表（中文标签不能按字符拆）
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

        folder = DOCS.joinpath(*folder_parts) if folder_parts else DOCS
        target = folder / filename
        if target.exists():
            print(f"✗ 已存在：{target.relative_to(ROOT)}")
            return 1
        folder.mkdir(parents=True, exist_ok=True)

        # 若顶级「科目」是全新的，顺手补建一个 index 入口页
        _ensure_subject_index(folder_parts)

        content = (
            frontmatter(title, tags, args.status)
            + f"\n# {title}\n\n"
            + "> ✍️ 开始写吧……\n"
        )
        target.write_text(content, encoding="utf-8")
        rel = target.relative_to(ROOT)
        print(f"✓ 已创建笔记：{rel}")
        print(f"  标题：{title}")
        print("  打开它开始写作，然后运行 note serve 预览、note publish 发布。")
        return 0

    # --topic：新建某科目/章节的 index.md 入口页
    folder = DOCS.joinpath(*parts)
    target = folder / "index.md"
    if target.exists():
        print(f"✗ 已存在：{target.relative_to(ROOT)}")
        return 1
    folder.mkdir(parents=True, exist_ok=True)
    _ensure_subject_index(parts[:-1])
    _create_index(parts)
    print(f"✓ 已创建章节入口页：docs/{'/'.join(parts)}/index.md")
    return 0


def _ensure_subject_index(folder_parts: list[str]) -> None:
    """当顶级「科目」目录存在但没有 index.md 时，自动补一个入口页。"""
    if not folder_parts:
        return
    subject_index = DOCS.joinpath(folder_parts[0], "index.md")
    if not subject_index.exists():
        _create_index([folder_parts[0]])


def _create_index(parts: list[str]) -> None:
    """为某个科目/章节生成 index.md 入口页。"""
    folder = DOCS.joinpath(*parts)
    target = folder / "index.md"
    if target.exists():
        return
    folder.mkdir(parents=True, exist_ok=True)
    title = parts[-1] if parts else "首页"
    content = (
        frontmatter(title, [])
        + f"\n# {title}\n\n"
        + f"> 这里是 **{title}** 的入口页。\n\n"
        + "- 新笔记请放在本文件夹下（一个 .md 文件 = 一篇笔记）。\n"
    )
    target.write_text(content, encoding="utf-8")
    print(f"  ✓ 自动补建入口页：docs/{'/'.join(parts)}/index.md")


def _run_mkdocs(*argv: str) -> int:
    """在项目根目录运行 mkdocs 命令。"""
    python = sys.executable
    proc = subprocess.run([python, "-m", "mkdocs", *argv], cwd=str(ROOT))
    return proc.returncode


def cmd_serve(args: argparse.Namespace) -> int:
    print("▶ 启动本地预览：http://127.0.0.1:%d  （Ctrl+C 停止）" % args.port)
    return _run_mkdocs("serve", "--dev-addr", f"127.0.0.1:{args.port}")


def cmd_build(args: argparse.Namespace) -> int:
    argv = ["build", "--strict"] if args.strict else ["build"]
    return _run_mkdocs(*argv)


def cmd_publish(args: argparse.Namespace) -> int:
    # 1. 先构建校验
    print("▶ 第 1 步 / 4：构建校验……")
    if _run_mkdocs("build") != 0:
        print("✗ 构建失败，请先修复后重试。可运行 note serve 本地排查。")
        return 1

    # 2. git 提交
    message = args.message or "更新学习笔记"
    try:
        subprocess.run(["git", "add", "-A"], cwd=str(ROOT), check=True)
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
        )
        print(f"✓ 第 2 步 / 4：已提交（{message}）")
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode("utf-8", "ignore")
        if "nothing to commit" in err or "no changes added" in err:
            print("· 没有需要提交的更改（内容未变化）")
        else:
            print(f"✗ git 提交失败：{err}")
            print("  提示：第一次使用请先 git init 并关联远程仓库，见使用指南/发布流程。")
            return 1

    # 3. push
    print("▶ 第 3 步 / 4：推送到 GitHub……")
    try:
        subprocess.run(["git", "push"], cwd=str(ROOT), check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode("utf-8", "ignore")
        print(f"✗ git push 失败：{err}")
        print("  提示：请确认已设置远程仓库 origin 并配置了 GitHub 登录。")
        return 1

    # 4. 完成
    print("✓ 第 4 步 / 4：推送成功！")
    print("  稍等约 1 分钟，GitHub Actions 会自动部署更新。")
    return 0


def cmd_stat(args: argparse.Namespace) -> int:
    if not DOCS.exists():
        print("还没有任何笔记。先运行 note new 创建一篇吧。")
        return 0
    from collections import Counter

    counts: Counter[str] = Counter()
    total = 0
    for md in DOCS.rglob("*.md"):
        if md.name == "index.md":
            continue
        rel = md.relative_to(DOCS)
        subject = rel.parts[0] if len(rel.parts) > 1 else "(根目录)"
        counts[subject] += 1
        total += 1

    if not counts:
        print("还没有普通笔记（只有科目入口页）。")
        return 0

    width = max(len(k) for k in counts) + 2
    for subject, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        bar = "█" * min(n, 30)
        print(f"{subject:<{width}} {n:>3} 篇  {bar}")
    print("-" * (width + 12))
    print(f"{'合计':<{width}} {total:>3} 篇")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    import gui_server

    gui_server.run(args.port)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="note",
        description="学习笔记站一键工具：建笔记 / 预览 / 发布",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    p_new = sub.add_parser("new", help="新建一篇笔记或章节入口页")
    p_new.add_argument("path", help="科目/章节路径，如 数学/微积分")
    p_new.add_argument("name", nargs="?", help="笔记名（新建普通笔记时填写）")
    p_new.add_argument("--topic", action="store_true", help="创建章节入口页 index.md")
    p_new.add_argument("--tags", default="", help="逗号分隔的标签，如 数学,微积分")
    p_new.add_argument(
        "--status", default="published", choices=["published", "draft"], help="笔记状态"
    )
    p_new.set_defaults(func=cmd_new)

    p_serve = sub.add_parser("serve", help="本地实时预览")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    p_build = sub.add_parser("build", help="仅构建站点（检查错误）")
    p_build.add_argument("--strict", action="store_true", help="严格模式：把警告当作错误")
    p_build.set_defaults(func=cmd_build)

    p_pub = sub.add_parser("publish", help="构建 + 提交 + 推送，触发自动部署")
    p_pub.add_argument("message", nargs="?", help="提交说明，如「新增 极限与连续」")
    p_pub.set_defaults(func=cmd_publish)

    p_stat = sub.add_parser("stat", help="统计各科目笔记数量")
    p_stat.set_defaults(func=cmd_stat)

    p_gui = sub.add_parser("gui", help="打开本地可视化后台（网页界面）")
    p_gui.add_argument("--port", type=int, default=8777, help="后台端口（默认 8777）")
    p_gui.set_defaults(func=cmd_gui)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
