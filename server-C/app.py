import random
import tkinter as tk
from collections import Counter
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from xml.dom import minidom
import xml.etree.ElementTree as ET

import pymysql

from integration_api import (
    DEFAULT_INTEGRATION_URL,
    DEFAULT_PROVIDER_PORT,
    IntegrationClient,
    IntegrationProviderServer,
    integrated_course_to_import_row,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "xml_data"
EXPORT_DIR = DATA_DIR / "exports"
IMPORT_DIR = DATA_DIR / "imports"
SAMPLE_DIR = DATA_DIR / "samples"

DB_CONFIG = {
    "host": "sql.wsfdb.cn",
    "port": 3306,
    "user": "zhongyixiaStudentSystem",
    "password": "zz050108",
    "database": "zhongyixiaStudentSystem",
    "charset": "utf8mb4",
    "autocommit": True,
    "cursorclass": pymysql.cursors.DictCursor,
}

APP_USERS = [("admin", "123456"), ("teacher", "123456")]
COLLEGE_C = "C"
TERM = "2025-2026-2"
GRADE_LIMITS = {"C000000": 4, "C000001": 5, "C000002": 6, "C000003": 7}


class Database:
    def __init__(self, config):
        self.config = config

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

    def _table_has_columns(self, table: str, columns: list[str]) -> bool:
        if not self._table_exists(table):
            return False
        return all(self._column_exists(table, col) for col in columns)

    def repair_schema(self):
        """修复远程库中旧版表结构（缺少 Cno 等字段时重建集成相关表）。"""
        core_required = {
            "c_courses": ["Cno", "Cnn", "Crd", "Cpt", "Tec", "Pla", "Share"],
            "c_students": ["Sno", "Snn", "Sex", "Sde", "Pwd"],
            "c_sc": ["Cno", "Sno", "Grd"],
        }
        integration_tables = [
            "inbound_cross_enrollments",
            "cross_college_selections",
            "imported_shared_courses",
        ]
        integration_required = {
            "imported_shared_courses": [
                "source_college",
                "Cno",
                "Cnn",
                "Crd",
                "Cpt",
                "Tec",
                "Pla",
                "xml_path",
            ],
            "cross_college_selections": [
                "source_college",
                "Sno",
                "Cno",
                "term_name",
                "status",
            ],
            "inbound_cross_enrollments": [
                "source_college",
                "Sno",
                "Snn",
                "Cno",
                "Cnn",
                "term_name",
                "status",
                "xml_path",
            ],
        }

        core_broken = any(
            self._table_exists(table) and not self._table_has_columns(table, cols)
            for table, cols in core_required.items()
        )
        if core_broken:
            for table in [
                "inbound_cross_enrollments",
                "cross_college_selections",
                "imported_shared_courses",
                "c_sc",
                "c_courses",
                "c_students",
                "c_accounts",
            ]:
                self.execute(f"DROP TABLE IF EXISTS {table}")

        for table in integration_tables:
            cols = integration_required[table]
            if self._table_exists(table) and not self._table_has_columns(table, cols):
                self.execute(f"DROP TABLE IF EXISTS {table}")

    def initialize_schema(self):
        self.repair_schema()
        statements = [
            "CREATE TABLE IF NOT EXISTS c_accounts (acc VARCHAR(12) PRIMARY KEY, passwd VARCHAR(12) NOT NULL, CreateDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS c_students (Sno VARCHAR(9) PRIMARY KEY, Snn VARCHAR(10) NOT NULL, Sex VARCHAR(1) NOT NULL, Sde VARCHAR(6) NOT NULL, Pwd CHAR(6) NOT NULL)",
            "CREATE TABLE IF NOT EXISTS c_courses (Cno VARCHAR(16) PRIMARY KEY, Cnn VARCHAR(20) NOT NULL, Crd INT NOT NULL, Cpt INT NOT NULL, Tec VARCHAR(20) NOT NULL, Pla VARCHAR(30) NOT NULL, Share CHAR(1) NOT NULL)",
            "CREATE TABLE IF NOT EXISTS c_sc (Cno VARCHAR(16) NOT NULL, Sno VARCHAR(9) NOT NULL, Grd INT NOT NULL DEFAULT 0, PRIMARY KEY (Cno, Sno))",
            "CREATE TABLE IF NOT EXISTS imported_shared_courses (source_college VARCHAR(5) NOT NULL, Cno VARCHAR(16) NOT NULL, Cnn VARCHAR(30) NOT NULL, Crd INT NOT NULL, Cpt INT NOT NULL, Tec VARCHAR(20) NOT NULL, Pla VARCHAR(30) NOT NULL, xml_path VARCHAR(255) NOT NULL, PRIMARY KEY (source_college, Cno))",
            "CREATE TABLE IF NOT EXISTS cross_college_selections (source_college VARCHAR(5) NOT NULL, Sno VARCHAR(9) NOT NULL, Cno VARCHAR(16) NOT NULL, term_name VARCHAR(30) NOT NULL, status VARCHAR(20) NOT NULL, PRIMARY KEY (source_college, Sno, Cno, term_name))",
            "CREATE TABLE IF NOT EXISTS inbound_cross_enrollments (source_college VARCHAR(5) NOT NULL, Sno VARCHAR(9) NOT NULL, Snn VARCHAR(20) NOT NULL, Cno VARCHAR(16) NOT NULL, Cnn VARCHAR(30) NOT NULL, term_name VARCHAR(30) NOT NULL, status VARCHAR(20) NOT NULL, xml_path VARCHAR(255) NOT NULL, PRIMARY KEY (source_college, Sno, Cno, term_name))",
        ]
        for sql in statements:
            self.execute(sql)

    def seed_base_data(self):
        for table in ['inbound_cross_enrollments', 'cross_college_selections', 'imported_shared_courses', 'c_sc', 'c_courses', 'c_students', 'c_accounts']:
            self.execute(f"DELETE FROM {table}")
        self.execute("INSERT INTO c_accounts (acc, passwd) VALUES (%s, %s)", APP_USERS, many=True)
        depts = ['CS', 'SE', 'AI', 'IS', 'NE']
        students = [(f"C{i:08d}"[:9], f"学生{i:02d}", '男' if i % 2 else '女', depts[(i - 1) % 5], f"{100000 + i}"[-6:]) for i in range(1, 51)]
        self.execute("INSERT INTO c_students (Sno, Snn, Sex, Sde, Pwd) VALUES (%s, %s, %s, %s, %s)", students, many=True)
        names = ['数据库', '数据结构', '计网', '操作系统', 'Python', '机器学习', 'Web开发', '信息系统', '软件测试', '数据集成']
        teachers = ['王老师', '李老师', '赵老师', '陈老师', '孙老师']
        places = ['一教101', '一教202', '二教305', '实验楼201', '实验楼403']
        courses = [(f"C{i:03d}", n, 2 + i % 3, 16 + i, teachers[(i - 1) % 5], places[(i - 1) % 5], 'Y' if i <= 6 else 'N') for i, n in enumerate(names, 1)]
        self.execute("INSERT INTO c_courses (Cno, Cnn, Crd, Cpt, Tec, Pla, Share) VALUES (%s, %s, %s, %s, %s, %s, %s)", courses, many=True)
        cnos = [c[0] for c in courses]
        picks = []
        for i, stu in enumerate(students, 1):
            random.seed(i)
            for cno in random.sample(cnos, 5):
                picks.append((cno, stu[0], 0))
        self.execute("INSERT INTO c_sc (Cno, Sno, Grd) VALUES (%s, %s, %s)", picks, many=True)

    def validate_login(self, acc, passwd):
        rows = self.execute("SELECT acc FROM c_accounts WHERE acc=%s AND passwd=%s", (acc, passwd), fetch=True)
        if rows:
            return {"account": rows[0]["acc"], "role": "admin"}
        rows = self.execute("SELECT Sno, Snn FROM c_students WHERE Sno=%s AND Pwd=%s", (acc, passwd), fetch=True)
        if rows:
            return {"account": rows[0]["Sno"], "role": "student", "name": rows[0]["Snn"]}
        return None

    def has_initialized_users(self):
        return self.execute("SELECT COUNT(*) total FROM c_accounts", fetch=True)[0]['total'] > 0

    def get_student_profile(self, sno):
        rows = self.execute("SELECT Sno, Snn, Sex, Sde, Pwd FROM c_students WHERE Sno=%s", (sno,), fetch=True)
        return rows[0] if rows else None

    def update_student_profile(self, sno, snn, sex, sde, pwd):
        return self.execute(
            "UPDATE c_students SET Snn=%s, Sex=%s, Sde=%s, Pwd=%s WHERE Sno=%s",
            (snn, sex, sde, pwd, sno),
        )

    def get_students(self):
        return self.execute("SELECT Sno, Snn, Sex, Sde, Pwd FROM c_students ORDER BY Sno", fetch=True)

    def get_courses(self):
        return self.execute("SELECT Cno, Cnn, Crd, Cpt, Tec, Pla, Share FROM c_courses ORDER BY Cno", fetch=True)

    def get_shared_courses(self):
        return self.execute("SELECT Cno, Cnn, Crd, Cpt, Tec, Pla FROM c_courses WHERE Share='Y' ORDER BY Cno", fetch=True)

    def get_local_selectable_courses(self):
        return self.execute("SELECT Cno, Cnn, Crd, Cpt, Tec, Pla FROM c_courses WHERE Share='Y' ORDER BY Cno", fetch=True)

    def count_student_active_courses(self, sno):
        local_total = self.execute("SELECT COUNT(*) total FROM c_sc WHERE Sno=%s AND Grd >= 0", (sno,), fetch=True)[0]["total"]
        cross_total = self.execute("SELECT COUNT(*) total FROM cross_college_selections WHERE Sno=%s AND status<>'已退选'", (sno,), fetch=True)[0]["total"]
        return local_total + cross_total

    def add_local_course_for_student(self, sno, cno):
        self.execute("INSERT INTO c_sc (Cno, Sno, Grd) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE Grd=0", (cno, sno, 0))

    def remove_local_course_for_student(self, sno, cno):
        count = self.execute("UPDATE c_sc SET Grd=-1 WHERE Sno=%s AND Cno=%s", (sno, cno))
        if count == 0:
            raise ValueError("未找到对应本院选课记录。")

    def get_enrollments(self):
        local_rows = self.execute("SELECT s.Sno, s.Snn, sc.Cno, c.Cnn, 'C' source_college, %s term_name, CASE WHEN sc.Grd < 0 THEN '已退选' ELSE '已选' END status FROM c_sc sc JOIN c_students s ON s.Sno=sc.Sno JOIN c_courses c ON c.Cno=sc.Cno ORDER BY s.Sno, sc.Cno", (TERM,), fetch=True)
        cross_rows = self.execute("SELECT s.Sno, s.Snn, cs.Cno, i.Cnn, cs.source_college, cs.term_name, cs.status FROM cross_college_selections cs JOIN c_students s ON s.Sno=cs.Sno JOIN imported_shared_courses i ON i.source_college=cs.source_college AND i.Cno=cs.Cno ORDER BY s.Sno, cs.Cno", fetch=True)
        return local_rows + cross_rows

    def get_imported_shared_courses(self):
        return self.execute("SELECT source_college, Cno, Cnn, Tec, Crd, Cpt FROM imported_shared_courses ORDER BY source_college, Cno", fetch=True)

    def get_inbound_cross_enrollments(self):
        return self.execute("SELECT source_college, Sno, Snn, Cno, Cnn, term_name, status FROM inbound_cross_enrollments ORDER BY source_college, Sno", fetch=True)

    def import_shared_courses(self, rows, xml_path):
        sql = "INSERT INTO imported_shared_courses (source_college, Cno, Cnn, Crd, Cpt, Tec, Pla, xml_path) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE Cnn=VALUES(Cnn), Crd=VALUES(Crd), Cpt=VALUES(Cpt), Tec=VALUES(Tec), Pla=VALUES(Pla), xml_path=VALUES(xml_path)"
        params = [(r['source_college'], r['Cno'], r['Cnn'], r['Crd'], r['Cpt'], r['Tec'], r['Pla'], xml_path) for r in rows]
        if params:
            self.execute(sql, params, many=True)

    def import_inbound_selections(self, rows, xml_path):
        sql = "INSERT INTO inbound_cross_enrollments (source_college, Sno, Snn, Cno, Cnn, term_name, status, xml_path) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE Snn=VALUES(Snn), Cnn=VALUES(Cnn), status=VALUES(status), xml_path=VALUES(xml_path)"
        params = [(r['source_college'], r['Sno'], r['Snn'], r['Cno'], r['Cnn'], r['term_name'], r['status'], xml_path) for r in rows]
        if params:
            self.execute(sql, params, many=True)

    def add_cross_college_enrollment(self, sno, source_college, cno, term_name):
        self.check_student_course_limit(sno)
        if not self.execute("SELECT Sno FROM c_students WHERE Sno=%s", (sno,), fetch=True):
            raise ValueError('学生不存在。')
        if not self.execute("SELECT Cno FROM imported_shared_courses WHERE source_college=%s AND Cno=%s", (source_college, cno), fetch=True):
            raise ValueError('共享课程不存在，请先导入课程XML。')
        self.execute("INSERT INTO cross_college_selections (source_college, Sno, Cno, term_name, status) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE status=VALUES(status)", (source_college, sno, cno, term_name, '跨校已选'))

    def drop_enrollment(self, sno, cno, source_college, term_name):
        count = self.execute("UPDATE c_sc SET Grd=-1 WHERE Sno=%s AND Cno=%s", (sno, cno)) if source_college == COLLEGE_C else self.execute("UPDATE cross_college_selections SET status='已退选' WHERE Sno=%s AND Cno=%s AND source_college=%s AND term_name=%s", (sno, cno, source_college, term_name))
        if count == 0:
            raise ValueError('未找到对应选课记录。')

    @staticmethod
    def get_student_course_limit(sno):
        return GRADE_LIMITS.get(sno[:7], 5)

    def check_student_course_limit(self, sno):
        current = self.count_student_active_courses(sno)
        limit = self.get_student_course_limit(sno)
        if current >= limit:
            raise ValueError(f"当前年级最多只能选择 {limit} 门课程。")

    def get_local_stats(self):
        return {
            'students': self.execute("SELECT COUNT(*) total FROM c_students", fetch=True)[0]['total'],
            'courses': self.execute("SELECT COUNT(*) total FROM c_courses", fetch=True)[0]['total'],
            'enrollments': self.execute("SELECT COUNT(*) total FROM c_sc WHERE Grd >= 0", fetch=True)[0]['total'] + self.execute("SELECT COUNT(*) total FROM cross_college_selections WHERE status<>'已退选'", fetch=True)[0]['total'],
        }

class XmlService:
    def __init__(self, db):
        self.db = db
        for p in (DATA_DIR, EXPORT_DIR, IMPORT_DIR, SAMPLE_DIR):
            p.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def prettify(root):
        return minidom.parseString(ET.tostring(root, encoding='utf-8')).toprettyxml(indent='  ', encoding='utf-8')

    def write_xml(self, root, path):
        path.write_bytes(self.prettify(root))
        return path

    def export_shared_courses(self):
        root = ET.Element('sharedCourses', attrib={'college': COLLEGE_C, 'term': TERM})
        for row in self.db.get_shared_courses():
            node = ET.SubElement(root, 'course')
            for key in ('Cno', 'Cnn', 'Crd', 'Cpt', 'Tec', 'Pla'):
                ET.SubElement(node, key).text = str(row[key])
        return self.write_xml(root, EXPORT_DIR / 'college_c_shared_courses.xml')

    def import_shared_courses(self, path):
        root = ET.parse(path).getroot()
        source_college = root.attrib.get('college', 'UNKNOWN')
        rows = []
        for node in root.findall('course'):
            rows.append({'source_college': source_college, 'Cno': node.findtext('Cno', ''), 'Cnn': node.findtext('Cnn', ''), 'Crd': int(node.findtext('Crd', '0')), 'Cpt': int(node.findtext('Cpt', '0')), 'Tec': node.findtext('Tec', ''), 'Pla': node.findtext('Pla', '')})
        self.db.import_shared_courses(rows, str(path))
        return source_college, len(rows)

    def export_local_cross_selections(self):
        rows = self.db.execute("SELECT cs.source_college, s.Sno, s.Snn, cs.Cno, i.Cnn, cs.term_name, cs.status FROM cross_college_selections cs JOIN c_students s ON s.Sno=cs.Sno JOIN imported_shared_courses i ON i.source_college=cs.source_college AND i.Cno=cs.Cno ORDER BY cs.source_college, s.Sno", fetch=True)
        paths = []
        for college in sorted({r['source_college'] for r in rows}):
            root = ET.Element('crossCollegeSelections', attrib={'fromCollege': COLLEGE_C, 'toCollege': college, 'term': TERM})
            for row in [r for r in rows if r['source_college'] == college]:
                node = ET.SubElement(root, 'selection')
                for key in ('Sno', 'Snn', 'Cno', 'Cnn', 'term_name', 'status'):
                    ET.SubElement(node, key).text = str(row[key])
            paths.append(self.write_xml(root, EXPORT_DIR / f"college_c_to_{college.lower()}_selections.xml"))
        return paths

    def import_inbound_cross_selections(self, path):
        root = ET.parse(path).getroot()
        source_college = root.attrib.get('fromCollege', 'UNKNOWN')
        rows = []
        for node in root.findall('selection'):
            rows.append({'source_college': source_college, 'Sno': node.findtext('Sno', ''), 'Snn': node.findtext('Snn', ''), 'Cno': node.findtext('Cno', ''), 'Cnn': node.findtext('Cnn', ''), 'term_name': node.findtext('term_name', TERM), 'status': node.findtext('status', '已选')})
        self.db.import_inbound_selections(rows, str(path))
        return source_college, len(rows)

    def export_drop_request(self, sno, cno, source_college, term_name):
        root = ET.Element('dropRequest', attrib={'fromCollege': COLLEGE_C, 'toCollege': source_college, 'term': term_name})
        for k, v in {'Sno': sno, 'Cno': cno, 'source_college': source_college, 'status': '已退选'}.items():
            ET.SubElement(root, k).text = v
        return self.write_xml(root, EXPORT_DIR / f'drop_{sno}_{source_college}_{cno}.xml')

    def export_stats_snapshot(self):
        root = ET.Element('collegeStats', attrib={'college': COLLEGE_C, 'term': TERM})
        for k, v in self.db.get_local_stats().items():
            ET.SubElement(root, k).text = str(v)
        return self.write_xml(root, EXPORT_DIR / 'college_c_stats.xml')

    def aggregate_stats(self, files):
        results = {COLLEGE_C: self.db.get_local_stats()}
        for path in files:
            root = ET.parse(path).getroot()
            results[root.attrib.get('college', 'UNKNOWN')] = {'students': int(root.findtext('students', '0')), 'courses': int(root.findtext('courses', '0')), 'enrollments': int(root.findtext('enrollments', '0'))}
        total = Counter()
        for values in results.values():
            total.update(values)
        return results, total

    def ensure_sample_external_xml(self):
        paths = []
        for college in ('A', 'B'):
            path = SAMPLE_DIR / f'college_{college.lower()}_stats.xml'
            if not path.exists():
                root = ET.Element('collegeStats', attrib={'college': college, 'term': TERM})
                for k, v in {'students': 50, 'courses': 10, 'enrollments': 250}.items():
                    ET.SubElement(root, k).text = str(v)
                self.write_xml(root, path)
            paths.append(path)
        return paths

class SystemCApp:
    def __init__(self, root):
        self.root = root
        self.db = Database(DB_CONFIG)
        self.xml_service = XmlService(self.db)
        self.integration_url = DEFAULT_INTEGRATION_URL
        self.provider_port = DEFAULT_PROVIDER_PORT
        self.provider_server = None
        self.user_info = None
        self.root.title("系统C：基于XML的数据集成教务系统")
        self.root.geometry("1240x760")
        self.root.configure(bg="#f4f7fb")
        self.create_login_view()

    def create_login_view(self):
        self.clear_root()
        wrapper = tk.Frame(self.root, bg="#f4f7fb")
        wrapper.pack(fill="both", expand=True)

        card = tk.Frame(wrapper, bg="white", bd=1, relief="solid")
        card.place(relx=0.5, rely=0.5, anchor="center", width=460, height=330)

        tk.Label(card, text="系统C登录", font=("STHeiti", 24, "bold"), bg="white", fg="#1f3a5f").pack(pady=(30, 10))
        tk.Label(card, text="学院C（MySQL）+ XML集成服务器", font=("STSong", 12), bg="white", fg="#5f6b7a").pack(pady=(0, 25))

        form = tk.Frame(card, bg="white")
        form.pack(padx=50, fill="x")

        tk.Label(form, text="账号", bg="white", anchor="w").grid(row=0, column=0, sticky="w", pady=10)
        tk.Label(form, text="密码", bg="white", anchor="w").grid(row=1, column=0, sticky="w", pady=10)
        self.username_var = tk.StringVar(value="admin")
        self.password_var = tk.StringVar(value="123456")
        tk.Entry(form, textvariable=self.username_var, width=28).grid(row=0, column=1, sticky="ew", pady=10)
        tk.Entry(form, textvariable=self.password_var, show="*", width=28).grid(row=1, column=1, sticky="ew", pady=10)
        form.columnconfigure(1, weight=1)

        ttk.Button(card, text="登录系统", command=self.handle_login).pack(pady=25)
        tk.Label(card, text="默认账号：admin / 123456", bg="white", fg="#6b7280").pack()

    def handle_login(self):
        try:
            self.db.initialize_schema()
            if not self.db.has_initialized_users():
                self.db.seed_base_data()
        except Exception as exc:
            messagebox.showerror("数据库连接失败", str(exc))
            return
        user = self.db.validate_login(self.username_var.get().strip(), self.password_var.get().strip())
        if not user:
            messagebox.showerror("登录失败", "用户名或密码错误。")
            return
        self.user_info = user
        self.ensure_provider_running()
        self.create_main_view()

    def ensure_provider_running(self):
        """登录后自动启动本院 Internal API，供集成服务器回调（默认 8083）。"""
        try:
            port = int(self.provider_port) if self.provider_port else DEFAULT_PROVIDER_PORT
            if self.provider_server is None or self.provider_server.port != port:
                self.provider_server = IntegrationProviderServer(self.db, port=port)
            self.provider_server.start()
        except Exception:
            pass

    def create_main_view(self):
        self.clear_root()
        top = tk.Frame(self.root, bg="#17324d", height=62)
        top.pack(fill="x")
        tk.Label(top, text="系统C：基于XML的数据集成教务系统", font=("STHeiti", 20, "bold"), bg="#17324d", fg="white").pack(side="left", padx=20, pady=12)
        role_text = "管理员" if self.user_info["role"] == "admin" else "学生"
        name_text = self.user_info.get("name", self.user_info["account"])
        right_box = tk.Frame(top, bg="#17324d")
        right_box.pack(side="right", padx=20)
        tk.Label(right_box, text=f"当前用户：{name_text} / {role_text}", bg="#17324d", fg="#d7e4f2").pack(side="left", padx=(0, 12), pady=12)
        ttk.Button(right_box, text="退出登录", command=self.logout).pack(side="left", pady=12)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=14)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        if self.user_info["role"] == "admin":
            self.tab_init = tk.Frame(self.notebook, bg="#f7fafc")
            self.tab_data = tk.Frame(self.notebook, bg="#f7fafc")
            self.tab_xml = tk.Frame(self.notebook, bg="#f7fafc")
            self.tab_integration = tk.Frame(self.notebook, bg="#f7fafc")
            self.tab_stats = tk.Frame(self.notebook, bg="#f7fafc")
            self.tab_drop = tk.Frame(self.notebook, bg="#f7fafc")
            self.notebook.add(self.tab_init, text="初始化")
            self.notebook.add(self.tab_data, text="本院数据")
            self.notebook.add(self.tab_xml, text="XML集成")
            self.notebook.add(self.tab_integration, text="集成服务器")
            self.notebook.add(self.tab_stats, text="集成统计")
            self.notebook.add(self.tab_drop, text="退选流程")
            self.build_init_tab()
            self.build_data_tab()
            self.build_xml_tab()
            self.build_integration_tab()
            self.build_stats_tab()
            self.build_drop_tab()
        else:
            self.tab_profile = tk.Frame(self.notebook, bg="#f7fafc")
            self.tab_courses = tk.Frame(self.notebook, bg="#f7fafc")
            self.tab_stats = tk.Frame(self.notebook, bg="#f7fafc")
            self.notebook.add(self.tab_profile, text="个人信息管理")
            self.notebook.add(self.tab_courses, text="课程信息管理")
            self.notebook.add(self.tab_stats, text="统计信息查看")
            self.build_student_profile_tab()
            self.build_student_course_tab()
            self.build_student_stats_tab()

        self.refresh_all_views()


    def build_init_tab(self):
        box = tk.Frame(self.tab_init, bg="white", bd=1, relief="solid")
        box.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Label(box, text="系统C初始化（严格按院系C表结构）", font=("STHeiti", 18, "bold"), bg="white", fg="#183b56").pack(anchor="w", padx=20, pady=(20, 12))
        tk.Label(box, text="初始化后将生成 c_accounts、c_students、c_courses、c_sc 四张院系C原始表，以及集成过程辅助表。", bg="white", fg="#4b5563", justify="left").pack(anchor="w", padx=20)
        tk.Label(box, text="注意：重新初始化会清空「已导入共享课程」等集成数据，拉取外院课后请勿重复初始化。", bg="white", fg="#b45309", justify="left").pack(anchor="w", padx=20, pady=(8, 0))
        ttk.Button(box, text="初始化示例数据", command=self.initialize_demo_data).pack(anchor="w", padx=20, pady=20)
        self.init_text = tk.Text(box, height=24, bg="#0f172a", fg="#dbeafe")
        self.init_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def build_data_tab(self):
        frame = tk.Frame(self.tab_data, bg="#f7fafc")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.student_tree = self.create_treeview(frame, ["Sno", "Snn", "Sex", "Sde", "Pwd"], "院系C学生表 c_students")
        self.course_tree = self.create_treeview(frame, ["Cno", "Cnn", "Crd", "Cpt", "Tec", "Pla", "Share"], "院系C课程表 c_courses")
        self.enrollment_tree = self.create_treeview(frame, ["Sno", "Snn", "Cno", "Cnn", "source_college", "term_name", "status"], "选课结果（本院+跨院）")

    def build_xml_tab(self):
        left = tk.Frame(self.tab_xml, bg="#f7fafc")
        left.pack(side="left", fill="both", expand=True, padx=(16, 8), pady=16)
        right = tk.Frame(self.tab_xml, bg="#f7fafc")
        right.pack(side="left", fill="both", expand=True, padx=(8, 16), pady=16)

        actions = tk.Frame(left, bg="white", bd=1, relief="solid")
        actions.pack(fill="x")
        tk.Label(actions, text="XML集成操作", font=("STHeiti", 16, "bold"), bg="white", fg="#183b56").pack(anchor="w", padx=18, pady=(16, 12))
        buttons = [
            ("导出本院共享课程XML", self.action_export_shared_courses),
            ("导入外院共享课程XML", self.action_import_shared_courses),
            ("本院学生选修外院课程", self.action_choose_external_course),
            ("导出发往原学院的选课XML", self.action_export_cross_selections),
            ("导入外院学生选修本院课程XML", self.action_import_inbound_selections),
            ("导出本院统计快照XML", self.action_export_stats_snapshot),
        ]
        for text, cmd in buttons:
            ttk.Button(actions, text=text, command=cmd).pack(anchor="w", padx=18, pady=6)

        self.xml_log = tk.Text(left, height=18, bg="#111827", fg="#d1fae5")
        self.xml_log.pack(fill="both", expand=True, pady=(12, 0))

        refresh_row = tk.Frame(right, bg="#f7fafc")
        refresh_row.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(refresh_row, text="刷新导入课程列表", command=self.refresh_imported_views).pack(anchor="e")
        self.shared_course_tree = self.create_treeview(right, ["source_college", "Cno", "Cnn", "Tec", "Crd", "Cpt"], "已导入共享课程")
        self.inbound_tree = self.create_treeview(right, ["source_college", "Sno", "Snn", "Cno", "Cnn", "term_name", "status"], "外院学生选修本院课程")

    def build_integration_tab(self):
        wrapper = tk.Frame(self.tab_integration, bg="#f7fafc")
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)

        config = tk.Frame(wrapper, bg="white", bd=1, relief="solid")
        config.pack(fill="x")
        tk.Label(config, text="集成服务器连接", font=("STHeiti", 16, "bold"), bg="white", fg="#183b56").pack(anchor="w", padx=18, pady=(16, 10))
        form = tk.Frame(config, bg="white")
        form.pack(fill="x", padx=18, pady=(0, 12))
        tk.Label(form, text="集成服务器地址", bg="white").grid(row=0, column=0, sticky="e", padx=8, pady=8)
        tk.Label(form, text="本院 Provider 端口", bg="white").grid(row=1, column=0, sticky="e", padx=8, pady=8)
        self.integration_url_var = tk.StringVar(value=DEFAULT_INTEGRATION_URL)
        self.provider_port_var = tk.StringVar(value=str(DEFAULT_PROVIDER_PORT))
        tk.Entry(form, textvariable=self.integration_url_var, width=42).grid(row=0, column=1, sticky="w", padx=8, pady=8)
        tk.Entry(form, textvariable=self.provider_port_var, width=42).grid(row=1, column=1, sticky="w", padx=8, pady=8)
        tk.Label(
            config,
            text="Internal 接口：GET/POST /api/internal/course/shared|choose|drop（XML，与集成服务器配置端口 8083 一致）",
            bg="white",
            fg="#4b5563",
        ).pack(anchor="w", padx=18, pady=(0, 8))
        btn_row = tk.Frame(config, bg="white")
        btn_row.pack(anchor="w", padx=18, pady=(0, 16))
        ttk.Button(btn_row, text="启动本院 Provider 服务", command=self.action_start_provider).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="从服务器拉取共享课程", command=self.action_fetch_integrated_courses).pack(side="left", padx=8)
        ttk.Button(btn_row, text="刷新集成服务器统计", command=self.refresh_stats).pack(side="left", padx=8)

        self.integration_log = tk.Text(wrapper, height=22, bg="#111827", fg="#d1fae5")
        self.integration_log.pack(fill="both", expand=True, pady=(14, 0))

    def build_stats_tab(self):
        wrapper = tk.Frame(self.tab_stats, bg="#f7fafc")
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)
        top = tk.Frame(wrapper, bg="white", bd=1, relief="solid")
        top.pack(fill="x")
        tk.Label(top, text="集成服务器统计", font=("STHeiti", 16, "bold"), bg="white", fg="#183b56").pack(anchor="w", padx=18, pady=(16, 10))
        tk.Label(top, text="优先调用集成服务器 GET /api/integrated/statistics（JSON 汇总 A/B/C）；失败时回退本地 XML。", bg="white", fg="#4b5563").pack(anchor="w", padx=18)
        ttk.Button(top, text="刷新统计结果", command=self.refresh_stats).pack(anchor="w", padx=18, pady=14)
        self.stats_text = tk.Text(wrapper, height=26, bg="#0b1220", fg="#bfdbfe")
        self.stats_text.pack(fill="both", expand=True, pady=(14, 0))

    def build_drop_tab(self):
        box = tk.Frame(self.tab_drop, bg="white", bd=1, relief="solid")
        box.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(box, text="集成环境退选流程", font=("STHeiti", 16, "bold"), bg="white", fg="#183b56").grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 12))
        labels = [("学生学号", "drop_student_var"), ("课程编号", "drop_course_var"), ("课程所属学院", "drop_source_var"), ("学期", "drop_term_var")]
        defaults = {"drop_source_var": COLLEGE_C, "drop_term_var": TERM}
        for idx, (text, attr) in enumerate(labels, start=1):
            tk.Label(box, text=text, bg="white").grid(row=idx, column=0, sticky="e", padx=10, pady=8)
            var = tk.StringVar(value=defaults.get(attr, ""))
            setattr(self, attr, var)
            tk.Entry(box, textvariable=var, width=36).grid(row=idx, column=1, sticky="w", padx=10, pady=8)
        ttk.Button(box, text="执行退选并导出XML", command=self.action_drop_enrollment).grid(row=5, column=1, sticky="w", padx=10, pady=16)
        self.drop_log = tk.Text(box, height=20, bg="#1f2937", fg="#fde68a")
        self.drop_log.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=18, pady=(0, 18))
        box.columnconfigure(1, weight=1)
        box.rowconfigure(6, weight=1)

    def create_treeview(self, parent, columns, title):
        outer = tk.Frame(parent, bg="white", bd=1, relief="solid")
        outer.pack(fill="both", expand=True, padx=8, pady=8)
        tk.Label(outer, text=title, font=("STSong", 14, "bold"), bg="white", fg="#183b56").pack(anchor="w", padx=12, pady=(10, 6))
        tree = ttk.Treeview(outer, columns=columns, show="headings", height=8)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=120)
        tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        return tree

    def initialize_demo_data(self):
        try:
            self.db.repair_schema()
            self.db.initialize_schema()
            self.db.seed_base_data()
            sample_files = self.xml_service.ensure_sample_external_xml()
            self.log(self.init_text, "已按院系C原始结构初始化：c_accounts / c_students / c_courses / c_sc")
            for path in sample_files:
                self.log(self.init_text, f"已生成示例统计XML：{path}")
            self.refresh_all_views()
        except Exception as exc:
            messagebox.showerror("初始化失败", str(exc))

    def action_export_shared_courses(self):
        try:
            path = self.xml_service.export_shared_courses()
            self.log(self.xml_log, f"已导出本院共享课程XML：{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def action_import_shared_courses(self):
        path = filedialog.askopenfilename(title="选择外院共享课程XML", filetypes=[("XML Files", "*.xml")], initialdir=str(SAMPLE_DIR))
        if not path:
            return
        try:
            college, count = self.xml_service.import_shared_courses(path)
            self.log(self.xml_log, f"已导入{college}学院共享课程 {count} 门：{path}")
            self.refresh_all_views()
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))

    def get_integration_client(self):
        self.integration_url = self.integration_url_var.get().strip() if hasattr(self, "integration_url_var") else self.integration_url
        return IntegrationClient(self.integration_url)

    def action_start_provider(self):
        try:
            port = int(self.provider_port_var.get().strip())
            if self.provider_server is None or self.provider_server.port != port:
                self.provider_server = IntegrationProviderServer(self.db, port=port)
            self.provider_server.start()
            self.provider_port = port
            self.log(self.integration_log, f"本院 Internal API 已启动：http://127.0.0.1:{port}/api/internal/course/shared")
            self.log(self.integration_log, f"外院选课回调：POST http://127.0.0.1:{port}/api/internal/course/choose")
        except Exception as exc:
            messagebox.showerror("Provider 启动失败", str(exc))

    def action_fetch_integrated_courses(self):
        try:
            self.db.repair_schema()
            client = self.get_integration_client()
            courses = client.get_shared_courses()
            if not courses:
                messagebox.showwarning(
                    "未获取到课程",
                    "集成服务器未返回外院共享课程。\n"
                    "请确认：\n"
                    "1. 院系 A 已启动（python app.py，端口 8081）\n"
                    "2. 浏览器访问 http://localhost:8080/api/integrated/course/shared\n"
                    "   时需带请求头 SourceSystem: C（或用下方测试链接）",
                )
                return
            rows = [integrated_course_to_import_row(c) for c in courses]
            self.db.import_shared_courses(rows, f"integration:{self.integration_url}")
            self.log(self.integration_log, f"已从集成服务器（XML）导入 {len(rows)} 门外院共享课程。")
            self.log(
                self.integration_log,
                "请到「XML集成」页右侧「已导入共享课程」查看；若为空请点该页「刷新导入课程列表」。",
            )
            self.refresh_imported_views()
            self.refresh_all_views()
        except Exception as exc:
            hint = ""
            if "Unknown column 'Cno'" in str(exc):
                hint = "\n\n请在「初始化」页重新点击「初始化示例数据」以重建数据库表。"
            messagebox.showerror("拉取课程失败", f"{exc}{hint}")

    def action_choose_external_course(self):
        dialog = ChoiceDialog(self.root, self.db)
        self.root.wait_window(dialog.top)
        if not dialog.result:
            return
        student_id, source_college, course_id, course_name = dialog.result
        try:
            student = self.db.get_student_profile(student_id)
            if not student:
                raise ValueError("学生不存在。")
            self.db.add_cross_college_enrollment(student_id, source_college, course_id, TERM)
            try:
                client = self.get_integration_client()
                student_xml = {
                    "Sno": student_id,
                    "Snm": student["Snn"],
                    "Sex": student["Sex"],
                    "Sde": student["Sde"],
                }
                code, msg = client.choose_course(student_xml, course_id, source_college)
                if code != "200":
                    raise RuntimeError(msg or f"集成服务器返回 Code={code}")
                self.log(self.xml_log, f"已同步至集成服务器：{student_id} 选修 {source_college}/{course_id}")
                if hasattr(self, "integration_log"):
                    self.log(self.integration_log, f"跨院选课已提交（XML）：{student_id} -> {source_college}/{course_id}")
            except Exception as sync_exc:
                self.log(self.xml_log, f"本地选课成功，但集成服务器同步失败：{sync_exc}")
            self.log(self.xml_log, f"学生 {student_id} 已选修 {source_college} 学院课程 {course_id}。")
            self.refresh_all_views()
        except Exception as exc:
            messagebox.showerror("选课失败", str(exc))


    def action_export_cross_selections(self):
        try:
            paths = self.xml_service.export_local_cross_selections()
            if not paths:
                self.log(self.xml_log, "当前没有本院学生选修外院课程的数据。")
                return
            for path in paths:
                self.log(self.xml_log, f"已导出跨校选课XML：{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def action_import_inbound_selections(self):
        path = filedialog.askopenfilename(title="选择外院学生选修本院课程XML", filetypes=[("XML Files", "*.xml")], initialdir=str(IMPORT_DIR))
        if not path:
            return
        try:
            college, count = self.xml_service.import_inbound_cross_selections(path)
            self.log(self.xml_log, f"已导入 {college} 学院学生选修本院课程 {count} 条。")
            self.refresh_all_views()
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))

    def action_export_stats_snapshot(self):
        try:
            path = self.xml_service.export_stats_snapshot()
            self.log(self.xml_log, f"已导出统计快照XML：{path}")
            self.refresh_stats()
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def action_drop_enrollment(self):
        student_id = self.drop_student_var.get().strip()
        course_id = self.drop_course_var.get().strip()
        source_college = self.drop_source_var.get().strip() or COLLEGE_C
        term_name = self.drop_term_var.get().strip() or TERM
        if not student_id or not course_id:
            messagebox.showwarning("信息不完整", "请填写学生学号和课程编号。")
            return
        try:
            self.db.drop_enrollment(student_id, course_id, source_college, term_name)
            self.log(self.drop_log, f"已完成退选：{student_id} - {course_id}")
            if source_college != COLLEGE_C:
                try:
                    student = self.db.get_student_profile(student_id) or {"Snn": "", "Sex": "", "Sde": ""}
                    student_xml = {
                        "Sno": student_id,
                        "Snm": student.get("Snn", ""),
                        "Sex": student.get("Sex", ""),
                        "Sde": student.get("Sde", ""),
                    }
                    code, msg = self.get_integration_client().drop_course(
                        student_xml, course_id, source_college
                    )
                    if code != "200":
                        raise RuntimeError(msg or f"Code={code}")
                    self.log(self.drop_log, "已通过集成服务器 POST /api/integrated/course/drop 同步退选。")
                except Exception as sync_exc:
                    self.log(self.drop_log, f"集成服务器退选同步失败：{sync_exc}")
                path = self.xml_service.export_drop_request(student_id, course_id, source_college, term_name)
                self.log(self.drop_log, f"已生成发送至原学院的退选XML：{path}")
            else:
                self.log(self.drop_log, "该课程属于学院C，本地退选已完成，无需跨校回传。")
            self.refresh_all_views()
        except Exception as exc:
            messagebox.showerror("退选失败", str(exc))

    def on_tab_changed(self, event=None):
        if not self.user_info or self.user_info.get("role") != "admin":
            return
        try:
            widget = self.notebook.nametowidget(self.notebook.select())
            if widget == self.tab_xml:
                self.refresh_imported_views()
        except Exception:
            pass

    def refresh_imported_views(self):
        """仅刷新 XML 集成页的外院课程相关表格（避免被其它查询错误连带跳过）。"""
        if self.user_info.get("role") != "admin":
            return
        shared_cols = ["source_college", "Cno", "Cnn", "Tec", "Crd", "Cpt"]
        inbound_cols = ["source_college", "Sno", "Snn", "Cno", "Cnn", "term_name", "status"]
        try:
            shared_rows = self.db.get_imported_shared_courses()
            self.populate_tree(self.shared_course_tree, shared_rows, shared_cols)
            if hasattr(self, "xml_log"):
                self.log(self.xml_log, f"已导入共享课程：{len(shared_rows)} 门。")
        except Exception as exc:
            if hasattr(self, "xml_log"):
                self.log(self.xml_log, f"刷新共享课程列表失败：{exc}")
        try:
            self.populate_tree(
                self.inbound_tree,
                self.db.get_inbound_cross_enrollments(),
                inbound_cols,
            )
        except Exception as exc:
            if hasattr(self, "xml_log"):
                self.log(self.xml_log, f"刷新外院选课列表失败：{exc}")

    def refresh_all_views(self):
        if self.user_info["role"] == "admin":
            self._safe_populate(self.student_tree, self.db.get_students, ["Sno", "Snn", "Sex", "Sde", "Pwd"])
            self._safe_populate(self.course_tree, self.db.get_courses, ["Cno", "Cnn", "Crd", "Cpt", "Tec", "Pla", "Share"])
            self._safe_populate(
                self.enrollment_tree,
                self.db.get_enrollments,
                ["Sno", "Snn", "Cno", "Cnn", "source_college", "term_name", "status"],
            )
            self.refresh_imported_views()
        else:
            try:
                self.refresh_student_profile()
                self.refresh_student_courses()
            except Exception:
                pass
        try:
            self.refresh_stats()
        except Exception:
            pass

    def _safe_populate(self, tree, fetch_fn, columns):
        try:
            self.populate_tree(tree, fetch_fn(), columns)
        except Exception as exc:
            if hasattr(self, "xml_log"):
                self.log(self.xml_log, f"刷新列表失败（{columns[0]}…）：{exc}")

    def build_student_profile_tab(self):
        box = tk.Frame(self.tab_profile, bg="white", bd=1, relief="solid")
        box.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Label(box, text="个人信息管理", font=("STHeiti", 18, "bold"), bg="white", fg="#183b56").pack(anchor="w", padx=20, pady=(20, 12))
        form = tk.Frame(box, bg="white")
        form.pack(fill="x", padx=20, pady=(0, 12))
        self.student_name_var = tk.StringVar()
        self.student_sex_var = tk.StringVar()
        self.student_dept_var = tk.StringVar()
        self.student_pwd_var = tk.StringVar()
        for idx, (label, var) in enumerate([("姓名", self.student_name_var), ("性别", self.student_sex_var), ("院系", self.student_dept_var), ("密码", self.student_pwd_var)]):
            tk.Label(form, text=label, bg="white").grid(row=idx, column=0, sticky="e", padx=8, pady=8)
            tk.Entry(form, textvariable=var, width=28).grid(row=idx, column=1, sticky="w", padx=8, pady=8)
        ttk.Button(form, text="保存个人信息", command=self.save_student_profile).grid(row=4, column=1, sticky="w", padx=8, pady=10)
        self.profile_text = tk.Text(box, height=10, bg="#0f172a", fg="#dbeafe")
        self.profile_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def build_student_course_tab(self):
        frame = tk.Frame(self.tab_courses, bg="#f7fafc")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        action_box = tk.Frame(frame, bg="white", bd=1, relief="solid")
        action_box.pack(fill="x", padx=8, pady=8)
        self.local_course_var = tk.StringVar()
        tk.Label(action_box, text="本院开放课程", bg="white").pack(side="left", padx=(16, 8), pady=12)
        self.local_course_box = ttk.Combobox(action_box, textvariable=self.local_course_var, state="readonly", width=28)
        self.local_course_box.pack(side="left", padx=8)
        ttk.Button(action_box, text="选择课程", command=self.select_local_course).pack(side="left", padx=8)
        ttk.Button(action_box, text="退选所选课程", command=self.drop_selected_course).pack(side="left", padx=8)
        self.course_tip = tk.Label(action_box, text="", bg="white", fg="#4b5563")
        self.course_tip.pack(side="right", padx=16)
        self.student_course_tree = self.create_treeview(frame, ["Cno", "Cnn", "source_college", "term_name", "status"], "我的课程信息")

    def build_student_stats_tab(self):
        wrapper = tk.Frame(self.tab_stats, bg="#f7fafc")
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)
        card = tk.Frame(wrapper, bg="white", bd=1, relief="solid")
        card.pack(fill="both", expand=True)
        tk.Label(card, text="统计信息查看", font=("STHeiti", 16, "bold"), bg="white", fg="#183b56").pack(anchor="w", padx=18, pady=(16, 10))
        self.student_stats_text = tk.Text(card, height=24, bg="#0b1220", fg="#bfdbfe")
        self.student_stats_text.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def refresh_student_profile(self):
        row = self.db.get_student_profile(self.user_info["account"])
        if not row:
            return
        self.student_name_var.set(row["Snn"])
        self.student_sex_var.set(row["Sex"])
        self.student_dept_var.set(row["Sde"])
        self.student_pwd_var.set(row["Pwd"])
        self.profile_text.delete("1.0", tk.END)
        self.profile_text.insert(tk.END, f"学号：{row['Sno']}\n")
        self.profile_text.insert(tk.END, f"姓名：{row['Snn']}\n")
        self.profile_text.insert(tk.END, f"性别：{row['Sex']}\n")
        self.profile_text.insert(tk.END, f"院系：{row['Sde']}\n")
        self.profile_text.insert(tk.END, f"登录密码：{row['Pwd']}\n")

    def save_student_profile(self):
        try:
            self.db.update_student_profile(
                self.user_info["account"],
                self.student_name_var.get().strip(),
                self.student_sex_var.get().strip(),
                self.student_dept_var.get().strip(),
                self.student_pwd_var.get().strip(),
            )
            self.user_info["name"] = self.student_name_var.get().strip() or self.user_info["name"]
            self.refresh_student_profile()
            messagebox.showinfo("保存成功", "个人信息已更新。")
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def refresh_student_courses(self):
        all_rows = self.db.get_enrollments()
        rows = [row for row in all_rows if row.get("Sno") == self.user_info["account"]]
        self.populate_tree(self.student_course_tree, rows, ["Cno", "Cnn", "source_college", "term_name", "status"])
        options = [f"{row['Cno']} | {row['Cnn']}" for row in self.db.get_local_selectable_courses()]
        self.local_course_box["values"] = options
        if options and not self.local_course_var.get():
            self.local_course_box.current(0)
        limit = self.db.get_student_course_limit(self.user_info["account"])
        current = self.db.count_student_active_courses(self.user_info["account"])
        self.course_tip.config(text=f"当前已选 {current} / {limit} 门")

    def select_local_course(self):
        value = self.local_course_var.get().strip()
        if not value:
            messagebox.showwarning("未选择课程", "请先选择一门本院开放课程。")
            return
        course_id = value.split(" | ", 1)[0]
        try:
            self.db.check_student_course_limit(self.user_info["account"])
            self.db.add_local_course_for_student(self.user_info["account"], course_id)
            self.refresh_student_courses()
            messagebox.showinfo("选课成功", f"已选择课程 {course_id}。")
        except Exception as exc:
            messagebox.showerror("选课失败", str(exc))

    def drop_selected_course(self):
        selected = self.student_course_tree.selection()
        if not selected:
            messagebox.showwarning("未选择课程", "请先在列表中选择一门课程。")
            return
        values = self.student_course_tree.item(selected[0], "values")
        course_id, source_college = values[0], values[2]
        try:
            self.db.drop_enrollment(self.user_info["account"], course_id, source_college, TERM)
            if source_college != COLLEGE_C:
                try:
                    profile = self.db.get_student_profile(self.user_info["account"]) or {}
                    student_xml = {
                        "Sno": self.user_info["account"],
                        "Snm": profile.get("Snn", self.user_info.get("name", "")),
                        "Sex": profile.get("Sex", ""),
                        "Sde": profile.get("Sde", ""),
                    }
                    self.get_integration_client().drop_course(
                        student_xml, course_id, source_college
                    )
                except Exception:
                    pass
            self.refresh_student_courses()
            messagebox.showinfo("退课成功", f"已退选课程 {course_id}。")
        except Exception as exc:
            messagebox.showerror("退课失败", str(exc))

    def refresh_stats(self):
        target = self.stats_text if self.user_info["role"] == "admin" else self.student_stats_text
        target.delete("1.0", tk.END)
        try:
            stats = self.get_integration_client().get_statistics()
            target.insert(tk.END, "集成服务器统计（GET /api/integrated/statistics，汇总各学院）\n")
            target.insert(tk.END, "=" * 46 + "\n")
            target.insert(tk.END, f"学生总数：{stats.get('studentCount', stats.get('students', 0))}\n")
            target.insert(tk.END, f"课程总数：{stats.get('courseCount', stats.get('courses', 0))}\n")
            target.insert(tk.END, f"选课总数：{stats.get('selectionCount', stats.get('enrollments', 0))}\n")
            colleges = stats.get("colleges", [])
            if colleges:
                target.insert(tk.END, f"已汇总学院：{', '.join(colleges)}\n")
            warnings = stats.get("warnings", [])
            if warnings:
                target.insert(tk.END, "-" * 46 + "\n")
                target.insert(tk.END, "部分学院未响应：\n")
                for w in warnings:
                    target.insert(tk.END, f"  - {w}\n")
            if hasattr(self, "integration_log"):
                self.log(self.integration_log, "已刷新集成服务器统计数据。")
            if self.user_info["role"] == "admin":
                local = self.db.get_local_stats()
                target.insert(tk.END, "-" * 46 + "\n")
                target.insert(tk.END, f"学院C本地：学生 {local['students']}，课程 {local['courses']}，选课 {local['enrollments']}\n")
                inbound_total = len(self.db.get_inbound_cross_enrollments())
                external_total = len(self.db.get_imported_shared_courses())
                target.insert(tk.END, f"已接入外院共享课程：{external_total} 门\n")
                target.insert(tk.END, f"外院学生选修本院：{inbound_total} 条\n")
            return
        except Exception as remote_exc:
            self.log(target, f"集成服务器不可用：{remote_exc}")
            self.log(target, "已回退到本地 XML 统计汇总。\n")
        try:
            sample_paths = self.xml_service.ensure_sample_external_xml()
            results, total = self.xml_service.aggregate_stats(sample_paths)
            self.log(target, "本地 XML 汇总结果")
            self.log(target, "=" * 46)
            for college, values in sorted(results.items()):
                self.log(target, f"学院 {college}：学生 {values['students']} 人，课程 {values['courses']} 门，选课 {values['enrollments']} 条")
            self.log(target, "-" * 46)
            self.log(target, f"总计：学生 {total['students']} 人，课程 {total['courses']} 门，选课 {total['enrollments']} 条")
        except Exception as exc:
            self.log(target, f"统计失败：{exc}")

    @staticmethod
    def populate_tree(tree, rows, columns):
        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            tree.insert("", "end", values=[row.get(col, "") for col in columns])

    @staticmethod
    def log(widget, message):
        widget.insert(tk.END, message + "\n")
        widget.see(tk.END)

    def logout(self):
        if not messagebox.askyesno("确认退出", "确定要退出登录吗？"):
            return
        self.user_info = None
        self.username_var = tk.StringVar(value="")
        self.password_var = tk.StringVar(value="")
        self.create_login_view()

    def clear_root(self):
        for child in self.root.winfo_children():
            child.destroy()


class ChoiceDialog:
    def __init__(self, parent, db):
        self.db = db
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("本院学生选修外院共享课程")
        self.top.geometry("460x280")
        self.top.grab_set()

        self.student_var = tk.StringVar()
        self.course_var = tk.StringVar()

        students = [row["Sno"] for row in self.db.get_students()]
        shared = self.db.get_imported_shared_courses()
        courses = [f"{row['source_college']}|{row['Cno']}|{row['Cnn']}" for row in shared]

        tk.Label(self.top, text="学生学号").pack(anchor="w", padx=20, pady=(20, 6))
        student_box = ttk.Combobox(self.top, textvariable=self.student_var, values=students, state="readonly")
        student_box.pack(fill="x", padx=20)
        if students:
            student_box.current(0)

        tk.Label(self.top, text="共享课程").pack(anchor="w", padx=20, pady=(12, 6))
        course_box = ttk.Combobox(self.top, textvariable=self.course_var, values=courses, state="readonly")
        course_box.pack(fill="x", padx=20)
        if courses:
            course_box.current(0)

        ttk.Button(self.top, text="确认选课", command=self.confirm).pack(pady=22)

    def confirm(self):
        if not self.student_var.get() or not self.course_var.get():
            messagebox.showwarning("请选择", "请先选择学生与共享课程。")
            return
        source_college, course_id, course_name = self.course_var.get().split("|", 2)
        self.result = (self.student_var.get(), source_college, course_id, course_name)
        self.top.destroy()


def main():
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    SystemCApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
