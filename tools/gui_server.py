#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui_server —— 学习笔记站的本地可视化后台
=========================================
用 Python 标准库 http.server 起一个本地网页，提供：
  - 笔记树浏览 / 新建 / 打开编辑 / 删除
  - 服务端 Markdown 渲染（复用 .venv 里的 markdown / pymdownx，和 mkdocs 同款引擎）
  - 一键构建 / 发布（git 提交+推送）/ 整站实时预览

启动：note.bat gui   （默认 http://127.0.0.1:8777）
"""
from __future__ import annotations

import json
import subprocess
import sys
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

import note  # 复用：ROOT, DOCS, slugify, frontmatter, _ensure_subject_index, _create_index

TOOLS = Path(__file__).resolve().parent
DASHBOARD = TOOLS / "dashboard.html"
ASSETS = note.DOCS / "assets"

PORT = 8777
SITE_PROC = None  # 整站预览（mkdocs serve）子进程


# --------------------------------------------------------------------------
# Markdown 渲染（服务端，和 mkdocs 同源，预览最保真）
# --------------------------------------------------------------------------
def _build_extensions() -> tuple[list[str], dict]:
    """探测可用的 markdown 扩展，逐个 import 校验，避免某个扩展缺失导致整体崩溃。"""
    import_tests = {
        "admonition": "markdown.extensions.admonition",
        "attr_list": "markdown.extensions.attr_list",
        "md_in_html": "markdown.extensions.md_in_html",
        "def_list": "markdown.extensions.def_list",
        "tables": "markdown.extensions.tables",
        "footnotes": "markdown.extensions.footnotes",
        "toc": "markdown.extensions.toc",
        "fenced_code": "markdown.extensions.fenced_code",
        "pymdownx.arithmatex": "pymdownx.arithmatex",
        "pymdownx.betterem": "pymdownx.betterem",
        "pymdownx.caret": "pymdownx.caret",
        "pymdownx.mark": "pymdownx.mark",
        "pymdownx.tilde": "pymdownx.tilde",
        "pymdownx.details": "pymdownx.details",
        "pymdownx.superfences": "pymdownx.superfences",
        "pymdownx.highlight": "pymdownx.highlight",
        "pymdownx.inlinehilite": "pymdownx.inlinehilite",
        "pymdownx.smartsymbols": "pymdownx.smartsymbols",
        "pymdownx.tasklist": "pymdownx.tasklist",
    }
    exts: list[str] = []
    for name, mod in import_tests.items():
        try:
            __import__(mod)
            exts.append(name)
        except Exception:
            pass
    cfg = {
        "pymdownx.arithmatex": {"generic": True},
    }
    return exts, cfg


EXTENSIONS, EXT_CONFIG = _build_extensions()


def render_markdown(text: str) -> str:
    import markdown as _md

    try:
        return _md.markdown(text, extensions=EXTENSIONS, extension_configs=EXT_CONFIG)
    except Exception:
        # 兜底：只保留最基础的能力
        return _md.markdown(text, extensions=["tables", "fenced_code"])


# --------------------------------------------------------------------------
# 文件系统辅助
# --------------------------------------------------------------------------
def safe_note_path(rel: str) -> Path | None:
    """把相对路径解析为 docs 内的绝对路径，阻止越权访问。"""
    if not rel:
        return None
    rel = rel.replace("\\", "/")
    if rel.startswith("docs/"):
        rel = rel[5:]
    target = (note.DOCS / rel).resolve()
    docs_root = note.DOCS.resolve()
    if target == docs_root or docs_root in target.parents:
        return target
    return None


def build_tree() -> dict:
    root = {"name": "docs", "path": "", "type": "dir", "children": []}

    def rec(folder: Path, node: dict) -> None:
        for p in sorted(folder.iterdir(), key=lambda x: (x.is_file(), x.name)):
            if p.name.startswith(".") or p.name in ("site", "assets"):
                continue
            if p.is_dir():
                child = {
                    "name": p.name,
                    "path": str(p.relative_to(note.DOCS)),
                    "type": "dir",
                    "children": [],
                }
                rec(p, child)
                node["children"].append(child)
            elif p.suffix == ".md":
                node["children"].append(
                    {
                        "name": p.stem,
                        "path": str(p.relative_to(note.DOCS)),
                        "type": "index" if p.name == "index.md" else "note",
                    }
                )

    rec(note.DOCS, root)
    return root


def create_note(subject: str, chapter: str, title: str, tags: list[str], status: str) -> str:
    """新建一篇笔记，返回相对路径（相对 ROOT）。"""
    subject = (subject or "").strip()
    chapter = (chapter or "").strip()
    title = (title or "").strip()
    if not subject or not title:
        raise ValueError("科目和标题都不能为空")

    parts = [subject]
    if chapter:
        parts.append(chapter)

    name = note.slugify(title)
    filename = name if name.endswith(".md") else name + ".md"
    folder = note.DOCS.joinpath(*parts)
    folder.mkdir(parents=True, exist_ok=True)

    note._ensure_subject_index(parts)
    if chapter:
        note._create_index(parts)

    target = folder / filename
    if target.exists():
        raise FileExistsError(f"已存在：{target.relative_to(note.ROOT)}")

    content = (
        note.frontmatter(title, tags or [], status)
        + f"\n# {title}\n\n"
        + "> 开始写吧……\n"
    )
    target.write_text(content, encoding="utf-8")
    # 返回相对于 docs/ 的路径（正斜杠），与笔记树、读写接口保持一致
    return str(target.relative_to(note.DOCS)).replace("\\", "/")


def upload_image(name: str, b64: str) -> dict:
    """保存上传的图片到 docs/assets/uploads，返回可引用的相对路径。"""
    import base64
    import re
    import uuid

    if not b64:
        return {"ok": False, "error": "未收到图片数据"}
    m = re.match(r"data:.*?;base64,(.*)", b64, re.S)
    raw = m.group(1) if m else b64
    try:
        data = base64.b64decode(raw)
    except Exception:
        return {"ok": False, "error": "图片数据无法解码"}

    up = ASSETS / "uploads"
    up.mkdir(parents=True, exist_ok=True)

    # 安全文件名：保留扩展名，加时间戳前缀避免重名与路径穿越
    stem = re.sub(r"[^\w一-龥-]", "", Path(name).stem)[:40] or "image"
    ext = Path(name).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"):
        ext = ".png"
    fname = f"{stem}-{uuid.uuid4().hex[:6]}{ext}"
    (up / fname).write_bytes(data)
    return {"ok": True, "url": f"assets/uploads/{fname}", "name": name}


# --------------------------------------------------------------------------
# 构建 / 发布 / 整站预览
# --------------------------------------------------------------------------
def run_build() -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build"],
        cwd=str(note.ROOT),
        capture_output=True,
        text=True,
    )
    ok = proc.returncode == 0
    log = (proc.stdout + proc.stderr).strip() or ("构建成功" if ok else "构建失败")
    return ok, log


def run_publish(message: str) -> tuple[bool, str]:
    message = message or "更新学习笔记"
    try:
        subprocess.run(["git", "add", "-A"], cwd=str(note.ROOT), check=True, capture_output=True)
        proc = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(note.ROOT),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            err = proc.stderr
            if "nothing to commit" in err or "no changes added" in err:
                return True, "没有需要提交的更改（内容未变化）"
            return False, err.strip() or "提交失败"
        subprocess.run(["git", "push"], cwd=str(note.ROOT), check=True, capture_output=True)
        return True, "已提交并推送，GitHub Actions 将在约 1 分钟后自动部署。"
    except subprocess.CalledProcessError as e:
        return False, (e.stderr or "git 出错").strip()


def site_preview_start() -> tuple[bool, str]:
    global SITE_PROC
    if SITE_PROC and SITE_PROC.poll() is None:
        return True, "http://127.0.0.1:8001/learn-notes/"
    SITE_PROC = subprocess.Popen(
        [sys.executable, "-m", "mkdocs", "serve", "--dev-addr", "127.0.0.1:8001"],
        cwd=str(note.ROOT),
    )
    return True, "http://127.0.0.1:8001/learn-notes/"


def site_preview_stop() -> None:
    global SITE_PROC
    if SITE_PROC:
        SITE_PROC.terminate()
        SITE_PROC = None


# --------------------------------------------------------------------------
# HTTP 处理
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 静默访问日志
        pass

    def _send_json(self, obj, code: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            if DASHBOARD.exists():
                return self._send_file(DASHBOARD, "text/html; charset=utf-8")
            self._send_json({"error": "dashboard.html 缺失"}, 500)
            return
        if path.startswith("/assets/"):
            rel = unquote(path[len("/assets/"):])
            target = (ASSETS / rel).resolve()
            if ASSETS.resolve() in target.parents and target.exists():
                ctype = {
                    ".js": "application/javascript",
                    ".css": "text/css",
                    ".woff2": "font/woff2",
                    ".woff": "font/woff",
                }.get(target.suffix, "application/octet-stream")
                return self._send_file(target, ctype)
            self.send_error(404)
            return
        if path == "/api/tree":
            return self._send_json(build_tree())
        if path == "/api/note":
            q = parse_qs(parsed.query)
            rel = q.get("path", [""])[0]
            target = safe_note_path(rel)
            if not target or not target.exists():
                return self._send_json({"error": "笔记不存在"}, 404)
            self._send_json({"path": rel, "content": target.read_text(encoding="utf-8")})
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        data = self._read_json()

        if path == "/api/new":
            try:
                rel = create_note(
                    data.get("subject", ""),
                    data.get("chapter", ""),
                    data.get("title", ""),
                    [t.strip() for t in (data.get("tags") or "").split(",") if t.strip()],
                    data.get("status", "published"),
                )
                return self._send_json({"ok": True, "path": rel})
            except (ValueError, FileExistsError) as e:
                return self._send_json({"ok": False, "error": str(e)}, 400)

        if path == "/api/note":
            rel = data.get("path", "")
            content = data.get("content", "")
            target = safe_note_path(rel)
            if not target:
                return self._send_json({"ok": False, "error": "非法路径"}, 400)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return self._send_json({"ok": True})

        if path == "/api/preview":
            html = render_markdown(data.get("md", ""))
            return self._send_json({"html": html})

        if path == "/api/upload":
            res = upload_image(data.get("name", "image.png"), data.get("data", ""))
            code = 200 if res.get("ok") else 400
            return self._send_json(res, code)

        if path == "/api/build":
            ok, log = run_build()
            return self._send_json({"ok": ok, "log": log})

        if path == "/api/publish":
            ok, log = run_publish(data.get("message", ""))
            return self._send_json({"ok": ok, "log": log})

        if path == "/api/site_preview":
            action = data.get("action", "start")
            if action == "stop":
                site_preview_stop()
                return self._send_json({"ok": True, "running": False})
            ok, url = site_preview_start()
            return self._send_json({"ok": ok, "running": True, "url": url})

        self.send_error(404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        rel = q.get("path", [""])[0]
        target = safe_note_path(rel)
        if not target or not target.exists():
            return self._send_json({"ok": False, "error": "笔记不存在"}, 404)
        target.unlink()
        # 若章节/科目变空，清掉空 index（保留目录结构由用户决定，这里只删笔记）
        self._send_json({"ok": True})


def run(port: int = PORT) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"▶ 学习笔记可视化后台已启动：{url}  （Ctrl+C 停止）")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        site_preview_stop()
        server.server_close()


if __name__ == "__main__":
    run(PORT)
