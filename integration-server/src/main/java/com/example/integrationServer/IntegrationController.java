package com.example.integrationServer;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/integrated")
public class IntegrationController {

    @Autowired
    private XmlService xmlService;

    @Autowired
    private RestTemplate restTemplate;

    @Value("${servers.A.url}")
    private String serverAUrl;

    @Value("${servers.B.url}")
    private String serverBUrl;

    @Value("${servers.C.url}")
    private String serverCUrl;

    // unified format → target server's class format
    private static final Map<String, String> CLASS_TO = Map.of(
            "A", "classToA.xsl", "B", "classToB.xsl", "C", "classToC.xsl"
    );


    /**
     * GET /api/integrated/course/shared
     * Fetches shared courses from all other departments (excluding requester),
     * transforms each to unified format, merges and returns.
     */
    @GetMapping(value = "/course/shared", produces = "application/xml;charset=UTF-8")
    public String getSharedCourses(@RequestHeader("SourceSystem") String source) {
        Map<String, String> serverUrls = Map.of("A", serverAUrl, "B", serverBUrl, "C", serverCUrl);

        StringBuilder mergedClasses = new StringBuilder();
        List<String> errors = new ArrayList<>();

        for (Map.Entry<String, String> entry : serverUrls.entrySet()) {
            String system = entry.getKey();
            if (system.equals(source)) continue;

            try {
                String url = entry.getValue() + "/api/internal/course/shared";
                ResponseEntity<String> resp = restTemplate.getForEntity(url, String.class);
                String body = resp.getBody();
                if (body == null || !resp.getStatusCode().is2xxSuccessful()) continue;

                // Extract Data content from Response wrapper
                String dataXml = extractData(body);
                if (dataXml == null || dataXml.isBlank()) continue;

                // Transform source format → unified format → requester's format
                String unified = xmlService.transform(dataXml, "formatClass.xsl");
                xmlService.validate(unified, "formatClass.xsd");
                String converted = xmlService.transform(unified, CLASS_TO.get(source));
                String inner = extractInnerElements(converted, "Classes");
                mergedClasses.append(inner);
            } catch (Exception e) {
                errors.add(system + ": " + e.getMessage());
            }
        }

        if (mergedClasses.isEmpty()) {
            String msg = errors.isEmpty() ? "暂无共享课程" : "获取失败: " + String.join("; ", errors);
            return xmlService.buildResponse("200", msg, "<Classes/>");
        }

        String data = "<Classes>" + mergedClasses + "</Classes>";
        return xmlService.buildResponse("200", "获取共享课程列表成功", data);
    }

    /**
     * POST /api/integrated/course/choose
     * Receives cross-department course selection, transforms to target format, forwards.
     */
    @PostMapping(value = "/course/choose",
            consumes = "application/xml;charset=UTF-8",
            produces = "application/xml;charset=UTF-8")
    public String chooseCourse(
            @RequestHeader("SourceSystem") String source,
            @RequestHeader("DestinationSystem") String destination,
            @RequestBody String body) {
        return forwardCrossCourse(source, destination, body, "choose");
    }

    /**
     * POST /api/integrated/course/drop
     * 跨院系退选：格式转换后转发至目标院系 /api/internal/course/drop
     */
    @PostMapping(value = "/course/drop",
            consumes = "application/xml;charset=UTF-8",
            produces = "application/xml;charset=UTF-8")
    public String dropCourse(
            @RequestHeader("SourceSystem") String source,
            @RequestHeader("DestinationSystem") String destination,
            @RequestBody String body) {
        return forwardCrossCourse(source, destination, body, "drop");
    }

    /**
     * GET /api/integrated/statistics
     * 汇总各院系 /api/internal/statistics 返回的 JSON 统计
     */
    @GetMapping(value = "/statistics", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, Object> getStatistics() {
        Map<String, String> serverUrls = Map.of("A", serverAUrl, "B", serverBUrl, "C", serverCUrl);
        int students = 0;
        int courses = 0;
        int enrollments = 0;
        List<String> colleges = new ArrayList<>();
        List<String> errors = new ArrayList<>();

        for (Map.Entry<String, String> entry : serverUrls.entrySet()) {
            try {
                String url = entry.getValue() + "/api/internal/statistics";
                ResponseEntity<Map> resp = restTemplate.getForEntity(url, Map.class);
                Map<?, ?> body = resp.getBody();
                if (body == null || !resp.getStatusCode().is2xxSuccessful()) {
                    errors.add(entry.getKey() + ": 无响应");
                    continue;
                }
                students += toInt(body.get("students"));
                courses += toInt(body.get("courses"));
                enrollments += toInt(body.get("enrollments"));
                colleges.add(entry.getKey());
            } catch (Exception e) {
                errors.add(entry.getKey() + ": " + e.getMessage());
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("students", students);
        result.put("studentCount", students);
        result.put("courses", courses);
        result.put("courseCount", courses);
        result.put("enrollments", enrollments);
        result.put("selectionCount", enrollments);
        result.put("colleges", colleges);
        if (!errors.isEmpty()) {
            result.put("warnings", errors);
        }
        return result;
    }

    private String forwardCrossCourse(String source, String destination, String body, String action) {
        Map<String, String> serverUrls = Map.of("A", serverAUrl, "B", serverBUrl, "C", serverCUrl);

        if (!serverUrls.containsKey(destination)) {
            return xmlService.buildResponse("400", "未知目标院系: " + destination, null);
        }

        try {
            if (!body.contains("<Student>") || !body.contains("<Choice>")) {
                return xmlService.buildResponse("400", "XML格式校验失败：缺少Student或Choice节点", null);
            }

            String studentFrag = extractElement(body, "Student");
            String choiceFrag = extractElement(body, "Choice");

            String studentsXml = "<Students><Student>" + studentFrag + "</Student></Students>";
            String choicesXml = "<choices><choice>" + choiceFrag + "</choice></choices>";

            String uniStudents = xmlService.transform(studentsXml, "formatStudent.xsl");
            String uniChoices = xmlService.transform(choicesXml, "formatClassChoice.xsl");

            String destStudents = xmlService.transform(uniStudents, "studentTo" + destination + ".xsl");
            String destChoices = xmlService.transform(uniChoices, "choiceTo" + destination + ".xsl");

            String destStudentInner = extractElement(destStudents, "student");
            String destChoiceInner = extractElement(destChoices, "choice");
            String transformed = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<CrossDepartmentChoice>\n    <Student>"
                    + destStudentInner + "</Student>\n    <Choice>" + destChoiceInner + "</Choice>\n</CrossDepartmentChoice>";

            String url = serverUrls.get(destination) + "/api/internal/course/" + action;
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.parseMediaType("application/xml;charset=UTF-8"));
            headers.set("SourceSystem", source);
            HttpEntity<String> request = new HttpEntity<>(transformed, headers);

            ResponseEntity<String> resp = restTemplate.postForEntity(url, request, String.class);
            return resp.getBody() != null ? resp.getBody()
                    : xmlService.buildResponse("500", "目标院系无响应", null);

        } catch (Exception e) {
            return xmlService.buildResponse("400", "处理失败: " + e.getMessage(), null);
        }
    }

    private static int toInt(Object value) {
        if (value == null) {
            return 0;
        }
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        try {
            return Integer.parseInt(value.toString());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    /**
     * POST /api/integrated/transform  (existing endpoint, kept for compatibility)
     */
    @PostMapping(value = "/transform",
            consumes = "application/xml",
            produces = "application/xml;charset=UTF-8")
    public String transformStudent(@RequestBody String rawXml) {
        try {
            String transformed = xmlService.transform(rawXml, "formatStudent.xsl");
            xmlService.validate(transformed, "formatStudent.xsd");
            return transformed;
        } catch (Exception e) {
            return "<error>" + e.getMessage() + "</error>";
        }
    }

    // Extract content inside <Data>...</Data>
    private String extractData(String xml) {
        int start = xml.indexOf("<Data>");
        int end = xml.indexOf("</Data>");
        if (start < 0 || end < 0) return xml;
        return xml.substring(start + 6, end).trim();
    }

    // Extract inner elements of a root tag (e.g. content inside <classes>)
    private String extractInnerElements(String xml, String rootTag) {
        int start = xml.indexOf("<" + rootTag + ">");
        int end = xml.lastIndexOf("</" + rootTag + ">");
        if (start < 0 || end < 0) return xml;
        return xml.substring(start + rootTag.length() + 2, end).trim();
    }

    // Extract the inner content of the first occurrence of a tag (e.g. <Student>...</Student> → inner)
    private String extractElement(String xml, String tag) {
        int start = xml.indexOf("<" + tag + ">");
        int end = xml.indexOf("</" + tag + ">");
        if (start < 0 || end < 0) return "";
        return xml.substring(start + tag.length() + 2, end).trim();
    }
}
