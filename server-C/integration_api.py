"""学院C与集成服务器的 HTTP 对接：XML 客户端 + /api/internal Provider 服务。"""

from __future__ import annotations

import threading
import xml.etree.ElementTree as ET
from typing import Any

import requests
from flask import Flask, Response, jsonify, request

from db_schema import COLLEGE_C, DEPT_NO, GROUP_NO
DEFAULT_INTEGRATION_URL = "http://localhost:8080"
DEFAULT_PROVIDER_PORT = 8083


def build_xml_response(code: int | str, message: str, data_inner: str = "") -> bytes:
    root = ET.Element("Response")
    ET.SubElement(root, "Code").text = str(code)
    ET.SubElement(root, "Message").text = message
    data_elem = ET.SubElement(root, "Data")
    if data_inner.strip():
        try:
            wrapper = ET.fromstring(f"<wrapper>{data_inner}</wrapper>")
            for child in wrapper:
                data_elem.append(child)
        except ET.ParseError:
            data_elem.text = data_inner
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def courses_to_internal_xml(courses: list[dict[str, Any]]) -> str:
    parts = ["<Classes>"]
    for row in courses:
        parts.append("<class>")
        parts.append(f"<Cno>{row.get('course_id', row.get('Cno', ''))}</Cno>")
        parts.append(f"<Cnm>{row.get('course_name', row.get('Cnn', row.get('Cnm', '')))}</Cnm>")
        parts.append(f"<Ctm>{row.get('class_hours', row.get('Cpt', row.get('Ctm', 0)))}</Ctm>")
        parts.append(f"<Cpt>{row.get('credit', row.get('Crd', row.get('Cpt', 0)))}</Cpt>")
        parts.append(f"<Tec>{row.get('teacher_name', row.get('Tec', ''))}</Tec>")
        parts.append(f"<Pla>{row.get('location', row.get('Pla', ''))}</Pla>")
        parts.append("<Share>Y</Share>")
        parts.append("</class>")
    parts.append("</Classes>")
    return "".join(parts)


def infer_source_college(course_id: str) -> str:
    cid = (course_id or "").strip().upper()
    if cid.startswith("A"):
        return "A"
    if cid.startswith("B"):
        return "B"
    if cid.startswith("C"):
        return "C"
    return "UNKNOWN"


def parse_cross_department_choice(data: bytes) -> tuple[dict[str, str], dict[str, str]]:
    root = ET.fromstring(data)
    student_node = root.find("Student")
    choice_node = root.find("Choice")
    if student_node is None or choice_node is None:
        raise ValueError("缺少 Student 或 Choice 节点")

    student = {
        "Sno": (student_node.findtext("Sno") or student_node.findtext("学号") or "").strip(),
        "Snn": (student_node.findtext("Snm") or student_node.findtext("姓名") or "").strip(),
        "Sex": (student_node.findtext("Sex") or student_node.findtext("性别") or "").strip(),
        "Sde": (
            student_node.findtext("Sde")
            or student_node.findtext("院系")
            or student_node.findtext("专业")
            or ""
        ).strip(),
    }
    choice = {
        "Cno": (
            choice_node.findtext("Cno")
            or choice_node.findtext("课程编号")
            or choice_node.findtext("cid")
            or ""
        ).strip(),
        "Sno": (
            choice_node.findtext("Sno")
            or choice_node.findtext("学生编号")
            or choice_node.findtext("学号")
            or choice_node.findtext("sid")
            or ""
        ).strip(),
        "Grd": (
            choice_node.findtext("Grd")
            or choice_node.findtext("成绩")
            or choice_node.findtext("得分")
            or choice_node.findtext("score")
            or "0"
        ).strip(),
    }
    if not student["Sno"] or not choice["Cno"] or not choice["Sno"]:
        raise ValueError("学生或选课信息不完整")
    return student, choice


def build_cross_department_choice_xml(
    student: dict[str, str],
    choice: dict[str, str],
) -> bytes:
    root = ET.Element("CrossDepartmentChoice")
    student_elem = ET.SubElement(root, "Student")
    for tag in ("Sno", "Snm", "Sex", "Sde"):
        ET.SubElement(student_elem, tag).text = student.get(tag, "")
    choice_elem = ET.SubElement(root, "Choice")
    ET.SubElement(choice_elem, "Cno").text = choice.get("Cno", "")
    ET.SubElement(choice_elem, "Sno").text = choice.get("Sno", student.get("Sno", ""))
    ET.SubElement(choice_elem, "Grd").text = choice.get("Grd", "0")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def parse_shared_courses_response(xml_bytes: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    code = (root.findtext("Code") or "").strip()
    if code and code != "200":
        msg = root.findtext("Message") or "获取共享课程失败"
        raise RuntimeError(msg)

    data = root.find("Data")
    if data is None:
        return []

    classes = data.find("Classes")
    if classes is None:
        return []

    rows: list[dict[str, Any]] = []
    for cls in classes.findall("class"):
        cno = (cls.findtext("Cno") or cls.findtext("课程编号") or "").strip()
        if not cno:
            continue
        college = infer_source_college(cno)
        if college == COLLEGE_C:
            continue
        rows.append(
            {
                "source_college": college,
                "Cno": cno,
                "Cnn": (cls.findtext("Cnm") or cls.findtext("Cnn") or cls.findtext("课程名称") or "").strip(),
                "Crd": int(cls.findtext("Cpt") or cls.findtext("学分") or cls.findtext("Crd") or "0"),
                "Cpt": int(cls.findtext("Ctm") or cls.findtext("课时") or "16"),
                "Tec": (cls.findtext("Tec") or cls.findtext("授课老师") or "待定").strip(),
                "Pla": (cls.findtext("Pla") or cls.findtext("授课地点") or "待定").strip(),
            }
        )
    return rows


def parse_response_code(xml_bytes: bytes) -> tuple[str, str]:
    root = ET.fromstring(xml_bytes)
    return (root.findtext("Code") or "").strip(), (root.findtext("Message") or "").strip()


class IntegrationClient:
    """调用集成服务器 XML API（与院系 A 一致）。"""

    def __init__(self, base_url: str = DEFAULT_INTEGRATION_URL, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_shared_courses(self) -> list[dict[str, Any]]:
        resp = requests.get(
            self._url("/api/integrated/course/shared"),
            headers={"SourceSystem": COLLEGE_C},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        rows = parse_shared_courses_response(resp.content)
        if not rows:
            root = ET.fromstring(resp.content)
            msg = (root.findtext("Message") or "").strip()
            if msg and "失败" in msg:
                raise RuntimeError(f"集成服务器：{msg}（请先启动院系 A：8081）")
        return rows

    def choose_course(
        self,
        student: dict[str, str],
        course_id: str,
        destination: str,
        grade: str = "0",
    ) -> tuple[str, str]:
        choice = {"Cno": course_id, "Sno": student["Sno"], "Grd": grade}
        xml_body = build_cross_department_choice_xml(student, choice)
        resp = requests.post(
            self._url("/api/integrated/course/choose"),
            data=xml_body,
            headers={
                "Content-Type": "application/xml; charset=UTF-8",
                "SourceSystem": COLLEGE_C,
                "DestinationSystem": destination.upper(),
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return parse_response_code(resp.content)

    def drop_course(
        self,
        student: dict[str, str],
        course_id: str,
        destination: str,
    ) -> tuple[str, str]:
        choice = {"Cno": course_id, "Sno": student["Sno"], "Grd": "-1"}
        xml_body = build_cross_department_choice_xml(student, choice)
        resp = requests.post(
            self._url("/api/integrated/course/drop"),
            data=xml_body,
            headers={
                "Content-Type": "application/xml; charset=UTF-8",
                "SourceSystem": COLLEGE_C,
                "DestinationSystem": destination.upper(),
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return parse_response_code(resp.content)

    def get_statistics(self) -> dict[str, Any]:
        resp = requests.get(self._url("/api/integrated/statistics"), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()


def integrated_course_to_import_row(course: dict[str, Any]) -> dict[str, Any]:
    college = str(course.get("source_college", course.get("college", course.get("ccollege", "")))).upper()
    course_id = str(course.get("course_id", course.get("Cno", course.get("cid", course.get("id", "")))))
    if not college or college == "UNKNOWN":
        college = infer_source_college(course_id)
    credit = course.get("credit", course.get("Crd", course.get("Cpt", course.get("ccredit", "0"))))
    class_hours = course.get("class_hours", course.get("Ctm", course.get("Cpt", course.get("hour", "16"))))
    return {
        "source_college": college,
        "course_id": course_id,
        "course_name": str(
            course.get("course_name", course.get("Cnn", course.get("Cnm", course.get("cname", course.get("name", "")))))
        ),
        "credit": str(credit),
        "class_hours": str(class_hours),
        "teacher_name": str(course.get("teacher_name", course.get("Tec", course.get("teacher", "待定")))),
        "location": str(course.get("location", course.get("Pla", course.get("place", "待定")))),
    }


class IntegrationProviderServer:
    """供集成服务器回调的 internal XML API（端口默认 8083）。"""

    def __init__(self, db, port: int = DEFAULT_PROVIDER_PORT):
        self.db = db
        self.port = port
        self.app = self._create_app()
        self._thread: threading.Thread | None = None

    def _create_app(self) -> Flask:
        app = Flask(__name__)

        @app.get("/api/internal/course/shared")
        def internal_shared_courses():
            courses = self.db.get_shared_courses()
            data_xml = courses_to_internal_xml(courses)
            return Response(
                build_xml_response(200, "获取共享课程列表成功", data_xml),
                mimetype="application/xml; charset=utf-8",
            )

        @app.post("/api/internal/course/choose")
        def internal_choose():
            try:
                student, choice = parse_cross_department_choice(request.data)
            except ValueError as exc:
                return Response(
                    build_xml_response(400, str(exc)),
                    status=400,
                    mimetype="application/xml; charset=utf-8",
                )

            source_college = request.headers.get("SourceSystem") or infer_source_college(choice["Sno"])
            if source_college == COLLEGE_C:
                source_college = infer_source_college(choice["Sno"])
                if source_college == COLLEGE_C:
                    source_college = "UNKNOWN"

            course_rows = self.db.execute(
                "SELECT course_name, share_flag FROM course WHERE course_id=%s AND dept_no=%s AND group_no=%s",
                (choice["Cno"], COLLEGE_C, GROUP_NO),
                fetch=True,
            )
            if not course_rows:
                return Response(
                    build_xml_response(400, "课程不存在"),
                    status=400,
                    mimetype="application/xml; charset=utf-8",
                )
            if str(course_rows[0].get("share_flag", "")).upper() != "Y":
                return Response(
                    build_xml_response(400, "该课程未对外共享，外院学生无法选修"),
                    status=400,
                    mimetype="application/xml; charset=utf-8",
                )
            course_name = course_rows[0]["course_name"]
            row = {
                "source_college": source_college,
                "student_id": choice["Sno"],
                "student_name": student.get("Snn", ""),
                "course_id": choice["Cno"],
                "course_name": course_name,
                "term_name": "2025-2026-2",
                "status": "跨校已选",
            }
            try:
                self.db.import_inbound_selections([row], "integration-server")
            except Exception as exc:
                return Response(
                    build_xml_response(400, str(exc)),
                    status=400,
                    mimetype="application/xml; charset=utf-8",
                )
            return Response(
                build_xml_response(200, "跨系选课成功"),
                mimetype="application/xml; charset=utf-8",
            )

        @app.post("/api/internal/course/drop")
        def internal_drop():
            try:
                _, choice = parse_cross_department_choice(request.data)
            except ValueError as exc:
                return Response(
                    build_xml_response(400, str(exc)),
                    status=400,
                    mimetype="application/xml; charset=utf-8",
                )

            updated = self.db.execute(
                "UPDATE inbound_cross_enrollments SET status='已退选' "
                "WHERE student_id=%s AND course_id=%s AND dept_no=%s AND group_no=%s",
                (choice["Cno"], choice["Sno"], DEPT_NO, GROUP_NO),
            )
            if updated == 0:
                return Response(
                    build_xml_response(400, "未找到对应选课记录"),
                    status=400,
                    mimetype="application/xml; charset=utf-8",
                )
            return Response(
                build_xml_response(200, "跨系退课成功"),
                mimetype="application/xml; charset=utf-8",
            )

        @app.get("/api/internal/statistics")
        def internal_statistics():
            stats = self.db.get_local_stats()
            return jsonify(
                {
                    "college": COLLEGE_C,
                    "students": stats["students"],
                    "courses": stats["courses"],
                    "enrollments": stats["enrollments"],
                }
            )

        return app

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._thread = threading.Thread(
            target=lambda: self.app.run(
                host="0.0.0.0",
                port=self.port,
                threaded=True,
                use_reloader=False,
            ),
            daemon=True,
        )
        self._thread.start()
