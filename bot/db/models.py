from sqlalchemy import (
    Column, Integer, BigInteger, Text, TIMESTAMP, ForeignKey, String, Date
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True)  # Telegram ID
    full_name = Column(Text, nullable=False)
    role = Column(String, nullable=False)  # 'admin', 'bm', 'teacher'
    created_at = Column(TIMESTAMP, server_default=func.now())


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    bm_id = Column(BigInteger, ForeignKey("users.id"))


class TeacherSubject(Base):
    __tablename__ = "teacher_subjects"
    teacher_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), primary_key=True)


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    teacher_id = Column(BigInteger, ForeignKey("users.id"))
    week_label = Column(Text, nullable=False)
    lesson_date = Column(Date, nullable=False)
    topic = Column(Text, nullable=False)
    deadline = Column(TIMESTAMP, nullable=False)
    created_by = Column(BigInteger, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, server_default=func.now())


class SlideSubmission(Base):
    __tablename__ = "slide_submissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("weekly_plans.id"))
    teacher_id = Column(BigInteger, ForeignKey("users.id"))
    file_id = Column(Text, nullable=False)
    file_name = Column(Text)
    uploaded_at = Column(TIMESTAMP, server_default=func.now())
    ai_check_result = Column(JSONB, nullable=True)
    ai_check_status = Column(String)  # 'pending', 'passed', 'failed'
