package com.example.integrationServer;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
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

        Map<String, String> serverUrls = Map.of("A", serverAUrl, "B", serverBUrl, "C", serverCUrl);

        if (!serverUrls.containsKey(destination)) {
            return xmlService.buildResponse("400", "未知目标院系: " + destination, null);
        }

        try {
            if (!body.contains("<Student>") || !body.contains("<Choice>")) {
                return xmlService.buildResponse("400", "XML格式校验失败：缺少Student或Choice节点", null);
            }

            // 1. Extract <Student> and <Choice> fragments from CrossDepartmentChoice
            String studentFrag = extractElement(body, "Student");
            String choiceFrag = extractElement(body, "Choice");

            // 2. Wrap into list roots expected by format XSLs
            String studentsXml = "<Students><Student>" + studentFrag + "</Student></Students>";
            String choicesXml = "<choices><choice>" + choiceFrag + "</choice></choices>";
            
            // 3. source format → unified format
            String uniStudents = xmlService.transform(studentsXml, "formatStudent.xsl");
            String uniChoices = xmlService.transform(choicesXml, "formatClassChoice.xsl");

            // 4. unified format → destination format
            String destStudents = xmlService.transform(uniStudents, "studentTo" + destination + ".xsl");
            String destChoices = xmlService.transform(uniChoices, "choiceTo" + destination + ".xsl");

            // 5. Re-assemble CrossDepartmentChoice for destination server
            String destStudentInner = extractElement(destStudents, "student");
            String destChoiceInner = extractElement(destChoices, "choice");
            String transformed = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<CrossDepartmentChoice>\n    <Student>"
                    + destStudentInner + "</Student>\n    <Choice>" + destChoiceInner + "</Choice>\n</CrossDepartmentChoice>";

            // Forward to destination server
            String url = serverUrls.get(destination) + "/api/internal/course/choose";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.parseMediaType("application/xml;charset=UTF-8"));
            HttpEntity<String> request = new HttpEntity<>(transformed, headers);

            ResponseEntity<String> resp = restTemplate.postForEntity(url, request, String.class);
            return resp.getBody() != null ? resp.getBody()
                    : xmlService.buildResponse("500", "目标院系无响应", null);

        } catch (Exception e) {
            return xmlService.buildResponse("400", "处理失败: " + e.getMessage(), null);
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
