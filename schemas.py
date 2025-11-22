import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class StudentBase(BaseModel):
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    class_name: Optional[str] = None

    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError("年龄必须在0-150之间")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("姓名不能为空")
        return v

    @field_validator("class_name")
    @classmethod
    def validate_class_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("班级不能为空")
        return v


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    class_name: Optional[str] = None

    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError("年龄必须在0-150之间")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("姓名不能为空")
        return v

    @field_validator("class_name")
    @classmethod
    def validate_class_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("班级不能为空")
        return v


class StudentRead(StudentBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        v = (v or "").strip()
        if len(v) < 3:
            raise ValueError("用户名长度至少为3")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        v = (v or "").strip()
        if len(v) < 6:
            raise ValueError("密码长度至少为6")
        return v


class UserRead(BaseModel):
    id: int
    username: str
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)


class LoginData(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        v = (v or "").strip()
        if len(v) < 3:
            raise ValueError("用户名长度至少为3")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        v = (v or "").strip()
        if len(v) < 6:
            raise ValueError("密码长度至少为6")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SubmissionCreate(BaseModel):
    student_name: str
    student_no: str
    class_name: str

    @field_validator("student_name")
    @classmethod
    def v_student_name(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("姓名不能为空")
        return v

    @field_validator("student_no")
    @classmethod
    def v_student_no(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("学号不能为空")
        return v

    @field_validator("class_name")
    @classmethod
    def v_class_name(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("班级不能为空")
        return v


class SubmissionRead(BaseModel):
    id: int
    student_name: str
    student_no: str
    class_name: str
    file_name: str
    file_path: str
    file_url: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    submitted_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)