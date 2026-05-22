"""学院C与集成服务器的 HTTP 对接：JSON 客户端 + XML Provider 服务。"""

from __future__ import annotations

import threading
import xml.etree.ElementTree as ET
from typing import Any

import requests
from flask import Flask, Response, request

COLLEGE_C = "C"
DEFAULT_INTEGRATION_URL = "http://localhost:8080"
DEFAULT_PROVIDER_PORT = 5001


class IntegrationClient:
    def __init__(self, base_url: str = DEFAULT_INTEGRATION_URL, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_integrated_courses(self) -> list[dict[str, Any]]:
        resp = requests.get(self._url("/api/integrated/courses"), timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("courses", data.get("data", []))

    def submit_selection(
        self,
        sid: str,
        sname: str,
        scollege: str,
        cid: str,
        cname: str,
        ccollege: str,
    ) -> dict[str, Any]:
        payload = {
            "sid": sid,
            "sname": sname,
            "scollege": scollege,
            "cid": cid,
            "cname": cname,
            "ccollege": ccollege,
        }
        resp = requests.post(self._url("/api/integrated/select"), json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json() if resp.content else {"success": True}

    def drop_selection(self, sid: str, cid: str) -> dict[str, Any]:
        payload = {"sid": sid, "cid": cid}
        resp = requests.post(self._url("/api/integrated/drop"), json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json() if resp.content else {"success": True}

    def get_statistics(self) -> dict[str, Any]:
        resp = requests.get(self._url("/api/integrated/statistics"), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()


def courses_to_xml(courses: list[dict[str, Any]]) -> bytes:
    root = ET.Element("courseList", attrib={"college": COLLEGE_C})
    for row in courses:
        node = ET.SubElement(root, "course")
        ET.SubElement(node, "id").text = str(row.get("Cno", row.get("id", "")))
        ET.SubElement(node, "name").text = str(row.get("Cnn", row.get("name", "")))
        ET.SubElement(node, "credit").text = str(row.get("Crd", row.get("credit", 0)))
        ET.SubElement(node, "teacher").text = str(row.get("Tec", row.get("teacher", "")))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def parse_selection_xml(data: bytes) -> dict[str, str]:
    root = ET.fromstring(data)
    tag_map = {
        "studentId": "Sno",
        "studentName": "Snn",
        "studentCollege": "source_college",
        "courseId": "Cno",
        "courseName": "Cnn",
        "term": "term_name",
        "status": "status",
    }
    result: dict[str, str] = {}
    for xml_tag, field in tag_map.items():
        node = root.find(f".//{xml_tag}")
        if node is not None and node.text:
            result[field] = node.text.strip()
    if "Sno" not in result:
        for child in root:
            if child.tag in tag_map and child.text:
                result[tag_map[child.tag]] = child.text.strip()
    return result


def integrated_course_to_import_row(course: dict[str, Any]) -> dict[str, Any]:
    college = str(course.get("college", course.get("ccollege", "UNKNOWN"))).upper()
    return {
        "source_college": college,
        "Cno": str(course.get("cid", course.get("id", ""))),
        "Cnn": str(course.get("cname", course.get("name", ""))),
        "Crd": int(course.get("credit", course.get("ccredit", course.get("Crd", 0)))),
        "Cpt": int(course.get("hour", course.get("chour", course.get("Cpt", 16)))),
        "Tec": str(course.get("teacher", course.get("Tec", "待定"))),
        "Pla": str(course.get("place", course.get("Pla", "待定"))),
    }


class IntegrationProviderServer:
    def __init__(self, db, port: int = DEFAULT_PROVIDER_PORT):
        self.db = db
        self.port = port
        self.app = self._create_app()
        self._thread: threading.Thread | None = None

    def _create_app(self) -> Flask:
        app = Flask(__name__)

        @app.get("/api/provider/courses")
        def provider_courses():
            courses = self.db.get_shared_courses()
            xml_bytes = courses_to_xml(courses)
            return Response(xml_bytes, mimetype="application/xml")

        @app.post("/api/provider/receiveSelection")
        def provider_receive_selection():
            selection = parse_selection_xml(request.data)
            if not selection.get("Sno") or not selection.get("Cno"):
                return Response("缺少 studentId 或 courseId", status=400, mimetype="text/plain")
            source_college = selection.get("source_college", "UNKNOWN")
            cno = selection["Cno"]
            course_rows = self.db.execute(
                "SELECT Cnn FROM c_courses WHERE Cno=%s",
                (cno,),
                fetch=True,
            )
            cnn = selection.get("Cnn") or (course_rows[0]["Cnn"] if course_rows else cno)
            row = {
                "source_college": source_college,
                "Sno": selection["Sno"],
                "Snn": selection.get("Snn", ""),
                "Cno": cno,
                "Cnn": cnn,
                "term_name": selection.get("term_name", "2025-2026-2"),
                "status": selection.get("status", "已选"),
            }
            self.db.import_inbound_selections([row], "integration-server")
            return Response(
                ET.tostring(ET.Element("result", attrib={"status": "ok"}), encoding="utf-8"),
                mimetype="application/xml",
            )

        return app

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._thread = threading.Thread(
            target=lambda: self.app.run(host="0.0.0.0", port=self.port, threaded=True, use_reloader=False),
            daemon=True,
        )
        self._thread.start()
