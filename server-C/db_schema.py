"""作业提交数据库表结构常量（2026作业2路线1提交数据库说明文档）。"""

import os

# 院系编号（系统 C）
DEPT_NO = "C"
COLLEGE_C = DEPT_NO
COLLEGE_DEPARTMENT = "院系C"

# 组号：可通过环境变量 GROUP_NO 覆盖，提交前请改为本组编号
GROUP_NO = os.environ.get("GROUP_NO", "3")

# 提交服务器 hw4（见 2026作业2路线1提交数据库说明文档.md）
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "10.60.254.44"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "123456"),
    "database": os.environ.get("DB_NAME", "hw4"),
    "charset": "utf8mb4",
    "autocommit": True,
}

# 学生表 student
STUDENT_COLS = [
    "student_id",
    "student_name",
    "gender",
    "department",
    "account",
    "password",
    "group_no",
    "dept_no",
]

# 课程表 course
COURSE_COLS = [
    "course_id",
    "course_name",
    "credit",
    "teacher_name",
    "location",
    "share_flag",
    "class_hours",
    "practice_hours",
    "group_no",
    "dept_no",
]

# 选课表 sc
SC_COLS = [
    "course_id",
    "student_id",
    "score",
    "group_no",
    "dept_no",
]

CREATE_STUDENT = """
CREATE TABLE IF NOT EXISTS student (
    student_id   VARCHAR(12) NOT NULL,
    student_name VARCHAR(10) NOT NULL,
    gender       VARCHAR(2)  NOT NULL,
    department   VARCHAR(16) NOT NULL,
    account      VARCHAR(10) NOT NULL,
    password     VARCHAR(6)  NOT NULL,
    group_no     VARCHAR(10) NOT NULL,
    dept_no      VARCHAR(10) NOT NULL,
    PRIMARY KEY (student_id, group_no, dept_no)
)
"""

CREATE_COURSE = """
CREATE TABLE IF NOT EXISTS course (
    course_id      VARCHAR(8)  NOT NULL,
    course_name    VARCHAR(16) NOT NULL,
    credit         VARCHAR(2)  NOT NULL,
    teacher_name   VARCHAR(20) NOT NULL,
    location       VARCHAR(20) NOT NULL,
    share_flag     CHAR(1)     NOT NULL,
    class_hours    VARCHAR(10) NOT NULL,
    practice_hours VARCHAR(10) NOT NULL,
    group_no       VARCHAR(10) NOT NULL,
    dept_no        VARCHAR(10) NOT NULL,
    PRIMARY KEY (course_id, group_no, dept_no)
)
"""

CREATE_SC = """
CREATE TABLE IF NOT EXISTS sc (
    course_id  VARCHAR(8)  NOT NULL,
    student_id VARCHAR(12) NOT NULL,
    score      VARCHAR(3)  NOT NULL DEFAULT '',
    group_no   VARCHAR(10) NOT NULL,
    dept_no    VARCHAR(10) NOT NULL,
    PRIMARY KEY (course_id, student_id, group_no, dept_no)
)
"""

LEGACY_TABLES = [
    "c_accounts",
    "c_students",
    "c_courses",
    "c_sc",
]

# 已废弃的集成辅助表（启动时迁移数据到 sc/course 后删除）
DEPRECATED_INTEGRATION_TABLES = [
    "imported_shared_courses",
    "cross_college_selections",
    "inbound_cross_enrollments",
]

INTEGRATION_DDL: list[str] = []

# hw4 提交表复合主键（共享库若仅有 course_id 主键会导致外院课程导入写入他院记录）
SUBMISSION_PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "student": ("student_id", "group_no", "dept_no"),
    "course": ("course_id", "group_no", "dept_no"),
    "sc": ("course_id", "student_id", "group_no", "dept_no"),
}
