import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


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