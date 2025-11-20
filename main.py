from fastapi import FastAPI, Depends, HTTPException, status, Request
from contextlib import asynccontextmanager
from starlette.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from crud.student_crud import get_students, get_student, create_student, update_student, delete_student
from crud.user_crud import get_user_by_username, create_user
from schemas import StudentCreate, StudentUpdate, StudentRead, UserCreate, UserRead, Token, LoginData
from auth import get_password_hash, verify_password, create_access_token, get_current_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="学生管理系统", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/app")
def app_index():
    return FileResponse("static/index.html")


@app.get("/")
async def root():
    return {"message": "学生管理系统 API 已启动！"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T10:00:00"}


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