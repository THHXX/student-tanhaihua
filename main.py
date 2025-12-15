from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form
from contextlib import asynccontextmanager
from starlette.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from database import Base, engine, get_db, Submission, Folder
from schemas import SubmissionCreate, SubmissionRead, ErrorResponse
from sqlalchemy import inspect, text
import os
import uuid
from pathlib import Path
import io
import zipfile
import urllib.parse

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="学生管理系统", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
UPLOAD_DIR = "uploads"

# --- UI Helper ---
def render_base(content, title="作业管理系统"):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='utf-8'>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{title}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f0f2f5; color: #333; }}
            .container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            h1, h2, h3 {{ color: #1a1a1a; margin-top: 0; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 15px; }}
            .btn {{ display: inline-flex; align-items: center; justify-content: center; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 6px; border: none; cursor: pointer; font-size: 14px; transition: all 0.2s; font-weight: 500; }}
            .btn:hover {{ background: #0069d9; transform: translateY(-1px); }}
            .btn-sm {{ padding: 6px 12px; font-size: 13px; }}
            .btn-danger {{ background: #dc3545; }}
            .btn-danger:hover {{ background: #c82333; }}
            .btn-success {{ background: #28a745; }}
            .btn-success:hover {{ background: #218838; }}
            .btn-secondary {{ background: #6c757d; }}
            .btn-secondary:hover {{ background: #5a6268; }}
            
            .folder-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; margin-top: 20px; }}
            .folder-card {{ border: 1px solid #eaeaea; padding: 20px; border-radius: 10px; background: #fff; text-align: center; transition: all 0.3s ease; text-decoration: none; color: inherit; display: block; position: relative; overflow: hidden; }}
            .folder-card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); border-color: #007bff; }}
            .folder-icon {{ font-size: 50px; color: #ffc107; margin-bottom: 10px; display: block; }}
            .folder-name {{ font-weight: 600; font-size: 16px; display: block; margin-bottom: 5px; }}
            .folder-count {{ font-size: 12px; color: #888; }}
            
            .table-container {{ overflow-x: auto; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; background: white; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #f8f9fa; font-weight: 600; color: #555; white-space: nowrap; }}
            tr:hover {{ background-color: #f8f9fa; }}
            
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 8px; font-weight: 600; color: #555; }}
            input, select {{ width: 100%; padding: 10px; box-sizing: border-box; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; transition: border-color 0.2s; }}
            input:focus, select:focus {{ border-color: #007bff; outline: none; }}
            
            .breadcrumb {{ margin-bottom: 20px; font-size: 14px; color: #666; }}
            .breadcrumb a {{ color: #007bff; text-decoration: none; }}
            .breadcrumb span {{ margin: 0 5px; color: #ccc; }}
            
            .actions-bar {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
            .empty-state {{ text-align: center; padding: 40px; color: #888; font-style: italic; }}
            
            .flash-message {{ padding: 15px; background: #d4edda; color: #155724; border-radius: 6px; margin-bottom: 20px; border: 1px solid #c3e6cb; }}
            .flash-error {{ background: #f8d7da; color: #721c24; border-color: #f5c6cb; }}
        </style>
    </head>
    <body>
        <div class="container">
            {content}
        </div>
    </body>
    </html>
    """

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
def index(db: Session = Depends(get_db)):
    folders = db.query(Folder).order_by(Folder.created_at.desc()).all()
    
    folder_html = ""
    for f in folders:
        # Count submissions
        count = db.query(Submission).filter(Submission.class_name == f.name).count()
        folder_html += f"""
        <a href="/folders/{f.id}" class="folder-card">
            <span class="folder-icon">📁</span>
            <span class="folder-name">{f.name}</span>
            <span class="folder-count">{count} 份作业</span>
        </a>
        """
    
    if not folders:
        folder_html = "<div class='empty-state'>暂无文件夹。</div>"

    content = f"""
    <div class="header">
        <h1>作业管理系统</h1>
        <a href="/submit" class="btn">我要交作业</a>
    </div>
    
    <h3>文件夹列表</h3>
    <div class="folder-grid">
        {folder_html}
    </div>
    """
    return render_base(content)

@app.get("/admin", response_class=HTMLResponse)
def admin_index(db: Session = Depends(get_db)):
    folders = db.query(Folder).order_by(Folder.created_at.desc()).all()
    
    folder_html = ""
    for f in folders:
        # Count submissions
        count = db.query(Submission).filter(Submission.class_name == f.name).count()
        folder_html += f"""
        <div style="position: relative;">
            <a href="/admin/folders/{f.id}" class="folder-card">
                <span class="folder-icon">📁</span>
                <span class="folder-name">{f.name}</span>
                <span class="folder-count">{count} 份作业</span>
            </a>
            <form action="/folders/{f.id}/delete" method="post" onsubmit="return confirm('确定要删除文件夹 【{f.name}】 吗？\\n注意：删除后文件夹内的作业可能无法分类！');" style="position: absolute; top: 10px; right: 10px; z-index: 10;">
                <button type="submit" title="删除文件夹" style="background: rgba(255, 255, 255, 0.9); border: 1px solid #ffcccc; color: #dc3545; width: 28px; height: 28px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px; transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">×</button>
            </form>
        </div>
        """
    
    if not folders:
        folder_html = "<div class='empty-state'>暂无文件夹，请先创建一个。</div>"

    content = f"""
    <div class="header">
        <h1>作业管理系统 (管理员)</h1>
        <a href="/" class="btn btn-secondary">返回首页</a>
    </div>
    
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
        <h3>新建文件夹 (课程/科目)</h3>
        <form action="/folders/create" method="post" style="display: flex; gap: 10px;">
            <input type="text" name="name" placeholder="例如：高等数学、马克思主义原理" required style="flex: 1;">
            <button type="submit" class="btn btn-success">创建</button>
        </form>
    </div>

    <h3>文件夹列表 (管理模式)</h3>
    <div class="folder-grid">
        {folder_html}
    </div>
    """
    return render_base(content, title="管理员控制台")

@app.post("/folders/create", response_class=HTMLResponse)
def create_folder(name: str = Form(...), db: Session = Depends(get_db)):
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    
    existing = db.query(Folder).filter(Folder.name == name).first()
    if existing:
        return RedirectResponse(url="/admin?error=exists", status_code=303)
        
    new_folder = Folder(name=name)
    db.add(new_folder)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/folders/{folder_id}", response_class=HTMLResponse)
def view_folder(folder_id: int, db: Session = Depends(get_db)):
    # Student View: No download links, no delete buttons
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    
    submissions = db.query(Submission).filter(Submission.class_name == folder.name).order_by(Submission.submitted_at.desc()).all()
    
    rows = ""
    for sub in submissions:
        time_str = sub.submitted_at.strftime("%Y-%m-%d %H:%M")
        rows += f"""
        <tr>
            <td>{sub.student_name}</td>
            <td>{sub.student_no}</td>
            <td>{time_str}</td>
            <td><span style="color: #888;">已提交</span></td>
        </tr>
        """
    
    if not submissions:
        rows = "<tr><td colspan='4' class='empty-state'>该文件夹下暂无作业</td></tr>"

    content = f"""
    <div class="breadcrumb">
        <a href="/">首页</a> <span>/</span> {folder.name}
    </div>

    <div class="header">
        <h2>{folder.name}</h2>
        <div class="actions-bar">
            <a href="/submit?folder_id={folder.id}" class="btn">在此提交作业</a>
        </div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>姓名</th>
                    <th>学号</th>
                    <th>提交时间</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    """
    return render_base(content, title=folder.name)

@app.get("/admin/folders/{folder_id}", response_class=HTMLResponse)
def view_folder_admin(folder_id: int, db: Session = Depends(get_db)):
    # Admin View: Full access
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    
    submissions = db.query(Submission).filter(Submission.class_name == folder.name).order_by(Submission.submitted_at.desc()).all()
    
    rows = ""
    for sub in submissions:
        file_url = f"/api/submissions/{sub.id}/file"
        time_str = sub.submitted_at.strftime("%Y-%m-%d %H:%M")
        rows += f"""
        <tr>
            <td>{sub.student_name}</td>
            <td>{sub.student_no}</td>
            <td>{time_str}</td>
            <td><a href="{file_url}" class="btn btn-sm btn-secondary" target="_blank">下载文件</a></td>
        </tr>
        """
    
    if not submissions:
        rows = "<tr><td colspan='4' class='empty-state'>该文件夹下暂无作业</td></tr>"

    content = f"""
    <div class="breadcrumb">
        <a href="/admin">管理首页</a> <span>/</span> {folder.name}
    </div>

    <div class="header">
        <h2>{folder.name} (管理)</h2>
        <div class="actions-bar">
            <a href="/submit?folder_id={folder.id}" class="btn">在此提交作业</a>
            <a href="/folders/{folder.id}/download" class="btn btn-success">📦 打包下载全部</a>
        </div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>姓名</th>
                    <th>学号</th>
                    <th>提交时间</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>

    <div style="margin-top: 50px; border-top: 1px solid #eee; padding-top: 20px;">
        <form action="/folders/{folder.id}/delete" method="post" onsubmit="return confirm('确定要删除这个文件夹吗？删除后文件夹内的记录可能无法分类！');">
            <button type="submit" class="btn btn-danger btn-sm">删除此文件夹</button>
        </form>
    </div>
    """
    return render_base(content, title=f"{folder.name} - 管理")

@app.post("/folders/{folder_id}/delete")
def delete_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if folder:
        db.delete(folder)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/folders/{folder_id}/download")
def download_folder_zip(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404)
    
    submissions = db.query(Submission).filter(Submission.class_name == folder.name).all()
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for sub in submissions:
            # Create a unique name inside zip: Name_No_Filename
            zip_name = f"{sub.student_name}_{sub.student_no}_{sub.file_name}"
            
            try:
                if os.path.isfile(sub.file_path):
                    with open(sub.file_path, "rb") as f:
                        zf.writestr(zip_name, f.read())
            except Exception as e:
                print(f"Error zipping {sub.id}: {e}")
                pass
                
    buf.seek(0)
    filename = urllib.parse.quote(f"{folder.name}_作业打包.zip")
    return StreamingResponse(
        buf, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )

@app.get("/submit", response_class=HTMLResponse)
def submit_form(folder_id: int = None, db: Session = Depends(get_db)):
    folders = db.query(Folder).all()
    options = ""
    for f in folders:
        selected = "selected" if folder_id and f.id == folder_id else ""
        options += f'<option value="{f.name}" {selected}>{f.name}</option>'
    
    if not folders:
        options = '<option value="" disabled>请先在首页创建文件夹</option>'

    content = f"""
    <div class="header">
        <h2>提交作业</h2>
        <a href="/" class="btn btn-secondary btn-sm">返回首页</a>
    </div>
    
    <form method="post" action="/submit" enctype="multipart/form-data" style="max-width: 500px; margin: 0 auto;">
        <div class="form-group">
            <label>提交到文件夹 (科目/班级)</label>
            <select name="class_name" required>
                {options}
            </select>
        </div>
        
        <div class="form-group">
            <label>姓名</label>
            <input name="student_name" required placeholder="请输入你的名字">
        </div>
        
        <div class="form-group">
            <label>学号</label>
            <input name="student_no" required placeholder="请输入你的学号">
        </div>
        
        <div class="form-group">
            <label>作业文件</label>
            <input type="file" name="file" required style="border: 1px dashed #ccc; padding: 20px; background: #fafafa;">
        </div>
        
        <button type="submit" class="btn btn-success" style="width: 100%; margin-top: 10px;">🚀 确认提交</button>
    </form>
    """
    return render_base(content, title="提交作业")

@app.post("/submit", response_class=HTMLResponse)
async def submit_form_post(
    student_name: str = Form(...),
    student_no: str = Form(...),
    class_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        # File Saving Logic
        data = await file.read()
        
        file_path = ""
        storage_provider = "local"

        Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(file.filename)[1] or ""
        safe = f"{uuid.uuid4().hex}{ext}"
        dest = Path(UPLOAD_DIR) / safe
        dest.write_bytes(data)
        
        file_path = str(dest)

        obj = Submission(
            student_name=student_name, 
            student_no=student_no, 
            class_name=class_name,
            file_name=file.filename, 
            file_path=file_path, 
            file_key="", 
            file_url="",
            storage_provider=storage_provider,
            content_type=file.content_type, 
            file_size=len(data)
        )
        db.add(obj)
        db.commit()
        
        # Find folder ID to redirect
        folder = db.query(Folder).filter(Folder.name == class_name).first()
        if folder:
            return RedirectResponse(url=f"/folders/{folder.id}", status_code=303)
        else:
            return RedirectResponse(url="/", status_code=303)

    except Exception as e:
        return render_base(f"<div class='flash-error'>提交失败：{str(e)}</div><a href='/submit' class='btn'>重试</a>")

@app.get("/api/submissions/{submission_id}/file")
def download_submission_file(submission_id: int, db: Session = Depends(get_db)):
    obj = db.query(Submission).filter(Submission.id == submission_id).first()
    if not obj:
        raise HTTPException(status_code=404)
    
    # Local file
    if not os.path.isfile(obj.file_path):
        raise HTTPException(status_code=404, detail="文件未找到")
        
    filename = urllib.parse.quote(obj.file_name)
    return FileResponse(obj.file_path, media_type=obj.content_type, filename=obj.file_name)

# Keep API endpoints for compatibility if needed, but UI is primary now.
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
