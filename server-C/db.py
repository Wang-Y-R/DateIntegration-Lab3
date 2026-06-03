"""系统 C 数据库访问层（hw4 提交表结构 + 集成辅助表）。"""

from __future__ import annotations

import random
from typing import Any

import pymysql

from db_schema import (
    COLLEGE_C,
    COLLEGE_DEPARTMENT,
    CREATE_COURSE,
    CREATE_SC,
    CREATE_STUDENT,
    DEPRECATED_INTEGRATION_TABLES,
    DEPT_NO,
    GROUP_NO,
    INTEGRATION_DDL,
    LEGACY_TABLES,
    SUBMISSION_PRIMARY_KEYS,
)

TERM = "2025-2026-2"
MAX_STUDENT_COURSES = 5
DROPPED_SCORE = "-1"


def infer_college_from_id(entity_id: str) -> str:
    cid = (entity_id or "").strip().upper()
    if cid.startswith("A"):
        return "A"
    if cid.startswith("B"):
        return "B"
    if cid.startswith("C"):
        return "C"
    return "UNKNOWN"


def is_local_student(student_id: str) -> bool:
    return infer_college_from_id(student_id) == COLLEGE_C


def is_local_course(course_id: str) -> bool:
    return infer_college_from_id(course_id) == COLLEGE_C


def is_sc_score_editable(student_id: str, course_id: str) -> bool:
    """本院 admin 可录入/修改成绩的选课：本院课（本院生选本院课 + 外院生选本院课）。"""
    del student_id
    return is_local_course(course_id)


def course_dept_no(course_id: str) -> str:
    """sc.dept_no 表示课程所属院系，由 course_id 前缀推断。"""
    college = infer_college_from_id(course_id)
    return college if college != "UNKNOWN" else COLLEGE_C


class Database:
    def __init__(self, config: dict[str, Any]):
        self.config = {**config, "cursorclass": pymysql.cursors.DictCursor}

    def connect(self):
        return pymysql.connect(**self.config)

    def execute(self, sql, params=None, fetch=False, many=False):
        with self.connect() as conn:
            with conn.cursor() as cur:
                if many:
                    cur.executemany(sql, params)
                else:
                    cur.execute(sql, params)
                return cur.fetchall() if fetch else cur.rowcount

    def _scope(self) -> tuple[str, str]:
        return DEPT_NO, GROUP_NO

    def _legacy_scope_sql(self) -> str:
        return "dept_no=%s AND group_no=%s"

    def _sc_system_scope_sql(self) -> str:
        """系统 C 相关的 sc 记录：本院学生选课 + 外院学生选本院课。"""
        return "group_no=%s AND (student_id LIKE 'C%%' OR dept_no=%s)"

    def _sc_system_scope_params(self) -> tuple[str, str]:
        dept, group = self._scope()
        return group, dept

    def _course_catalog_scope_sql(self) -> str:
        """本院全部课程 + 外院 share_flag=Y 的共享课（不含外院未共享课）。"""
        return (
            "group_no=%s AND ("
            "(dept_no=%s AND course_id LIKE 'C%%') "
            "OR (course_id NOT LIKE 'C%%' AND share_flag='Y')"
            ")"
        )

    def _imported_shared_scope_sql(self) -> str:
        return "group_no=%s AND course_id NOT LIKE 'C%%' AND share_flag='Y'"

    def _course_catalog_scope_params(self) -> tuple[str, str]:
        dept, group = self._scope()
        return group, dept

    def drop_legacy_tables(self):
        for table in LEGACY_TABLES:
            self.execute(f"DROP TABLE IF EXISTS {table}")

    def _primary_key_columns(self, table: str) -> list[str]:
        rows = self.execute(
            "SELECT COLUMN_NAME FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND INDEX_NAME='PRIMARY' "
            "ORDER BY SEQ_IN_INDEX",
            (self.config["database"], table),
            fetch=True,
        )
        return [r["COLUMN_NAME"] for r in rows]

    def repair_submission_primary_keys(self):
        """修正 hw4 提交表主键为 (业务键, group_no, dept_no)，避免外院课程导入覆盖他院记录。"""
        for table, cols in SUBMISSION_PRIMARY_KEYS.items():
            if not self._table_exists(table):
                continue
            expected = list(cols)
            if self._primary_key_columns(table) == expected:
                continue
            col_list = ", ".join(cols)
            self.execute(f"ALTER TABLE {table} DROP PRIMARY KEY, ADD PRIMARY KEY ({col_list})")

    def repair_schema(self):
        """清理旧版 c_* 表；迁移并删除已废弃的集成辅助表。"""
        self.drop_legacy_tables()
        self.repair_submission_primary_keys()
        self.migrate_and_drop_integration_tables()
        self.normalize_sc_dept_no()
        self.normalize_imported_course_dept_no()
        self.cleanup_sc_duplicates()
        self.normalize_student_departments()

    def normalize_sc_dept_no(self):
        """sc.dept_no 与 course_id 所属院系对齐（外院课应为 A/B，本院课为 C）。"""
        _, group = self._scope()
        for prefix, college in (("A", "A"), ("B", "B"), ("C", COLLEGE_C)):
            self.execute(
                "UPDATE sc SET dept_no=%s WHERE group_no=%s AND course_id LIKE %s AND dept_no<>%s",
                (college, group, f"{prefix}%", college),
            )

    def normalize_imported_course_dept_no(self):
        """外院导入课程 course.dept_no 应对齐 course_id 所属院系（A/B，而非本院 C）。"""
        dept, group = self._scope()
        wrong = self.execute(
            "SELECT course_id FROM course WHERE group_no=%s AND dept_no=%s AND course_id NOT LIKE 'C%%'",
            (group, dept),
            fetch=True,
        )
        for row in wrong:
            cid = row["course_id"]
            correct = course_dept_no(cid)
            if correct == dept:
                continue
            if self.execute(
                "SELECT 1 AS ok FROM course WHERE course_id=%s AND group_no=%s AND dept_no=%s",
                (cid, group, correct),
                fetch=True,
            ):
                self.execute(
                    "DELETE FROM course WHERE course_id=%s AND group_no=%s AND dept_no=%s",
                    (cid, group, dept),
                )
            else:
                self.execute(
                    "UPDATE course SET dept_no=%s WHERE course_id=%s AND group_no=%s AND dept_no=%s",
                    (correct, cid, group, dept),
                )

    def migrate_and_drop_integration_tables(self):
        """将旧集成辅助表数据迁入 sc/course，然后删除辅助表。"""
        dept, group = self._scope()
        if self._table_exists("imported_shared_courses"):
            rows = self.execute(
                "SELECT source_college, course_id, course_name, credit, class_hours, teacher_name, location "
                "FROM imported_shared_courses WHERE dept_no=%s AND group_no=%s",
                (dept, group),
                fetch=True,
            )
            for row in rows:
                self._upsert_external_course_row(row)
        if self._table_exists("cross_college_selections"):
            rows = self.execute(
                "SELECT student_id, course_id FROM cross_college_selections "
                "WHERE dept_no=%s AND group_no=%s AND status<>'已退选'",
                (dept, group),
                fetch=True,
            )
            for row in rows:
                self._upsert_sc_row(row["course_id"], row["student_id"], "")
        if self._table_exists("inbound_cross_enrollments"):
            rows = self.execute(
                "SELECT student_id, course_id FROM inbound_cross_enrollments "
                "WHERE dept_no=%s AND group_no=%s AND status<>'已退选'",
                (dept, group),
                fetch=True,
            )
            for row in rows:
                self._upsert_sc_row(row["course_id"], row["student_id"], "")
        for table in DEPRECATED_INTEGRATION_TABLES:
            self.execute(f"DROP TABLE IF EXISTS {table}")

    def _upsert_external_course_row(self, row: dict):
        course_id = str(row.get("course_id", "")).strip()
        if not course_id:
            return
        _, group = self._scope()
        course_dept = course_dept_no(course_id)
        class_h = str(row.get("class_hours", "16"))
        name = str(row.get("course_name", course_id))[:16]
        teacher = str(row.get("teacher_name", ""))[:20]
        location = str(row.get("location", ""))[:20]
        self.execute(
            "INSERT INTO course (course_id, course_name, credit, teacher_name, location, share_flag, "
            "class_hours, practice_hours, group_no, dept_no) "
            "VALUES (%s, %s, %s, %s, %s, 'Y', %s, '', %s, %s) "
            "ON DUPLICATE KEY UPDATE course_name=VALUES(course_name), credit=VALUES(credit), "
            "teacher_name=VALUES(teacher_name), location=VALUES(location), "
            "class_hours=VALUES(class_hours), group_no=VALUES(group_no), dept_no=VALUES(dept_no)",
            (
                course_id,
                name,
                str(row.get("credit", "0"))[:2],
                teacher,
                location,
                class_h[:10],
                group,
                course_dept,
            ),
        )

    def _upsert_sc_row(self, course_id: str, student_id: str, score: str = ""):
        _, group = self._scope()
        sc_dept = course_dept_no(course_id)
        self.execute(
            "INSERT INTO sc (course_id, student_id, score, group_no, dept_no) "
            "VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE score=VALUES(score)",
            (course_id, student_id, score, group, sc_dept),
        )

    def cleanup_sc_duplicates(self):
        """清理 sc 表中同一学生同一课程的重复记录（保留一条有效选课）。"""
        group, dept = self._sc_system_scope_params()
        dup_groups = self.execute(
            "SELECT course_id, student_id, dept_no, COUNT(*) AS cnt "
            f"FROM sc WHERE {self._sc_system_scope_sql()} "
            "GROUP BY course_id, student_id, dept_no, group_no HAVING cnt > 1",
            (group, dept),
            fetch=True,
        )
        for row in dup_groups:
            course_id, student_id, sc_dept = row["course_id"], row["student_id"], row["dept_no"]
            self.execute(
                "DELETE FROM sc WHERE course_id=%s AND student_id=%s AND dept_no=%s AND group_no=%s AND score=%s",
                (course_id, student_id, sc_dept, group, DROPPED_SCORE),
            )
            while True:
                remaining = self.execute(
                    "SELECT COUNT(*) AS total FROM sc "
                    "WHERE course_id=%s AND student_id=%s AND dept_no=%s AND group_no=%s",
                    (course_id, student_id, sc_dept, group),
                    fetch=True,
                )[0]["total"]
                if remaining <= 1:
                    break
                self.execute(
                    "DELETE FROM sc WHERE course_id=%s AND student_id=%s AND dept_no=%s AND group_no=%s LIMIT 1",
                    (course_id, student_id, sc_dept, group),
                )

    def normalize_student_departments(self):
        """本院学生院系名称统一为院系C（department 字段）。"""
        dept, group = self._scope()
        self.execute(
            "UPDATE student SET department=%s WHERE dept_no=%s AND group_no=%s AND department<>%s",
            (COLLEGE_DEPARTMENT, dept, group, COLLEGE_DEPARTMENT),
        )

    def _table_exists(self, table: str) -> bool:
        rows = self.execute(
            "SELECT COUNT(*) AS total FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
            (self.config["database"], table),
            fetch=True,
        )
        return rows[0]["total"] > 0

    def _column_exists(self, table: str, column: str) -> bool:
        rows = self.execute(
            "SELECT COUNT(*) AS total FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
            (self.config["database"], table, column),
            fetch=True,
        )
        return rows[0]["total"] > 0

    def initialize_schema(self):
        self.repair_schema()
        for ddl in (CREATE_STUDENT, CREATE_COURSE, CREATE_SC, *INTEGRATION_DDL):
            self.execute(ddl)

    def seed_base_data(self):
        dept, group = self._scope()
        scope = self._legacy_scope_sql()
        for table in ("sc", "student"):
            self.execute(f"DELETE FROM {table} WHERE {scope}", (dept, group))
        self.execute(
            f"DELETE FROM course WHERE {self._course_catalog_scope_sql()}",
            self._course_catalog_scope_params(),
        )

        admin_row = (
            "CADMIN000001",
            "管理员",
            "男",
            COLLEGE_DEPARTMENT,
            "admin",
            "123456",
            group,
            dept,
        )
        self.execute(
            "INSERT INTO student (student_id, student_name, gender, department, account, password, group_no, dept_no) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            admin_row,
        )

        students = []
        for i in range(1, 51):
            sid = f"C2023{i:05d}"
            students.append(
                (
                    sid,
                    f"学生{i:02d}",
                    "男" if i % 2 else "女",
                    COLLEGE_DEPARTMENT,
                    sid[-10:],
                    f"{100000 + i}"[-6:],
                    group,
                    dept,
                )
            )
        self.execute(
            "INSERT INTO student (student_id, student_name, gender, department, account, password, group_no, dept_no) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            students,
            many=True,
        )

        names = [
            "数据库",
            "数据结构",
            "计网",
            "操作系统",
            "Python",
            "机器学习",
            "Web开发",
            "信息系统",
            "软件测试",
            "数据集成",
        ]
        teachers = ["王老师", "李老师", "赵老师", "陈老师", "孙老师"]
        places = ["一教101", "一教202", "二教305", "实验楼201", "实验楼403"]
        courses = []
        for i, name in enumerate(names, 1):
            credit = str(2 + i % 3)
            class_h = str(16 + i)
            practice_h = str(i % 4)
            courses.append(
                (
                    f"C{i:07d}",
                    name,
                    credit,
                    teachers[(i - 1) % 5],
                    places[(i - 1) % 5],
                    "Y" if i <= 6 else "N",
                    class_h,
                    practice_h,
                    group,
                    dept,
                )
            )
        self.execute(
            "INSERT INTO course (course_id, course_name, credit, teacher_name, location, share_flag, "
            "class_hours, practice_hours, group_no, dept_no) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            courses,
            many=True,
        )

        course_ids = [c[0] for c in courses]
        picks = []
        for i, stu in enumerate(students, 1):
            random.seed(i)
            for j, cid in enumerate(random.sample(course_ids, 5)):
                # 前 15 名学生填入示例成绩，其余留空表示未录入
                if i <= 15:
                    score = str(60 + (i + j) % 41)
                else:
                    score = ""
                picks.append((cid, stu[0], score, group, course_dept_no(cid)))
        self.execute(
            "INSERT INTO sc (course_id, student_id, score, group_no, dept_no) VALUES (%s, %s, %s, %s, %s)",
            picks,
            many=True,
        )

    def seed_sc_from_existing(self) -> int:
        """当 student/course 已有数据但 sc 为空时，按规则补全选课示例。"""
        dept, group = self._scope()
        students = self.execute(
            "SELECT student_id FROM student WHERE dept_no=%s AND group_no=%s AND account<>'admin' ORDER BY student_id",
            (dept, group),
            fetch=True,
        )
        courses = self.execute(
            "SELECT course_id FROM course WHERE dept_no=%s AND group_no=%s AND course_id LIKE 'C%%' ORDER BY course_id",
            (dept, group),
            fetch=True,
        )
        if not students or not courses:
            return 0

        self.execute(
            f"DELETE FROM sc WHERE {self._sc_system_scope_sql()}",
            (group, dept),
        )
        course_ids = [r["course_id"] for r in courses]
        pick_n = min(5, len(course_ids))
        picks = []
        for i, row in enumerate(students, 1):
            random.seed(i)
            for j, cid in enumerate(random.sample(course_ids, pick_n)):
                score = str(60 + (i + j) % 41) if i <= 15 else ""
                picks.append((cid, row["student_id"], score, group, course_dept_no(cid)))
        if picks:
            self.execute(
                "INSERT INTO sc (course_id, student_id, score, group_no, dept_no) VALUES (%s, %s, %s, %s, %s)",
                picks,
                many=True,
            )
        return len(picks)

    def ensure_sc_sample_data(self) -> int:
        """若本院有学生/课程但 sc 为空，则自动补全。"""
        dept, group = self._scope()
        student_cnt = self.execute(
            "SELECT COUNT(*) AS total FROM student WHERE dept_no=%s AND group_no=%s AND account<>'admin'",
            (dept, group),
            fetch=True,
        )[0]["total"]
        course_cnt = self.execute(
            "SELECT COUNT(*) AS total FROM course WHERE dept_no=%s AND group_no=%s",
            (dept, group),
            fetch=True,
        )[0]["total"]
        sc_cnt = self.count_sc_records()
        self.cleanup_sc_duplicates()
        if student_cnt > 0 and course_cnt > 0 and sc_cnt == 0:
            return self.seed_sc_from_existing()
        return sc_cnt

    def validate_login(self, acc: str, passwd: str):
        dept, group = self._scope()
        rows = self.execute(
            "SELECT student_id, student_name, account FROM student "
            "WHERE (account=%s OR student_id=%s) AND password=%s AND dept_no=%s AND group_no=%s",
            (acc, acc, passwd, dept, group),
            fetch=True,
        )
        if not rows:
            return None
        row = rows[0]
        role = "admin" if row["account"] == "admin" else "student"
        return {
            "account": row["student_id"] if role == "student" else row["account"],
            "student_id": row["student_id"],
            "role": role,
            "name": row["student_name"],
        }

    def has_initialized_users(self) -> bool:
        dept, group = self._scope()
        return (
            self.execute(
                "SELECT COUNT(*) AS total FROM student WHERE dept_no=%s AND group_no=%s",
                (dept, group),
                fetch=True,
            )[0]["total"]
            > 0
        )

    def get_student_profile(self, student_id: str):
        dept, group = self._scope()
        rows = self.execute(
            "SELECT student_id, student_name, gender, department, account, password "
            "FROM student WHERE student_id=%s AND dept_no=%s AND group_no=%s",
            (student_id, dept, group),
            fetch=True,
        )
        return rows[0] if rows else None

    def update_student_profile(self, student_id, student_name, gender, department, password):
        dept, group = self._scope()
        return self.execute(
            "UPDATE student SET student_name=%s, gender=%s, department=%s, password=%s "
            "WHERE student_id=%s AND dept_no=%s AND group_no=%s",
            (student_name, gender, COLLEGE_DEPARTMENT, password, student_id, dept, group),
        )

    def get_students(self):
        dept, group = self._scope()
        return self.execute(
            "SELECT student_id, student_name, gender, department, account, password, group_no, dept_no "
            "FROM student WHERE dept_no=%s AND group_no=%s ORDER BY student_id",
            (dept, group),
            fetch=True,
        )

    def get_courses(self):
        group, dept = self._course_catalog_scope_params()
        return self.execute(
            "SELECT course_id, course_name, credit, teacher_name, location, share_flag, "
            "class_hours, practice_hours, group_no, dept_no "
            f"FROM course WHERE {self._course_catalog_scope_sql()} "
            "ORDER BY CASE WHEN course_id LIKE 'C%%' THEN 0 ELSE 1 END, course_id",
            (group, dept),
            fetch=True,
        )

    def set_course_share_flag(self, course_id: str, share_flag: str):
        """设置本院课程是否对外共享（Y=外院可选，N=仅本院可选）。"""
        if not is_local_course(course_id):
            raise ValueError("只能修改本院课程（C 开头）的 share_flag，外院导入课程不可修改。")
        flag = str(share_flag).upper()
        if flag not in ("Y", "N"):
            raise ValueError("share_flag 只能为 Y 或 N。")
        dept, group = self._scope()
        updated = self.execute(
            "UPDATE course SET share_flag=%s WHERE course_id=%s AND dept_no=%s AND group_no=%s",
            (flag, course_id, dept, group),
        )
        if updated == 0:
            raise ValueError("课程不存在。")

    def get_shared_courses(self):
        """对外共享课程（share_flag=Y），供集成服务器/外院选课。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT course_id, course_name, credit, class_hours, practice_hours, teacher_name, location "
            "FROM course WHERE share_flag='Y' AND dept_no=%s AND group_no=%s AND course_id LIKE 'C%%' ORDER BY course_id",
            (dept, group),
            fetch=True,
        )

    def get_local_selectable_courses(self):
        """本院学生可选的全部本院课程（与 share_flag 无关）。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT course_id, course_name, credit, class_hours, practice_hours, teacher_name, location "
            "FROM course WHERE dept_no=%s AND group_no=%s AND course_id LIKE 'C%%' ORDER BY course_id",
            (dept, group),
            fetch=True,
        )

    def count_sc_records(self) -> int:
        group, dept = self._sc_system_scope_params()
        return self.execute(
            f"SELECT COUNT(*) AS total FROM sc WHERE {self._sc_system_scope_sql()}",
            (group, dept),
            fetch=True,
        )[0]["total"]

    def count_student_local_courses(self, student_id: str) -> int:
        """本院已选课程数（计入选课上限）：本院学生 + 本院课程。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT COUNT(*) AS total FROM sc WHERE student_id=%s AND dept_no=%s AND group_no=%s "
            "AND score<>%s AND course_id LIKE 'C%%'",
            (student_id, dept, group, DROPPED_SCORE),
            fetch=True,
        )[0]["total"]

    def count_student_cross_courses(self, student_id: str) -> int:
        """跨院已选课程数（不计入本院选课上限）。"""
        _, group = self._scope()
        return self.execute(
            "SELECT COUNT(*) AS total FROM sc WHERE student_id=%s AND group_no=%s "
            "AND score<>%s AND course_id NOT LIKE 'C%%'",
            (student_id, group, DROPPED_SCORE),
            fetch=True,
        )[0]["total"]

    def count_student_active_courses(self, student_id: str) -> int:
        return self.count_student_local_courses(student_id) + self.count_student_cross_courses(student_id)

    def get_selectable_imported_courses(self, student_id: str):
        """学生可选的已导入外院共享课程（排除已选中的跨院课）。"""
        dept, group = self._scope()
        refs = self.get_imported_shared_course_refs()
        enrolled = self.execute(
            "SELECT course_id FROM sc WHERE student_id=%s AND group_no=%s AND score<>%s",
            (student_id, group, DROPPED_SCORE),
            fetch=True,
        )
        enrolled_ids = {r["course_id"] for r in enrolled}
        return [r for r in refs if r["course_id"] not in enrolled_ids]

    def add_local_course_for_student(self, student_id: str, course_id: str):
        _, group = self._scope()
        sc_dept = course_dept_no(course_id)
        self.execute(
            "DELETE FROM sc WHERE student_id=%s AND course_id=%s AND dept_no=%s AND group_no=%s",
            (student_id, course_id, sc_dept, group),
        )
        self.execute(
            "INSERT INTO sc (course_id, student_id, score, group_no, dept_no) VALUES (%s, %s, %s, %s, %s)",
            (course_id, student_id, "", group, sc_dept),
        )

    def get_sc_submission_rows(self):
        """本院选课 sc 提交字段（不含已退选记录）。"""
        group, dept = self._sc_system_scope_params()
        return self.execute(
            "SELECT course_id, student_id, score, group_no, dept_no "
            f"FROM sc WHERE {self._sc_system_scope_sql()} AND score<>%s "
            "ORDER BY student_id, course_id",
            (group, dept, DROPPED_SCORE),
            fetch=True,
        )

    def set_sc_score(self, student_id: str, course_id: str, score: str):
        """修改选课成绩（仅本院课程：本院生选本院课、外院生选本院课）。"""
        if not is_sc_score_editable(student_id, course_id):
            raise ValueError("本院学生选修外院课程的成绩由开课院系管理，本院无法修改。")
        raw = str(score).strip()
        _, group = self._scope()
        sc_dept = course_dept_no(course_id)
        if raw == DROPPED_SCORE:
            deleted = self.execute(
                "DELETE FROM sc WHERE student_id=%s AND course_id=%s AND dept_no=%s AND group_no=%s",
                (student_id, course_id, sc_dept, group),
            )
            if deleted == 0:
                raise ValueError("未找到对应选课记录。")
            return
        if raw == "":
            normalized = ""
        elif raw.isdigit():
            value = int(raw)
            if value < 0 or value > 100:
                raise ValueError("成绩须在 0-100 之间。")
            normalized = str(value)
        else:
            raise ValueError("成绩须为 0-100 的数字；留空表示未录入，-1 表示退选并删除记录。")
        if len(normalized) > 3:
            raise ValueError("成绩最多 3 位字符。")
        self.cleanup_sc_duplicates()
        updated = self.execute(
            "UPDATE sc SET score=%s WHERE student_id=%s AND course_id=%s AND dept_no=%s AND group_no=%s",
            (normalized, student_id, course_id, sc_dept, group),
        )
        if updated == 0:
            raise ValueError("未找到对应选课记录。")

    def get_student_enrollments(self, student_id: str):
        """指定学生的全部选课（本院 + 跨院，均在 sc 表）。"""
        _, group = self._scope()
        rows = self.execute(
            "SELECT sc.course_id, COALESCE(c.course_name, '') AS course_name, sc.score "
            "FROM sc sc "
            "LEFT JOIN course c ON c.course_id=sc.course_id AND c.group_no=sc.group_no AND c.dept_no=sc.dept_no "
            "WHERE sc.student_id=%s AND sc.group_no=%s AND sc.score<>%s "
            "ORDER BY sc.course_id",
            (student_id, group, DROPPED_SCORE),
            fetch=True,
        )
        result = []
        for row in rows:
            cid = row["course_id"]
            college = COLLEGE_C if is_local_course(cid) else infer_college_from_id(cid)
            result.append(
                {
                    "course_id": cid,
                    "course_name": row["course_name"],
                    "score": row["score"],
                    "source_college": college,
                    "status": "已选",
                }
            )
        return result

    def get_enrollments(self):
        """全部选课记录，供统计等场景使用。"""
        group, dept = self._sc_system_scope_params()
        rows = self.execute(
            "SELECT sc.course_id, sc.student_id, s.student_name, c.course_name, sc.score, "
            "sc.group_no, sc.dept_no "
            "FROM sc sc "
            "LEFT JOIN student s ON s.student_id=sc.student_id AND s.dept_no=%s AND s.group_no=sc.group_no "
            "LEFT JOIN course c ON c.course_id=sc.course_id AND c.dept_no=sc.dept_no AND c.group_no=sc.group_no "
            f"WHERE {self._sc_system_scope_sql()} AND sc.score<>%s "
            "ORDER BY sc.student_id, sc.course_id",
            (dept, group, dept, DROPPED_SCORE),
            fetch=True,
        )
        result = []
        for row in rows:
            cid, sid = row["course_id"], row["student_id"]
            local_student = is_local_student(sid)
            local_course = is_local_course(cid)
            if local_student and local_course:
                enroll_type, college = "本院", COLLEGE_C
            elif local_student:
                enroll_type, college = "跨院", infer_college_from_id(cid)
            else:
                enroll_type, college = "外院 inbound", infer_college_from_id(sid)
            result.append(
                {
                    **row,
                    "enroll_type": enroll_type,
                    "source_college": college,
                    "term_name": TERM,
                    "status": "已选",
                }
            )
        return result

    def get_imported_shared_courses(self):
        """已导入/可见的外院共享课程（share_flag=Y）。"""
        _, group = self._scope()
        return self.execute(
            "SELECT course_id, course_name, credit, teacher_name, location, "
            "share_flag, class_hours, practice_hours, group_no, dept_no "
            f"FROM course WHERE {self._imported_shared_scope_sql()} "
            "ORDER BY course_id",
            (group,),
            fetch=True,
        )

    def get_imported_shared_course_refs(self):
        """选课对话框用：来源学院 + 课程编号 + 名称。"""
        _, group = self._scope()
        rows = self.execute(
            f"SELECT course_id, course_name FROM course WHERE {self._imported_shared_scope_sql()} "
            "ORDER BY course_id",
            (group,),
            fetch=True,
        )
        return [
            {
                "source_college": infer_college_from_id(r["course_id"]),
                "course_id": r["course_id"],
                "course_name": r["course_name"],
            }
            for r in rows
        ]

    def get_inbound_cross_enrollments(self):
        """外院学生选修本院课程（sc 表：外院学号 + 本院课程）。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT course_id, student_id, score, group_no, dept_no "
            "FROM sc WHERE dept_no=%s AND group_no=%s AND score<>%s "
            "AND student_id NOT LIKE 'C%%' AND course_id LIKE 'C%%' "
            "ORDER BY student_id, course_id",
            (dept, group, DROPPED_SCORE),
            fetch=True,
        )

    def get_outbound_cross_enrollments(self):
        """本院学生选修外院课程（sc 表）。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT sc.course_id, sc.student_id, s.student_name, c.course_name, sc.score "
            "FROM sc sc "
            "LEFT JOIN student s ON s.student_id=sc.student_id AND s.dept_no=%s AND s.group_no=sc.group_no "
            "LEFT JOIN course c ON c.course_id=sc.course_id AND c.dept_no=sc.dept_no AND c.group_no=sc.group_no "
            "WHERE sc.group_no=%s AND sc.score<>%s "
            "AND sc.student_id LIKE 'C%%' AND sc.course_id NOT LIKE 'C%%' "
            "ORDER BY sc.student_id, sc.course_id",
            (dept, group, DROPPED_SCORE),
            fetch=True,
        )

    def import_shared_courses(self, rows, xml_path: str):
        del xml_path
        imported = 0
        for row in rows:
            course_id = str(row.get("course_id", "")).strip()
            if not course_id or is_local_course(course_id):
                continue
            self._upsert_external_course_row(row)
            imported += 1
        if not imported and rows:
            raise ValueError("未写入任何外院课程（请确认 course_id 以 A/B 等外院前缀开头）。")
        return imported

    def import_inbound_selections(self, rows, xml_path: str):
        del xml_path
        _, group = self._scope()
        for row in rows:
            sc_dept = course_dept_no(row["course_id"])
            if str(row.get("status", "已选")) == "已退选":
                self.execute(
                    "DELETE FROM sc WHERE student_id=%s AND course_id=%s AND dept_no=%s AND group_no=%s",
                    (row["student_id"], row["course_id"], sc_dept, group),
                )
            else:
                self._upsert_sc_row(row["course_id"], row["student_id"], "")

    def add_cross_college_enrollment(self, student_id, source_college, course_id, term_name):
        del source_college, term_name
        dept, group = self._scope()
        if not self.execute(
            "SELECT student_id FROM student WHERE student_id=%s AND dept_no=%s AND group_no=%s",
            (student_id, dept, group),
            fetch=True,
        ):
            raise ValueError("学生不存在。")
        course_row = self.execute(
            "SELECT course_id, share_flag FROM course WHERE course_id=%s AND dept_no=%s AND group_no=%s",
            (course_id, course_dept_no(course_id), group),
            fetch=True,
        )
        if not course_row:
            raise ValueError("共享课程不存在，请先导入外院共享课程。")
        if not is_local_course(course_id) and str(course_row[0].get("share_flag", "")).upper() != "Y":
            raise ValueError("该外院课程未对外共享，无法选修。")
        self._upsert_sc_row(course_id, student_id, "")

    def drop_enrollment(self, student_id, course_id, source_college, term_name):
        del source_college, term_name
        _, group = self._scope()
        sc_dept = course_dept_no(course_id)
        count = self.execute(
            "DELETE FROM sc WHERE student_id=%s AND course_id=%s AND dept_no=%s AND group_no=%s",
            (student_id, course_id, sc_dept, group),
        )
        if count == 0:
            raise ValueError("未找到对应选课记录。")

    @staticmethod
    def get_student_course_limit(student_id: str) -> int:
        return MAX_STUDENT_COURSES

    def check_student_course_limit(self, student_id: str):
        current = self.count_student_local_courses(student_id)
        limit = self.get_student_course_limit(student_id)
        if current >= limit:
            raise ValueError(f"本院课程最多只能选择 {limit} 门。")

    def get_local_stats(self):
        dept, group = self._scope()
        students = self.execute(
            "SELECT COUNT(*) AS total FROM student WHERE dept_no=%s AND group_no=%s AND account<>'admin'",
            (dept, group),
            fetch=True,
        )[0]["total"]
        courses = self.execute(
            f"SELECT COUNT(*) AS total FROM course WHERE {self._course_catalog_scope_sql()}",
            self._course_catalog_scope_params(),
            fetch=True,
        )[0]["total"]
        local_enroll = self.execute(
            f"SELECT COUNT(*) AS total FROM sc WHERE {self._sc_system_scope_sql()} AND score<>%s",
            (*self._sc_system_scope_params(), DROPPED_SCORE),
            fetch=True,
        )[0]["total"]
        return {"students": students, "courses": courses, "enrollments": local_enroll}
