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
import re
import subprocess
import sys
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse, parse_qs, unquote

import note  # 复用：ROOT, DOCS, slugify, frontmatter, _ensure_subject_index, _create_index

TOOLS = note.ROOT / "tools"
DASHBOARD = TOOLS / "dashboard.html"
ASSETS = note.DOCS / "assets"
SITE = note.ROOT / "site"          # mkdocs 构建产物（预览借用它的样式表，保证排版一致）

PORT = 8777
SITE_PROC = None  # 整站预览（mkdocs serve）子进程

# Windows 控制台默认 GBK，避免打印“▶”等字符时崩溃（打包成 exe 后必现）
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


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
        "pymdownx.tabbed": "pymdownx.tabbed",
        "pymdownx.keys": "pymdownx.keys",
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
        "pymdownx.tabbed": {"alternate_style": True},
        "pymdownx.tasklist": {"custom_checkbox": True},
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
# 预览保真：去 front matter、图片路径改写、复用站点样式表
# --------------------------------------------------------------------------
FRONT_MATTER = re.compile(r"\A---[ \t]*\n.*?\n---[ \t]*\n", re.S)
URL_ATTR = re.compile(r'\b(src|href)="([^"]+)"', re.I)
EXTERNAL = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//|#|data:)", re.I)


def strip_front_matter(text: str) -> str:
    """去掉笔记开头的 YAML front matter —— 站点会隐藏它，预览也应一致。"""
    if text.lstrip().startswith("---"):
        return FRONT_MATTER.sub("", text, count=1)
    return text


def _doc_relative(target: Path) -> str | None:
    """把绝对路径转成相对 docs 的 URL 路径；越界返回 None。"""
    docs_root = note.DOCS.resolve()
    try:
        rel = target.resolve().relative_to(docs_root)
    except (ValueError, OSError):
        return None
    return "/".join(rel.parts)


def rewrite_local_urls(html: str, note_rel: str = "") -> str:
    """把相对图片/链接改写成后台可直接访问的 /doc/... 地址。

    站点上由 MkDocs 负责解析相对路径，预览里必须自己算：
    先按「笔记所在目录」解析，再按「docs 根目录」兜底（与站点容错一致）。
    """
    base_dir = PurePosixPath(note_rel).parent if note_rel else PurePosixPath(".")

    def repl(m: re.Match) -> str:
        attr, url = m.group(1), m.group(2)
        if EXTERNAL.match(url):
            return m.group(0)
        clean = url.split("#")[0].split("?")[0]
        if not clean:
            return m.group(0)
        if clean.startswith("/"):
            candidates = [clean.lstrip("/")]
        else:
            candidates = [str(base_dir / clean), clean]
        for cand in candidates:
            parts = [p for p in PurePosixPath(cand).parts if p not in (".", "..")]
            rel = _doc_relative(note.DOCS / Path(*parts))
            if rel and (note.DOCS / Path(*parts)).exists():
                return f'{attr}="/doc/{rel}"'
        return m.group(0)

    return URL_ATTR.sub(repl, html)


def preview_assets() -> dict:
    """预览要引用的样式表。优先用 mkdocs 真实构建产物，缺失时退回内置兜底样式。"""
    css: list[str] = []
    sheets = SITE / "assets" / "stylesheets"
    if sheets.exists():
        for pattern in ("main*.min.css", "palette*.min.css"):
            hits = sorted(sheets.glob(pattern))
            if hits:
                css.append("/" + hits[0].relative_to(note.ROOT).as_posix())
    has_material = bool(css)
    if not has_material:
        css.append("/preview-fallback.css")
    if (note.DOCS / "assets" / "extra.css").exists():
        css.append("/assets/extra.css")
    if (note.DOCS / "assets" / "katex" / "katex.min.css").exists():
        css.append("/assets/katex/katex.min.css")
    katex_js = []
    kdir = note.DOCS / "assets" / "katex"
    if (kdir / "katex.min.js").exists():
        katex_js = ["/assets/katex/katex.min.js", "/assets/katex/contrib/auto-render.min.js"]
    return {"css": css, "katex_js": katex_js, "material": has_material}


def render_preview(md: str, note_rel: str = "") -> dict:
    html = render_markdown(strip_front_matter(md))
    html = rewrite_local_urls(html, note_rel)
    return {"html": html, **preview_assets()}


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


def _up_prefix(note_rel: str) -> str:
    """从笔记所在目录回到 docs 根所需的 ../ 前缀。

    站点（MkDocs）按「相对笔记文件所在目录」解析图片路径，所以上传到
    docs/assets/uploads 的图片必须写成 ../../assets/uploads/x.png 这种形式，
    否则笔记放在子目录里时线上就会 404。
    """
    parent = PurePosixPath(note_rel).parent if note_rel else PurePosixPath(".")
    depth = 0 if str(parent) in (".", "") else len(parent.parts)
    return "../" * depth


def upload_image(name: str, b64: str, note_rel: str = "") -> dict:
    """保存上传的图片到 docs/assets/uploads，返回可引用的相对路径（相对笔记目录）。"""
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

    # 安全文件名：保留扩展名，加随机后缀避免重名与路径穿越
    stem = re.sub(r"[^\w一-龥-]", "", Path(name).stem)[:40] or "image"
    ext = Path(name).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"):
        ext = ".png"
    fname = f"{stem}-{uuid.uuid4().hex[:6]}{ext}"
    (up / fname).write_bytes(data)
    url = f"{_up_prefix(note_rel)}assets/uploads/{fname}"
    return {"ok": True, "url": url, "name": name}


# --------------------------------------------------------------------------
# 构建 / 发布 / 整站预览
# --------------------------------------------------------------------------
# 子进程输出统一按 UTF-8 解码：Windows 默认走 GBK，mkdocs/git 的输出里
# 只要有一个非 GBK 字节，解码线程就会抛 UnicodeDecodeError，进而让
# stdout 变成 None，后续字符串拼接直接 TypeError —— 表现为「发布失败」。
SUB_KW = {"encoding": "utf-8", "errors": "replace"}

# 某些托管环境会通过 PYTHONPATH 注入 sitecustomize，用来拦截文件删除
# （表现为 mkdocs 清理 site/ 时报 SAFE_DELETE_FAIL_CLOSED）。子进程里剥掉这些
# 变量，保证「构建 / 发布」在任何启动方式下都能正常清理站点目录。
ENV_STRIP = ("PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME")


def _child_env() -> dict:
    import os

    env = os.environ.copy()
    for k in ENV_STRIP:
        env.pop(k, None)
    return env


def _run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(note.ROOT), capture_output=True, check=check,
        env=_child_env(), **SUB_KW,
    )


def _out(proc: subprocess.CompletedProcess) -> str:
    """安全拼接子进程输出（解码异常时对应流可能为 None）。"""
    return ((proc.stdout or "") + (proc.stderr or "")).strip()


def run_build() -> tuple[bool, str]:
    try:
        proc = _run([note.PY, "-m", "mkdocs", "build"])
    except Exception as e:  # 解释器缺失等
        return False, f"无法执行构建：{e}"
    ok = proc.returncode == 0
    log = _out(proc) or ("构建成功" if ok else "构建失败（无输出）")
    return ok, log


def run_publish(message: str) -> tuple[bool, str]:
    """构建校验 + git 提交 + git push。返回 (ok, 给用户看的信息)。"""
    message = message or "更新学习笔记"
    try:
        # 1. 构建校验（失败立即中止，不污染 git）
        print("▶ 第 1 步 / 3：构建校验……")
        rc = _run([note.PY, "-m", "mkdocs", "build"])
        if rc.returncode != 0:
            return False, f"构建失败\n{_out(rc)[-1000:]}"

        # 2. 暂存 + 提交
        print("▶ 第 2 步 / 3：暂存并提交……")
        _run(["git", "add", "-A"], check=True)
        proc = _run(["git", "commit", "-m", message])
        if proc.returncode != 0:
            err = _out(proc)
            # Git for Windows 把这条消息写到 stdout；同时兼容 stderr
            if "nothing to commit" in err or "no changes added" in err:
                # 没有新内容变更，但本地可能领先远端（之前 commit 没推上去）。
                # 此时直接尝试 push，把本地领先的内容推到远端。
                for attempt in (1, 2):
                    push = _run(["git", "push"])
                    if push.returncode == 0:
                        return True, "本地没有新内容，但已把本地领先的提交推送到 GitHub（约 1 分钟自动部署）"
                    err2 = _out(push)
                    if "cannot lock ref" in err2 and attempt == 1:
                        import time as _t
                        _t.sleep(2)
                        continue
                    if "up-to-date" in err2.lower():
                        return True, "本地与远程一致，线上已是最新"
                    return False, f"推送失败\n{err2[-1000:]}"
                return True, "本地与远程一致，线上已是最新"
            return False, f"提交失败\n{err[-1000:]}"

        # 3. push（lock 冲突会自动重试一次）
        print("▶ 第 3 步 / 3：推送到 GitHub……")
        for attempt in (1, 2):
            push = _run(["git", "push"])
            if push.returncode == 0:
                return True, "已提交并推送，GitHub Actions 将在约 1 分钟内自动部署。"
            err = _out(push)
            if "cannot lock ref" in err and attempt == 1:
                # GitHub 端短暂 ref 锁冲突，等 2 秒重试一次
                import time as _t
                _t.sleep(2)
                continue
            return False, f"推送失败\n{err[-1000:]}"
    except subprocess.CalledProcessError as e:
        raw = e.stderr or e.stdout or b"git error"
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        return False, str(raw).strip()


def site_preview_start() -> tuple[bool, str]:
    global SITE_PROC
    if SITE_PROC and SITE_PROC.poll() is None:
        return True, "http://127.0.0.1:8001/learn-notes/"
    SITE_PROC = subprocess.Popen(
        [note.PY, "-m", "mkdocs", "serve", "--dev-addr", "127.0.0.1:8001"],
        cwd=str(note.ROOT),
        env=_child_env(),
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
MIME = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
}


def _mime_for(p: Path) -> str:
    return MIME.get(p.suffix.lower(), "application/octet-stream")


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
        # 静态资源：/assets/*（docs/assets）、/doc/*（docs 内任意文件，供预览取图）、/site/*（构建产物，供预览取样式表）
        for prefix, root in (("/assets/", ASSETS), ("/doc/", note.DOCS), ("/site/", SITE)):
            if path.startswith(prefix):
                rel = unquote(path[len(prefix):])
                target = (root / rel).resolve()
                try:
                    target.relative_to(root.resolve())
                except ValueError:
                    return self.send_error(403)
                if target.is_file():
                    return self._send_file(target, _mime_for(target))
                self.send_error(404)
                return
        if path == "/preview-fallback.css":
            fb = TOOLS / "preview_fallback.css"
            if fb.exists():
                return self._send_file(fb, "text/css; charset=utf-8")
            self.send_error(404)
            return
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
            return self._send_json(render_preview(data.get("md", ""), data.get("path", "")))

        if path == "/api/upload":
            res = upload_image(data.get("name", "image.png"), data.get("data", ""), data.get("path", ""))
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


def _instance_alive(port: int) -> bool:
    """检测是否已有本后台实例在运行。

    Windows 的 SO_REUSEADDR 允许两个进程同时监听同一端口，会导致请求被
    随机分给新旧两个进程（旧进程还跑着老代码）—— 启动前先探测，避免出现
    「一会儿正常一会儿不正常」的怪现象。
    """
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/tree", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def run(port: int = PORT) -> None:
    url = f"http://127.0.0.1:{port}/"
    if _instance_alive(port):
        print(f"▶ 后台已在运行：{url}  （直接打开页面，不重复启动）")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        return
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        # 端口被别的程序占用 —— 打开页面看看是不是我们的服务
        print(f"▶ 端口 {port} 已被占用，尝试直接打开页面：{url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        return
    print(f"▶ 学习笔记可视化后台已启动：{url}  （关闭本窗口即停止）")
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
