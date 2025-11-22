from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form
from contextlib import asynccontextmanager
from starlette.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from database import Base, engine, get_db, Submission
from crud.student_crud import get_students, get_student, create_student, update_student, delete_student
from crud.user_crud import get_user_by_username, create_user
from schemas import StudentCreate, StudentUpdate, StudentRead, UserCreate, UserRead, Token, LoginData
from schemas import SubmissionCreate, SubmissionRead
from auth import get_password_hash, verify_password, create_access_token, get_current_user
from sqlalchemy import inspect, text

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    try:
        cols = [c['name'] for c in insp.get_columns('submissions')]
        with engine.begin() as conn:
            if 'class_name' not in cols:
                conn.execute(text('ALTER TABLE submissions ADD COLUMN class_name VARCHAR(50)'))
            if 'file_key' not in cols:
                conn.execute(text('ALTER TABLE submissions ADD COLUMN file_key VARCHAR(255)'))
            if 'file_url' not in cols:
                conn.execute(text('ALTER TABLE submissions ADD COLUMN file_url VARCHAR(512)'))
            if 'storage_provider' not in cols:
                conn.execute(text('ALTER TABLE submissions ADD COLUMN storage_provider VARCHAR(50)'))
    except Exception:
        pass
    yield

app = FastAPI(title="学生管理系统", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
UPLOAD_DIR = "uploads"

@app.get("/submit", response_class=HTMLResponse)
def submit_form():
    return """
    <html><head><meta charset='utf-8'><title>提交作业</title></head>
    <body>
      <h2>提交作业</h2>
      <form method="post" action="/submit" enctype="multipart/form-data">
        姓名：<input name="student_name" required><br>
        学号：<input name="student_no" required><br>
        班级：<input name="class_name" required><br>
        文件：<input type="file" name="file" required><br>
        <button type="submit">提交</button>
      </form>
    </body></html>
    """

@app.post("/submit", response_class=HTMLResponse)
async def submit_form_post(
    student_name: str = Form(...),
    student_no: str = Form(...),
    class_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        import os, uuid, boto3
        from pathlib import Path
        data = await file.read()
        bucket = os.getenv("S3_BUCKET")
        if bucket:
            endpoint = os.getenv("S3_ENDPOINT_URL")
            region = os.getenv("AWS_REGION")
            s3 = boto3.client("s3",
                               aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                               aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                               region_name=region,
                               endpoint_url=endpoint or None)
            ext = os.path.splitext(file.filename)[1] or ""
            key = f"submissions/{uuid.uuid4().hex}{ext}"
            s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=file.content_type)
            url = (endpoint.rstrip("/") + f"/{bucket}/{key}") if endpoint else f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
            obj = Submission(student_name=student_name, student_no=student_no, class_name=class_name,
                             file_name=file.filename, file_path=key, file_key=key, file_url=url,
                             storage_provider=("custom" if endpoint else "aws"),
                             content_type=file.content_type, file_size=len(data))
        else:
            Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
            ext = os.path.splitext(file.filename)[1] or ""
            safe = f"{uuid.uuid4().hex}{ext}"
            dest = Path(UPLOAD_DIR) / safe
            dest.write_bytes(data)
            obj = Submission(student_name=student_name, student_no=student_no, class_name=class_name,
                             file_name=file.filename, file_path=str(dest),
                             content_type=file.content_type, file_size=len(data))
        db.add(obj)
        db.commit()
        return f"<p>提交成功，编号 {obj.id}</p>"
    except Exception as e:
        return f"<p>提交失败：{e}</p>"


@app.get("/")
async def root():
    return {"message": "作业提交服务已启动！"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T10:00:00"}

@app.get("/api/db/check")
def db_check():
    insp = inspect(engine)
    return {
        "dialect": engine.url.get_backend_name(),
        "database": engine.url.database,
        "tables": insp.get_table_names(),
    }

@app.post("/api/submissions", response_model=SubmissionRead)
async def create_submission(
    student_name: str = Form(...),
    student_no: str = Form(...),
    class_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    import os, uuid, boto3
    from pathlib import Path
    data = await file.read()
    bucket = os.getenv("S3_BUCKET")
    if bucket:
        endpoint = os.getenv("S3_ENDPOINT_URL")
        region = os.getenv("AWS_REGION")
        s3 = boto3.client("s3",
                           aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                           aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                           region_name=region,
                           endpoint_url=endpoint or None)
        ext = os.path.splitext(file.filename)[1] or ""
        key = f"submissions/{uuid.uuid4().hex}{ext}"
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=file.content_type)
        url = (endpoint.rstrip("/") + f"/{bucket}/{key}") if endpoint else f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        obj = Submission(student_name=student_name, student_no=student_no, class_name=class_name,
                         file_name=file.filename, file_path=key, file_key=key, file_url=url,
                         storage_provider=("custom" if endpoint else "aws"),
                         content_type=file.content_type, file_size=len(data))
    else:
        Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(file.filename)[1] or ""
        safe = f"{uuid.uuid4().hex}{ext}"
        dest = Path(UPLOAD_DIR) / safe
        dest.write_bytes(data)
        obj = Submission(student_name=student_name, student_no=student_no, class_name=class_name,
                         file_name=file.filename, file_path=str(dest),
                         content_type=file.content_type, file_size=len(data))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@app.get("/api/submissions", response_model=list[SubmissionRead])
def list_submissions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(Submission)
    return q.order_by(Submission.id.desc()).offset(skip).limit(limit).all()

@app.get("/api/submissions/export-zip")
def export_zip(db: Session = Depends(get_db)):
    import io, zipfile, os, boto3
    items = db.query(Submission).order_by(Submission.id.asc()).all()
    buf = io.BytesIO()
    zf = zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED)
    bucket = os.getenv("S3_BUCKET")
    s3 = None
    if bucket:
        endpoint = os.getenv("S3_ENDPOINT_URL")
        region = os.getenv("AWS_REGION")
        s3 = boto3.client("s3",
                           aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                           aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                           region_name=region,
                           endpoint_url=endpoint or None)
    for it in items:
        if bucket and it.file_key:
            resp = s3.get_object(Bucket=bucket, Key=it.file_key)
            data = resp["Body"].read()
            zf.writestr(it.file_name, data)
        else:
            try:
                with open(it.file_path, "rb") as f:
                    zf.writestr(it.file_name, f.read())
            except Exception:
                pass
    zf.close()
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=submissions.zip"})

@app.get("/api/submissions/{submission_id}/file")
def download_submission_file(submission_id: int, db: Session = Depends(get_db)):
    import os, boto3
    obj = db.query(Submission).filter(Submission.id == submission_id).first()
    if not obj:
        raise HTTPException(status_code=404)
    bucket = os.getenv("S3_BUCKET")
    if bucket and obj.file_key:
        endpoint = os.getenv("S3_ENDPOINT_URL")
        region = os.getenv("AWS_REGION")
        s3 = boto3.client("s3",
                           aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                           aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                           region_name=region,
                           endpoint_url=endpoint or None)
        resp = s3.get_object(Bucket=bucket, Key=obj.file_key)
        body = resp["Body"].read()
        return StreamingResponse(iter([body]), media_type=obj.content_type, headers={"Content-Disposition": f"attachment; filename={obj.file_name}"})
    return FileResponse(obj.file_path, media_type=obj.content_type, filename=obj.file_name)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR", "message": "请求参数校验失败", "details": exc.errors()})


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"code": "HTTP_ERROR", "message": exc.detail or "请求错误"})


@app.exception_handler(SQLAlchemyError)
async def handle_sqlalchemy_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"code": "DB_ERROR", "message": "数据库错误"})


@app.exception_handler(ResponseValidationError)
async def handle_response_validation_error(request: Request, exc: ResponseValidationError):
    return JSONResponse(status_code=500, content={"code": "RESPONSE_VALIDATION_ERROR", "message": "响应数据校验失败", "details": exc.errors()})

@app.get("/api/students", response_model=list[StudentRead])
def list_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_students(db, skip, limit)


@app.get("/api/students/{student_id}", response_model=StudentRead)
def get_student_detail(student_id: int, db: Session = Depends(get_db)):
    obj = get_student(db, student_id)
    if not obj:
        raise HTTPException(status_code=404)
    return obj


@app.post("/api/students", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student_endpoint(student: StudentCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return create_student(db, student)


@app.put("/api/students/{student_id}", response_model=StudentRead)
def update_student_endpoint(student_id: int, student: StudentUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    obj = update_student(db, student_id, student)
    if not obj:
        raise HTTPException(status_code=404)
    return obj


@app.delete("/api/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student_endpoint(student_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    obj = delete_student(db, student_id)
    if not obj:
        raise HTTPException(status_code=404)
    return None


@app.post("/api/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    hashed = get_password_hash(user.password)
    obj = create_user(db, user, hashed)
    return obj


@app.post("/api/auth/login", response_model=Token)
def login(data: LoginData, db: Session = Depends(get_db)):
    u = get_user_by_username(db, data.username)
    if not u or not verify_password(data.password, u.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码不正确")
    token = create_access_token({"sub": u.username})
    return {"access_token": token, "token_type": "bearer"}