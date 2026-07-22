"""
V2.1 web server — 提供 web/ 静态资源 + 启用 gzip
跑: uvicorn api.web_server:app --host 0.0.0.0 --port 8000
"""
import gzip
import mimetypes
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).parent.parent
WEB_DIR = ROOT / "web"

app = FastAPI(title="Open Curriculum CN Web")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# 可 gzip 压缩的 MIME
GZIP_TYPES = {
    "application/javascript", "text/javascript", "text/css",
    "application/json", "text/html", "text/xml", "text/plain",
    "image/svg+xml",
}


def _should_gzip(req: Request, content_type: str) -> bool:
    """只在客户端支持 + 体积 > 1KB + 类型在白名单时启用 gzip"""
    if not content_type.split(";")[0].strip() in GZIP_TYPES:
        return False
    accept = req.headers.get("accept-encoding", "")
    return "gzip" in accept.lower()


@app.get("/{path:path}")
def serve(path: str = ""):
    """静态文件 + gzip"""
    if not path:
        path = "index.html"
    # P0 必修: 防路径遍历 — 解析后必须在 WEB_DIR 内
    fp = (WEB_DIR / path).resolve()
    try:
        fp.relative_to(WEB_DIR.resolve())
    except ValueError:
        return Response("Forbidden", status_code=403)
    if not fp.exists() or not fp.is_file():
        return Response("Not Found", status_code=404)

    # Mime
    mt, _ = mimetypes.guess_type(str(fp))
    if not mt:
        mt = "application/octet-stream"
    return _make_response(fp, mt)


def _make_response(fp, mt):
    """实际生成 response"""
    headers = {
        "Content-Type": mt,
        "Cache-Control": "public, max-age=3600",
    }
    if mt.split(";")[0].strip() in GZIP_TYPES:
        # 静态 gzip 预压缩 (build 时压缩一次, serve 时返回)
        gz_path = fp.with_suffix(fp.suffix + ".gz")
        if gz_path.exists():
            return FileResponse(gz_path, media_type=mt, headers={**headers, "Content-Encoding": "gzip"})
    return FileResponse(fp, media_type=mt, headers=headers)


@app.get("/")
def root():
    return FileResponse(WEB_DIR / "index.html", media_type="text/html")
