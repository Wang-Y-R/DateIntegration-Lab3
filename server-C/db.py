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
    DEPT_NO,
    GROUP_NO,
    INTEGRATION_DDL,
    LEGACY_TABLES,
)

TERM = "2025-2026-2"
MAX_STUDENT_COURSES = 5
DROPPED_SCORE = "-1"


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

    def drop_legacy_tables(self):
        for table in LEGACY_TABLES:
            self.execute(f"DROP TABLE IF EXISTS {table}")

    def repair_schema(self):
        """清理旧版 c_* 表；若集成辅助表缺列则重建（仅本组）。"""
        self.drop_legacy_tables()
        dept, group = self._scope()
        for table in ("imported_shared_courses", "cross_college_selections", "inbound_cross_enrollments"):
            if not self._table_exists(table):
                continue
            if table == "imported_shared_courses" and not self._column_exists(table, "course_id"):
                self.execute(f"DELETE FROM {table} WHERE dept_no=%s AND group_no=%s", (dept, group))
                self.execute(f"DROP TABLE IF EXISTS {table}")
            elif table == "cross_college_selections" and not self._column_exists(table, "student_id"):
                self.execute(f"DELETE FROM {table} WHERE dept_no=%s AND group_no=%s", (dept, group))
                self.execute(f"DROP TABLE IF EXISTS {table}")
            elif table == "inbound_cross_enrollments" and not self._column_exists(table, "student_id"):
                self.execute(f"DELETE FROM {table} WHERE dept_no=%s AND group_no=%s", (dept, group))
                self.execute(f"DROP TABLE IF EXISTS {table}")
        self.cleanup_sc_duplicates()
        self.normalize_student_departments()

    def cleanup_sc_duplicates(self):
        """清理 sc 表中同一学生同一课程的重复记录（保留一条有效选课）。"""
        dept, group = self._scope()
        dup_groups = self.execute(
            "SELECT course_id, student_id, COUNT(*) AS cnt "
            "FROM sc WHERE dept_no=%s AND group_no=%s "
            "GROUP BY course_id, student_id, group_no, dept_no HAVING cnt > 1",
            (dept, group),
            fetch=True,
        )
        for row in dup_groups:
            course_id, student_id = row["course_id"], row["student_id"]
            self.execute(
                "DELETE FROM sc WHERE course_id=%s AND student_id=%s AND dept_no=%s AND group_no=%s AND score=%s",
                (course_id, student_id, dept, group, DROPPED_SCORE),
            )
            while True:
                remaining = self.execute(
                    "SELECT COUNT(*) AS total FROM sc "
                    "WHERE course_id=%s AND student_id=%s AND dept_no=%s AND group_no=%s",
                    (course_id, student_id, dept, group),
                    fetch=True,
                )[0]["total"]
                if remaining <= 1:
                    break
                self.execute(
                    "DELETE FROM sc WHERE course_id=%s AND student_id=%s AND dept_no=%s AND group_no=%s LIMIT 1",
                    (course_id, student_id, dept, group),
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
        for table in (
            "inbound_cross_enrollments",
            "cross_college_selections",
            "imported_shared_courses",
            "sc",
            "course",
            "student",
        ):
            self.execute(f"DELETE FROM {table} WHERE {scope}", (dept, group))

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
                picks.append((cid, stu[0], score, group, dept))
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
            "SELECT course_id FROM course WHERE dept_no=%s AND group_no=%s ORDER BY course_id",
            (dept, group),
            fetch=True,
        )
        if not students or not courses:
            return 0

        self.execute("DELETE FROM sc WHERE dept_no=%s AND group_no=%s", (dept, group))
        course_ids = [r["course_id"] for r in courses]
        pick_n = min(5, len(course_ids))
        picks = []
        for i, row in enumerate(students, 1):
            random.seed(i)
            for j, cid in enumerate(random.sample(course_ids, pick_n)):
                score = str(60 + (i + j) % 41) if i <= 15 else ""
                picks.append((cid, row["student_id"], score, group, dept))
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
        dept, group = self._scope()
        return self.execute(
            "SELECT course_id, course_name, credit, teacher_name, location, share_flag, "
            "class_hours, practice_hours, group_no, dept_no "
            "FROM course WHERE dept_no=%s AND group_no=%s ORDER BY course_id",
            (dept, group),
            fetch=True,
        )

    def set_course_share_flag(self, course_id: str, share_flag: str):
        """设置课程是否对外共享（Y=外院可选，N=仅本院可选）。"""
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
            "FROM course WHERE share_flag='Y' AND dept_no=%s AND group_no=%s ORDER BY course_id",
            (dept, group),
            fetch=True,
        )

    def get_local_selectable_courses(self):
        """本院学生可选的全部本院课程（与 share_flag 无关）。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT course_id, course_name, credit, class_hours, practice_hours, teacher_name, location "
            "FROM course WHERE dept_no=%s AND group_no=%s ORDER BY course_id",
            (dept, group),
            fetch=True,
        )

    def count_sc_records(self) -> int:
        dept, group = self._scope()
        return self.execute(
            "SELECT COUNT(*) AS total FROM sc WHERE dept_no=%s AND group_no=%s",
            (dept, group),
            fetch=True,
        )[0]["total"]

    def count_student_local_courses(self, student_id: str) -> int:
        """本院已选课程数（计入选课上限）。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT COUNT(*) AS total FROM sc WHERE student_id=%s AND dept_no=%s AND group_no=%s "
            "AND score<>%s",
            (student_id, dept, group, DROPPED_SCORE),
            fetch=True,
        )[0]["total"]

    def count_student_cross_courses(self, student_id: str) -> int:
        """跨院已选课程数（不计入本院选课上限）。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT COUNT(*) AS total FROM cross_college_selections "
            "WHERE student_id=%s AND dept_no=%s AND group_no=%s AND status<>'已退选'",
            (student_id, dept, group),
            fetch=True,
        )[0]["total"]

    def count_student_active_courses(self, student_id: str) -> int:
        return self.count_student_local_courses(student_id) + self.count_student_cross_courses(student_id)

    def get_selectable_imported_courses(self, student_id: str):
        """学生可选的已导入外院共享课程（排除已选中的跨院课）。"""
        dept, group = self._scope()
        refs = self.get_imported_shared_course_refs()
        enrolled = self.execute(
            "SELECT source_college, course_id FROM cross_college_selections "
            "WHERE student_id=%s AND dept_no=%s AND group_no=%s AND status<>'已退选'",
            (student_id, dept, group),
            fetch=True,
        )
        enrolled_keys = {(r["source_college"], r["course_id"]) for r in enrolled}
        return [r for r in refs if (r["source_college"], r["course_id"]) not in enrolled_keys]

    def add_local_course_for_student(self, student_id: str, course_id: str):
        dept, group = self._scope()
        self.execute(
            "DELETE FROM sc WHERE student_id=%s AND course_id=%s AND dept_no=%s AND group_no=%s",
            (student_id, course_id, dept, group),
        )
        self.execute(
            "INSERT INTO sc (course_id, student_id, score, group_no, dept_no) VALUES (%s, %s, %s, %s, %s)",
            (course_id, student_id, "", group, dept),
        )

    def get_sc_submission_rows(self):
        """本院选课 sc 提交字段（不含已退选记录）。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT course_id, student_id, score, group_no, dept_no "
            "FROM sc WHERE dept_no=%s AND group_no=%s AND score<>%s "
            "ORDER BY student_id, course_id",
            (dept, group, DROPPED_SCORE),
            fetch=True,
        )

    def set_sc_score(self, student_id: str, course_id: str, score: str):
        """修改本院选课成绩。空字符串=未录入，0-100=成绩；-1 表示退选并删除记录。"""
        raw = str(score).strip()
        dept, group = self._scope()
        if raw == DROPPED_SCORE:
            deleted = self.execute(
                "DELETE FROM sc WHERE student_id=%s AND course_id=%s AND dept_no=%s AND group_no=%s",
                (student_id, course_id, dept, group),
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
            (normalized, student_id, course_id, dept, group),
        )
        if updated == 0:
            raise ValueError("未找到对应选课记录。")

    def get_student_enrollments(self, student_id: str):
        """指定学生的选课列表（本院 sc + 跨院，供学生端展示）。"""
        dept, group = self._scope()
        local_rows = self.execute(
            "SELECT sc.course_id, COALESCE(c.course_name, '') AS course_name, sc.score, "
            "%s AS source_college, "
            "CASE WHEN sc.score=%s THEN '已退选' ELSE '已选' END AS status "
            "FROM sc sc "
            "LEFT JOIN course c ON c.course_id=sc.course_id AND c.dept_no=sc.dept_no AND c.group_no=sc.group_no "
            "WHERE sc.student_id=%s AND sc.dept_no=%s AND sc.group_no=%s AND sc.score<>%s "
            "ORDER BY sc.course_id",
            (COLLEGE_C, DROPPED_SCORE, student_id, dept, group, DROPPED_SCORE),
            fetch=True,
        )
        cross_rows = ()
        try:
            cross_rows = self.execute(
                "SELECT cs.course_id, COALESCE(i.course_name, '') AS course_name, '' AS score, "
                "cs.source_college, cs.status "
                "FROM cross_college_selections cs "
                "LEFT JOIN imported_shared_courses i ON i.source_college=cs.source_college AND i.course_id=cs.course_id "
                "AND i.dept_no=cs.dept_no AND i.group_no=cs.group_no "
                "WHERE cs.student_id=%s AND cs.dept_no=%s AND cs.group_no=%s AND cs.status<>'已退选' "
                "ORDER BY cs.course_id",
                (student_id, dept, group),
                fetch=True,
            )
        except Exception:
            cross_rows = ()
        return list(local_rows) + list(cross_rows)

    def get_enrollments(self):
        """全部选课记录（本院 sc + 跨院），供统计等场景使用。"""
        dept, group = self._scope()
        local_rows = self.execute(
            "SELECT sc.course_id, sc.student_id, s.student_name, c.course_name, sc.score, "
            "sc.group_no, sc.dept_no, '本院' AS enroll_type, %s AS source_college, "
            "%s AS term_name, CASE WHEN sc.score=%s THEN '已退选' ELSE '已选' END AS status "
            "FROM sc sc "
            "LEFT JOIN student s ON s.student_id=sc.student_id AND s.dept_no=sc.dept_no AND s.group_no=sc.group_no "
            "LEFT JOIN course c ON c.course_id=sc.course_id AND c.dept_no=sc.dept_no AND c.group_no=sc.group_no "
            "WHERE sc.dept_no=%s AND sc.group_no=%s AND sc.score<>%s "
            "ORDER BY sc.student_id, sc.course_id",
            (COLLEGE_C, TERM, DROPPED_SCORE, dept, group, DROPPED_SCORE),
            fetch=True,
        )
        cross_rows = ()
        try:
            cross_rows = self.execute(
                "SELECT cs.course_id, cs.student_id, s.student_name, i.course_name, '' AS score, "
                "cs.group_no, cs.dept_no, '跨院' AS enroll_type, cs.source_college, cs.term_name, cs.status "
                "FROM cross_college_selections cs "
                "LEFT JOIN student s ON s.student_id=cs.student_id AND s.dept_no=cs.dept_no AND s.group_no=cs.group_no "
                "LEFT JOIN imported_shared_courses i ON i.source_college=cs.source_college AND i.course_id=cs.course_id "
                "AND i.dept_no=cs.dept_no AND i.group_no=cs.group_no "
                "WHERE cs.dept_no=%s AND cs.group_no=%s AND cs.status<>'已退选' "
                "ORDER BY cs.student_id, cs.course_id",
                (dept, group),
                fetch=True,
            )
        except Exception:
            cross_rows = ()
        return list(local_rows) + list(cross_rows)

    def get_imported_shared_courses(self):
        """已导入外院共享课程，按提交表 course 字段展示。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT course_id, course_name, credit, teacher_name, location, "
            "'Y' AS share_flag, class_hours, '' AS practice_hours, group_no, dept_no "
            "FROM imported_shared_courses WHERE dept_no=%s AND group_no=%s "
            "ORDER BY course_id",
            (dept, group),
            fetch=True,
        )

    def get_imported_shared_course_refs(self):
        """选课对话框用：来源学院 + 课程编号 + 名称。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT source_college, course_id, course_name "
            "FROM imported_shared_courses WHERE dept_no=%s AND group_no=%s "
            "ORDER BY source_college, course_id",
            (dept, group),
            fetch=True,
        )

    def get_inbound_cross_enrollments(self):
        """外院学生选修本院课程，按提交表 sc 字段展示。"""
        dept, group = self._scope()
        return self.execute(
            "SELECT course_id, student_id, "
            "CASE WHEN status='已退选' THEN %s ELSE '' END AS score, "
            "group_no, dept_no "
            "FROM inbound_cross_enrollments WHERE dept_no=%s AND group_no=%s "
            "ORDER BY student_id, course_id",
            (DROPPED_SCORE, dept, group),
            fetch=True,
        )

    def import_shared_courses(self, rows, xml_path: str):
        dept, group = self._scope()
        sql = (
            "INSERT INTO imported_shared_courses "
            "(source_college, course_id, course_name, credit, class_hours, teacher_name, location, xml_path, group_no, dept_no) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE course_name=VALUES(course_name), credit=VALUES(credit), "
            "class_hours=VALUES(class_hours), teacher_name=VALUES(teacher_name), location=VALUES(location), xml_path=VALUES(xml_path)"
        )
        params = [
            (
                r["source_college"],
                r["course_id"],
                r["course_name"],
                str(r.get("credit", "")),
                str(r.get("class_hours", "")),
                r.get("teacher_name", ""),
                r.get("location", ""),
                xml_path,
                group,
                dept,
            )
            for r in rows
        ]
        if params:
            self.execute(sql, params, many=True)

    def import_inbound_selections(self, rows, xml_path: str):
        dept, group = self._scope()
        sql = (
            "INSERT INTO inbound_cross_enrollments "
            "(source_college, student_id, student_name, course_id, course_name, term_name, status, xml_path, group_no, dept_no) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE student_name=VALUES(student_name), course_name=VALUES(course_name), "
            "status=VALUES(status), xml_path=VALUES(xml_path)"
        )
        params = [
            (
                r["source_college"],
                r["student_id"],
                r["student_name"],
                r["course_id"],
                r["course_name"],
                r.get("term_name", TERM),
                r.get("status", "已选"),
                xml_path,
                group,
                dept,
            )
            for r in rows
        ]
        if params:
            self.execute(sql, params, many=True)

    def add_cross_college_enrollment(self, student_id, source_college, course_id, term_name):
        dept, group = self._scope()
        if not self.execute(
            "SELECT student_id FROM student WHERE student_id=%s AND dept_no=%s AND group_no=%s",
            (student_id, dept, group),
            fetch=True,
        ):
            raise ValueError("学生不存在。")
        if not self.execute(
            "SELECT course_id FROM imported_shared_courses WHERE source_college=%s AND course_id=%s "
            "AND dept_no=%s AND group_no=%s",
            (source_college, course_id, dept, group),
            fetch=True,
        ):
            raise ValueError("共享课程不存在，请先导入课程XML。")
        self.execute(
            "INSERT INTO cross_college_selections (source_college, student_id, course_id, term_name, status, group_no, dept_no) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE status=VALUES(status)",
            (source_college, student_id, course_id, term_name, "跨校已选", group, dept),
        )

    def drop_enrollment(self, student_id, course_id, source_college, term_name):
        dept, group = self._scope()
        if source_college == COLLEGE_C:
            count = self.execute(
                "DELETE FROM sc WHERE student_id=%s AND course_id=%s AND dept_no=%s AND group_no=%s",
                (student_id, course_id, dept, group),
            )
        else:
            count = self.execute(
                "UPDATE cross_college_selections SET status='已退选' "
                "WHERE student_id=%s AND course_id=%s AND source_college=%s AND term_name=%s "
                "AND dept_no=%s AND group_no=%s",
                (student_id, course_id, source_college, term_name, dept, group),
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
            "SELECT COUNT(*) AS total FROM course WHERE dept_no=%s AND group_no=%s",
            (dept, group),
            fetch=True,
        )[0]["total"]
        local_enroll = self.execute(
            "SELECT COUNT(*) AS total FROM sc WHERE dept_no=%s AND group_no=%s AND score<>%s",
            (dept, group, DROPPED_SCORE),
            fetch=True,
        )[0]["total"]
        cross_enroll = self.execute(
            "SELECT COUNT(*) AS total FROM cross_college_selections "
            "WHERE dept_no=%s AND group_no=%s AND status<>'已退选'",
            (dept, group),
            fetch=True,
        )[0]["total"]
        return {"students": students, "courses": courses, "enrollments": local_enroll + cross_enroll}
