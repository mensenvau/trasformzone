import os
import sys
from pathlib import Path
from fastapi import FastAPI, Form, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

sys.path.append(str(Path(__file__).parent.parent))

from utils.sql import execute_all, execute_one
from utils.build_logger import log_build, get_build_history
from tools.ai import generator_config, generator_parser

app = FastAPI()
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

PAGE_SIZE = 15

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    registry = execute_all("SELECT TOP 20 * FROM config.file_registry WHERE is_active = 1 ORDER BY id DESC")
    return templates.TemplateResponse(
        request=request, name="index.html", context={"registry": registry, "history": get_build_history(10)}
    )

@app.get("/registry", response_class=HTMLResponse)
async def registry_view(request: Request, page: int = Query(1, ge=1), q: str = Query("")):
    offset = (page - 1) * PAGE_SIZE
    search = f"%{q}%"
    rows = execute_all("""
        SELECT * FROM config.file_registry
        WHERE is_active = 1
          AND (domain LIKE ? OR report_type LIKE ? OR file_wildcard LIKE ? OR target_table LIKE ?)
        ORDER BY id DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """, (search, search, search, search, offset, PAGE_SIZE))
    total = execute_one("""
        SELECT COUNT(*) AS cnt FROM config.file_registry
        WHERE is_active = 1
          AND (domain LIKE ? OR report_type LIKE ? OR file_wildcard LIKE ? OR target_table LIKE ?)
    """, (search, search, search, search))
    total_count = total.get('cnt', 0)
    total_pages = max(1, -(-total_count // PAGE_SIZE))
    return templates.TemplateResponse(
        request=request, name="registry.html",
        context={"registry": rows, "page": page, "total_pages": total_pages, "total_count": total_count, "q": q}
    )

@app.post("/registry/add")
async def add_registry(domain: str = Form(...), report_type: str = Form(...),
                        file_wildcard: str = Form(...),
                        target_table: str = Form(...), insert_mode: str = Form(...),
                        key_columns: str = Form(None), description: str = Form(None)):
    execute_all("""
        INSERT INTO config.file_registry (domain, report_type, file_wildcard, target_table, insert_mode, key_columns, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (domain, report_type, file_wildcard, target_table, insert_mode, key_columns, description))
    return RedirectResponse(url="/registry", status_code=303)

@app.post("/registry/{reg_id}/edit")
async def edit_registry(reg_id: int, domain: str = Form(...), report_type: str = Form(...),
                         file_wildcard: str = Form(...), guid: str = Form(...),
                         target_table: str = Form(...), insert_mode: str = Form(...),
                         key_columns: str = Form(None), description: str = Form(None)):
    execute_all("""
        UPDATE config.file_registry
        SET domain=?, report_type=?, file_wildcard=?, guid=?, target_table=?, insert_mode=?, key_columns=?, description=?, updated_at=GETDATE()
        WHERE id=?
    """, (domain, report_type, file_wildcard, guid, target_table, insert_mode, key_columns, description, reg_id))
    return RedirectResponse(url="/registry", status_code=303)

@app.post("/registry/{reg_id}/delete")
async def delete_registry(reg_id: int):
    execute_all("UPDATE config.file_registry SET is_active = 0 WHERE id = ?", (reg_id,))
    return RedirectResponse(url="/registry", status_code=303)

@app.get("/workflow/{reg_id}", response_class=HTMLResponse)
async def workflow(request: Request, reg_id: int):
    reg = execute_one("SELECT * FROM config.file_registry WHERE id = ?", (reg_id,))
    root = Path(__file__).parent.parent
    config_path = root / "parsers" / reg['domain'] / reg['report_type'] / "current" / "config.yaml"
    parser_path = root / "parsers" / reg['domain'] / reg['report_type'] / "current" / "parser.py"
    config_content = open(config_path, encoding='utf-8').read() if config_path.exists() else ""
    parser_code = open(parser_path, encoding='utf-8').read() if parser_path.exists() else ""
    return templates.TemplateResponse(
        request=request, name="workflow.html",
        context={"reg": reg, "config_content": config_content, "parser_code": parser_code}
    )

@app.post("/workflow/{reg_id}/generate-config")
async def api_config(reg_id: int, sub_id: str = Form(...)):
    reg = execute_one("SELECT * FROM config.file_registry WHERE id = ?", (reg_id,))
    try:
        generator_config.generate(reg['domain'], reg['report_type'], reg['guid'], sub_id, reg['file_wildcard'], "01")
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/workflow/{reg_id}/generate-parser")
async def api_parser(reg_id: int, sub_id: str = Form(...)):
    reg = execute_one("SELECT * FROM config.file_registry WHERE id = ?", (reg_id,))
    try:
        generator_parser.generate(reg['domain'], reg['report_type'], reg['guid'], sub_id, reg['file_wildcard'], 2, "01")
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
