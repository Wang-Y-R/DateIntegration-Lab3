"""
System A（院系A - 软件学院）Flask 后端应用
提供 Web GUI 和内部 XML API 接口
"""

import os
import sqlite3
from functools import wraps

import requests as http_client
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from lxml import etree

from db import get_db, init_db

app = Flask(__name__)
app.secret_key = "system-a-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XSD_DIR = os.path.join(BASE_DIR, "xsd")
XSL_DIR = os.path.join(BASE_DIR, "xsl")

INTEGRATION_SERVER = os.environ.get("INTEGRATION_SERVER", "http://localhost:8080")


# ========== 登录验证装饰器 ==========


def login_required(f):
    """要求用户已登录才能访问的装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """要求管理员权限才能访问的装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "管理员":
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated_function


# ========== XML 工具函数 ==========


def build_xml_response(code, message, data_xml=""):
    """构建标准 XML 响应报文

    Args:
        code: 状态码，如 200 / 400
        message: 状态描述
        data_xml: Data 节点内部 XML 字符串

    Returns:
        完整的 XML 响应字符串
    """
    response = etree.Element("Response")
    code_elem = etree.SubElement(response, "Code")
    code_elem.text = str(code)
    msg_elem = etree.SubElement(response, "Message")
    msg_elem.text = message
    data_elem = etree.SubElement(response, "Data")
    # 如果 data_xml 非空，将其中解析出的子节点追加到 Data 中
    if data_xml and data_xml.strip():
        try:
            data_children = etree.fromstring(f"<root>{data_xml}</root>")
            for child in data_children:
                data_elem.append(child)
        except etree.XMLSyntaxError:
            data_elem.text = data_xml
    return etree.tostring(
        response, xml_declaration=True, encoding="UTF-8", pretty_print=True
    ).decode("utf-8")


def validate_xml(xml_string, xsd_path):
    """使用 XSD 文件校验 XML 字符串

    Args:
        xml_string: 待校验的 XML 字符串
        xsd_path: XSD 文件的绝对路径

    Returns:
        (is_valid, error_message) 元组
    """
    try:
        schema_doc = etree.parse(xsd_path)
        schema = etree.XMLSchema(schema_doc)
        doc = etree.fromstring(
            xml_string.encode("utf-8") if isinstance(xml_string, str) else xml_string
        )
        schema.assertValid(doc)
        return True, ""
    except etree.DocumentInvalid as e:
        return False, str(e)
    except etree.XMLSyntaxError as e:
        return False, f"XML语法错误: {e}"
    except Exception as e:
        return False, str(e)


def transform_xml(xml_string, xsl_path):
    """使用 XSLT 将 XML 从一种格式转换为另一种格式

    Args:
        xml_string: 源 XML 字符串
        xsl_path: XSL 文件的绝对路径

    Returns:
        转换后的 XML 字符串
    """
    xsl_doc = etree.parse(xsl_path)
    transform = etree.XSLT(xsl_doc)
    doc = etree.fromstring(
        xml_string.encode("utf-8") if isinstance(xml_string, str) else xml_string
    )
    result = transform(doc)
    return etree.tostring(result, pretty_print=True, encoding="unicode")


def query_to_xml_courses(rows):
    """将课程查询结果转换为 System A 的 XML 格式

    Args:
        rows: sqlite3.Row 列表，包含课程字段

    Returns:
        Classes 节点下的 XML 字符串
    """
    classes_elem = etree.Element("Classes")
    for row in rows:
        cls = etree.SubElement(classes_elem, "class")
        fields = ["课程编号", "课程名称", "学分", "授课老师", "授课地点"]
        for field in fields:
            elem = etree.SubElement(cls, field)
            elem.text = str(row[field]) if row[field] is not None else ""
        # 共享字段仅在行中存在时才添加
        if "共享" in row.keys():
            share_elem = etree.SubElement(cls, "共享")
            share_elem.text = str(row["共享"]) if row["共享"] is not None else "N"
    return etree.tostring(classes_elem, encoding="unicode")


def query_to_xml_students(rows):
    """将学生查询结果转换为 System A 的 XML 格式

    Args:
        rows: sqlite3.Row 列表，包含学生字段

    Returns:
        Students 节点下的 XML 字符串
    """
    students_elem = etree.Element("Students")
    for row in rows:
        stu = etree.SubElement(students_elem, "student")
        fields = ["学号", "姓名", "性别", "院系"]
        for field in fields:
            elem = etree.SubElement(stu, field)
            elem.text = str(row[field]) if row[field] is not None else ""
    return etree.tostring(students_elem, encoding="unicode")


# ========== Web GUI 路由 ==========


@app.route("/", methods=["GET", "POST"])
def login():
    """登录页面：GET 显示表单，POST 验证账户并跳转"""
    # 已登录用户直接跳转到仪表盘
    if request.method == "GET" and "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("login.html", error="请输入账户名和密码")

        db = get_db()
        # 查询账户表验证用户名和密码
        account = db.execute(
            "SELECT * FROM account WHERE 账户名 = ? AND 密码 = ?",
            (username, password),
        ).fetchone()
        db.close()

        if account is None:
            return render_template("login.html", error="账户名或密码错误")

        # 登录成功，写入 session
        session["user"] = account["账户名"]
        session["role"] = account["权限"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """登出：清除 session 并跳转到登录页"""
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    """仪表盘页面：根据角色显示不同内容"""
    db = get_db()
    user = session["user"]
    role = session["role"]

    if role == "管理员":
        total_students = db.execute("SELECT COUNT(*) as cnt FROM student").fetchone()[
            "cnt"
        ]
        total_courses = db.execute("SELECT COUNT(*) as cnt FROM course").fetchone()[
            "cnt"
        ]
        total_choices = db.execute("SELECT COUNT(*) as cnt FROM choice").fetchone()[
            "cnt"
        ]
        shared_courses = db.execute(
            "SELECT COUNT(*) as cnt FROM course WHERE 共享='Y'"
        ).fetchone()["cnt"]
        course_enrollments = db.execute(
            """SELECT c.课程名称 as course_name, COUNT(ch.学生编号) as count
               FROM course c LEFT JOIN choice ch ON c.课程编号 = ch.课程编号
               GROUP BY c.课程编号 ORDER BY count DESC"""
        ).fetchall()
        db.close()
        stats = {
            "total_students": total_students,
            "total_courses": total_courses,
            "total_choices": total_choices,
            "shared_courses": shared_courses,
            "course_enrollments": [dict(row) for row in course_enrollments],
        }
        return render_template(
            "dashboard.html",
            role=role,
            user=user,
            stats=stats,
        )
    else:
        # 学生看到个人信息和已选课程
        student = db.execute(
            "SELECT * FROM student WHERE 关联账户 = ?",
            (user,),
        ).fetchone()
        # 查询该学生已选课程列表
        choices = db.execute(
            """SELECT c.*, ch.成绩
               FROM choice ch
               JOIN course c ON ch.课程编号 = c.课程编号
               WHERE ch.学生编号 = ?""",
            (student["学号"],),
        ).fetchall()
        db.close()
        return render_template(
            "dashboard.html",
            role=role,
            user=user,
            student=student,
            enrolled_courses=choices,
        )


@app.route("/courses")
@login_required
def courses():
    """课程列表页面：展示所有本地课程及其共享状态"""
    db = get_db()
    all_courses = db.execute("SELECT * FROM course ORDER BY 课程编号").fetchall()

    # 如果当前用户是学生，获取其已选课程编号
    enrolled_ids = set()
    if session["role"] == "学生":
        student = db.execute(
            "SELECT * FROM student WHERE 关联账户 = ?",
            (session["user"],),
        ).fetchone()
        if student:
            enrolled = db.execute(
                "SELECT 课程编号 FROM choice WHERE 学生编号 = ?",
                (student["学号"],),
            ).fetchall()
            enrolled_ids = {row["课程编号"] for row in enrolled}

    db.close()
    return render_template(
        "courses.html",
        courses=all_courses,
        enrolled_ids=enrolled_ids,
        role=session["role"],
    )


@app.route("/courses/enroll/<course_id>", methods=["POST"])
@login_required
def enroll_course(course_id):
    """学生选课：将学生与课程关联插入 choice 表"""
    if session["role"] != "学生":
        return redirect(url_for("courses"))

    db = get_db()
    # 获取当前学生的学号
    student = db.execute(
        "SELECT * FROM student WHERE 关联账户 = ?",
        (session["user"],),
    ).fetchone()
    if student is None:
        db.close()
        return redirect(url_for("courses"))

    try:
        # 插入选课记录，成绩暂为空
        db.execute(
            "INSERT INTO choice (课程编号, 学生编号, 成绩) VALUES (?, ?, ?)",
            (course_id, student["学号"], ""),
        )
        db.commit()
        app.logger.info("学生 %s 选课成功: %s", student["学号"], course_id)
    except sqlite3.IntegrityError:
        # 违反唯一约束（重复选课）
        app.logger.warning("学生 %s 重复选课: %s", student["学号"], course_id)
    finally:
        db.close()

    return redirect(url_for("courses"))


@app.route("/courses/drop/<course_id>", methods=["POST"])
@login_required
def drop_course(course_id):
    """学生退课：从 choice 表删除对应记录"""
    if session["role"] != "学生":
        return redirect(url_for("courses"))

    db = get_db()
    student = db.execute(
        "SELECT * FROM student WHERE 关联账户 = ?",
        (session["user"],),
    ).fetchone()
    if student is None:
        db.close()
        return redirect(url_for("courses"))

    try:
        db.execute(
            "DELETE FROM choice WHERE 课程编号 = ? AND 学生编号 = ?",
            (course_id, student["学号"]),
        )
        db.commit()
        app.logger.info("学生 %s 退课成功: %s", student["学号"], course_id)
    except Exception as e:
        app.logger.error("退课失败: %s", e)
    finally:
        db.close()

    return redirect(url_for("courses"))


@app.route("/courses/toggle-share/<course_id>", methods=["POST"])
@admin_required
def toggle_share(course_id):
    """管理员切换课程共享状态"""
    db = get_db()
    course = db.execute(
        "SELECT * FROM course WHERE 课程编号 = ?", (course_id,)
    ).fetchone()
    if course is None:
        db.close()
        return redirect(url_for("courses"))

    new_status = "N" if course["共享"] == "Y" else "Y"
    db.execute("UPDATE course SET 共享 = ? WHERE 课程编号 = ?", (new_status, course_id))
    db.commit()
    db.close()
    return redirect(url_for("courses"))


@app.route("/shared-courses")
@login_required
def shared_courses():
    """跨系选课页面：从集成服务器拉取其他院系的共享课程"""
    if session["role"] != "学生":
        return redirect(url_for("dashboard"))

    db = get_db()
    local_shared = db.execute(
        "SELECT * FROM course WHERE 共享 = 'Y' ORDER BY 课程编号"
    ).fetchall()
    db.close()

    cross_courses = []
    error = None
    try:
        resp = http_client.get(
            f"{INTEGRATION_SERVER}/api/integrated/course/shared",
            headers={"SourceSystem": "A"},
            timeout=5,
        )
        if resp.status_code == 200:
            root = etree.fromstring(resp.content)
            code = root.findtext("Code", "")
            if code == "200":
                data_node = root.find("Data")
                if data_node is not None:
                    classes_node = data_node.find("Classes")
                    if classes_node is not None:
                        for cls in classes_node.findall("class"):
                            cross_courses.append({
                                "课程编号": cls.findtext("课程编号", ""),
                                "课程名称": cls.findtext("课程名称", ""),
                                "学分": cls.findtext("学分", ""),
                                "授课老师": cls.findtext("授课老师", ""),
                                "授课地点": cls.findtext("授课地点", ""),
                            })
    except Exception as e:
        error = f"无法连接集成服务器: {e}"
        app.logger.warning("集成服务器连接失败: %s", e)

    return render_template(
        "shared_courses.html",
        local_shared=local_shared,
        cross_courses=cross_courses,
        error=error,
        user=session["user"],
    )


@app.route("/courses/choose-cross", methods=["POST"])
@login_required
def choose_cross_course():
    """跨系选课请求：组装 System A 格式 XML 并发送到集成服务器"""
    if session["role"] != "学生":
        return redirect(url_for("shared_courses"))

    course_id = request.form.get("course_id", "").strip()
    target_system = request.form.get("target_system", "").strip()

    if not course_id or not target_system:
        return redirect(url_for("shared_courses"))

    db = get_db()
    student = db.execute(
        "SELECT * FROM student WHERE 关联账户 = ?",
        (session["user"],),
    ).fetchone()
    db.close()

    if student is None:
        return redirect(url_for("shared_courses"))

    cross_choice = etree.Element("CrossDepartmentChoice")

    student_elem = etree.SubElement(cross_choice, "Student")
    etree.SubElement(student_elem, "学号").text = student["学号"]
    etree.SubElement(student_elem, "姓名").text = student["姓名"]
    etree.SubElement(student_elem, "性别").text = student["性别"]
    etree.SubElement(student_elem, "院系").text = student["院系"]

    choice_elem = etree.SubElement(cross_choice, "Choice")
    etree.SubElement(choice_elem, "课程编号").text = course_id
    etree.SubElement(choice_elem, "学生编号").text = student["学号"]
    etree.SubElement(choice_elem, "成绩").text = ""

    xml_body = etree.tostring(
        cross_choice, xml_declaration=True, encoding="UTF-8", pretty_print=True
    ).decode("utf-8")

    try:
        resp = http_client.post(
            f"{INTEGRATION_SERVER}/api/integrated/course/choose",
            data=xml_body.encode("utf-8"),
            headers={
                "Content-Type": "application/xml; charset=UTF-8",
                "SourceSystem": "A",
                "DestinationSystem": target_system,
            },
            timeout=10,
        )
        app.logger.info(
            "跨系选课响应: 目标=%s 课程=%s 状态=%s",
            target_system, course_id, resp.status_code,
        )
    except Exception as e:
        app.logger.error("跨系选课请求失败: %s", e)

    return redirect(url_for("shared_courses"))


@app.route("/admin/stats")
@admin_required
def admin_stats():
    """管理员统计页面：展示学生数、课程数、选课统计"""
    db = get_db()

    total_students = db.execute("SELECT COUNT(*) as cnt FROM student").fetchone()["cnt"]
    total_courses = db.execute("SELECT COUNT(*) as cnt FROM course").fetchone()["cnt"]
    shared_courses = db.execute(
        "SELECT COUNT(*) as cnt FROM course WHERE 共享='Y'"
    ).fetchone()["cnt"]
    total_choices = db.execute("SELECT COUNT(*) as cnt FROM choice").fetchone()["cnt"]
    course_enrollments = db.execute(
        """SELECT c.课程名称 as course_name, COUNT(ch.学生编号) as count
           FROM course c LEFT JOIN choice ch ON c.课程编号 = ch.课程编号
           GROUP BY c.课程编号 ORDER BY count DESC"""
    ).fetchall()
    db.close()

    stats = {
        "total_students": total_students,
        "total_courses": total_courses,
        "total_choices": total_choices,
        "shared_courses": shared_courses,
        "course_enrollments": [dict(row) for row in course_enrollments],
    }

    return render_template("admin_stats.html", stats=stats)


# ========== 内部 API 路由（供集成服务器调用，返回 XML） ==========


@app.route("/api/internal/statistics", methods=["GET"])
def api_internal_statistics():
    """供集成服务器汇总统计"""
    db = get_db()
    stats = {
        "college": "A",
        "students": db.execute("SELECT COUNT(*) as cnt FROM student").fetchone()["cnt"],
        "courses": db.execute("SELECT COUNT(*) as cnt FROM course").fetchone()["cnt"],
        "enrollments": db.execute("SELECT COUNT(*) as cnt FROM choice").fetchone()["cnt"],
    }
    db.close()
    return jsonify(stats)


@app.route("/api/internal/course/shared", methods=["GET"])
def api_shared_courses():
    """获取本院系所有共享课程的 XML 列表

    供集成服务器调用，返回共享课程（共享='Y'）的 XML 数据。
    请求头中应包含 SourceSystem 标识发起方身份。
    """
    # 记录请求来源
    source = request.headers.get("SourceSystem", "未知")
    app.logger.info("收到获取共享课程请求，来源: %s", source)

    db = get_db()
    # 查询所有标记为共享的课程
    shared_rows = db.execute(
        "SELECT * FROM course WHERE 共享 = 'Y' ORDER BY 课程编号"
    ).fetchall()
    db.close()

    if not shared_rows:
        xml_body = build_xml_response(200, "暂无共享课程", "")
    else:
        # 转换为 System A 的 XML 课程格式
        classes_xml = query_to_xml_courses(shared_rows)
        xml_body = build_xml_response(200, "获取共享课程列表成功", classes_xml)

    return xml_body, 200, {"Content-Type": "application/xml; charset=UTF-8"}


@app.route("/api/internal/course/choose", methods=["POST"])
def api_cross_choose():
    """跨系选课接口：接收集成服务器推送的跨系选课 XML

    解析 CrossDepartmentChoice XML，提取学生信息和选课信息，
    将学生插入 student 表（如不存在），将选课记录插入 choice 表。
    """
    source = request.headers.get("SourceSystem", "未知")
    app.logger.info("收到跨系选课请求，来源: %s", source)

    # 读取请求体 XML
    xml_data = request.data
    if not xml_data:
        xml_body = build_xml_response(400, "请求体为空")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    try:
        root = etree.fromstring(xml_data)
    except etree.XMLSyntaxError as e:
        xml_body = build_xml_response(400, f"XML解析失败: {e}")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    # 提取学生信息
    student_node = root.find("Student")
    if student_node is None:
        xml_body = build_xml_response(400, "缺少Student节点")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    sno = student_node.findtext("学号", "") or student_node.findtext("Sno", "")
    sno = sno.strip()
    snm = student_node.findtext("姓名", "") or student_node.findtext("Snm", "")
    snm = snm.strip()
    sex = student_node.findtext("性别", "") or student_node.findtext("Sex", "")
    sex = sex.strip()
    sde = student_node.findtext("院系", "") or student_node.findtext("Sde", "") or student_node.findtext("专业", "")
    sde = sde.strip()

    if not sno or not snm:
        xml_body = build_xml_response(400, "学生信息不完整")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    choice_node = root.find("Choice")
    if choice_node is None:
        xml_body = build_xml_response(400, "缺少Choice节点")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    cid = choice_node.findtext("课程编号", "") or choice_node.findtext("Cid", "") or choice_node.findtext("Cno", "")
    cid = cid.strip()
    grd = choice_node.findtext("成绩", "") or choice_node.findtext("Grd", "") or choice_node.findtext("得分", "")
    grd = grd.strip()

    if not cid:
        xml_body = build_xml_response(400, "课程编号缺失")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    db = get_db()
    try:
        # 检查学生是否已存在，不存在则插入（跨系学生可能无关联账户）
        existing = db.execute("SELECT * FROM student WHERE 学号 = ?", (sno,)).fetchone()
        if existing is None:
            db.execute(
                "INSERT INTO student (学号, 姓名, 性别, 院系, 关联账户) VALUES (?, ?, ?, ?, ?)",
                (sno, snm, sex, sde, sno),  # 跨系学生使用学号作为关联账户
            )
            app.logger.info("插入跨系学生: %s %s", sno, snm)

        # 插入选课记录
        db.execute(
            "INSERT INTO choice (课程编号, 学生编号, 成绩) VALUES (?, ?, ?)",
            (cid, sno, grd),
        )
        db.commit()
        app.logger.info("跨系选课成功: 学生 %s 选课 %s", sno, cid)
        xml_body = build_xml_response(200, "跨系选课成功")
        return xml_body, 200, {"Content-Type": "application/xml; charset=UTF-8"}

    except sqlite3.IntegrityError:
        db.rollback()
        app.logger.warning("跨系选课重复: 学生 %s 课程 %s", sno, cid)
        xml_body = build_xml_response(400, "该学生已选修此课程")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}
    except Exception as e:
        db.rollback()
        app.logger.error("跨系选课异常: %s", e)
        xml_body = build_xml_response(500, f"服务器内部错误: {e}")
        return xml_body, 500, {"Content-Type": "application/xml; charset=UTF-8"}
    finally:
        db.close()


@app.route("/api/internal/course/drop", methods=["POST"])
def api_cross_drop():
    """跨系退课接口：接收集成服务器推送的跨系退课 XML

    解析 CrossDepartmentChoice XML，从 choice 表中删除对应选课记录。
    """
    source = request.headers.get("SourceSystem", "未知")
    app.logger.info("收到跨系退课请求，来源: %s", source)

    xml_data = request.data
    if not xml_data:
        xml_body = build_xml_response(400, "请求体为空")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    try:
        root = etree.fromstring(xml_data)
    except etree.XMLSyntaxError as e:
        xml_body = build_xml_response(400, f"XML解析失败: {e}")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    # 提取学生信息
    student_node = root.find("Student")
    if student_node is None:
        xml_body = build_xml_response(400, "缺少Student节点")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    sno = (student_node.findtext("学号", "") or student_node.findtext("Sno", "")).strip()
    if not sno:
        xml_body = build_xml_response(400, "学号缺失")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    choice_node = root.find("Choice")
    if choice_node is None:
        xml_body = build_xml_response(400, "缺少Choice节点")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    cid = (choice_node.findtext("课程编号", "") or choice_node.findtext("Cid", "") or choice_node.findtext("Cno", "")).strip()
    if not cid:
        xml_body = build_xml_response(400, "课程编号缺失")
        return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

    db = get_db()
    try:
        # 删除选课记录
        cursor = db.execute(
            "DELETE FROM choice WHERE 课程编号 = ? AND 学生编号 = ?",
            (cid, sno),
        )
        db.commit()

        if cursor.rowcount == 0:
            app.logger.warning("跨系退课未找到记录: 学生 %s 课程 %s", sno, cid)
            xml_body = build_xml_response(400, "未找到对应选课记录")
            return xml_body, 400, {"Content-Type": "application/xml; charset=UTF-8"}

        app.logger.info("跨系退课成功: 学生 %s 退课 %s", sno, cid)
        xml_body = build_xml_response(200, "跨系退课成功")
        return xml_body, 200, {"Content-Type": "application/xml; charset=UTF-8"}

    except Exception as e:
        db.rollback()
        app.logger.error("跨系退课异常: %s", e)
        xml_body = build_xml_response(500, f"服务器内部错误: {e}")
        return xml_body, 500, {"Content-Type": "application/xml; charset=UTF-8"}
    finally:
        db.close()


# ========== 启动入口 ==========

if __name__ == "__main__":
    init_db()
    app.run(port=8081, debug=True)
