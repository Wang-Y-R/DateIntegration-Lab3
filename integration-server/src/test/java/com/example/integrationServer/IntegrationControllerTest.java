package com.example.integrationServer;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.HttpEntity;
import org.springframework.http.ResponseEntity;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.client.RestTemplate;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class IntegrationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private RestTemplate restTemplate;

    // ── 共享课程 ──────────────────────────────────────────────────

    /**
     * A 院系请求共享课程：B、C 返回各自本地格式，集成服务器应转换为 A 院系格式（中文字段）后合并返回。
     * 预期 A 格式字段：课程编号、课程名称、学分、授课老师、授课地点
     */
    @Test
    void getSharedCourses_mergesAndConvertsToAFormat() throws Exception {
        String bResponse = wrapData("<Classes><class>" +
                "<编号>B0001</编号><名称>高等数学</名称><课时>48</课时>" +
                "<学分>3</学分><老师>王老师</老师><地点>教学楼101</地点><共享>Y</共享>" +
                "</class></Classes>");
        String cResponse = wrapData("<Classes><class>" +
                "<Cno>C001</Cno><Cnm>线性代数</Cnm><Ctm>32</Ctm>" +
                "<Cpt>2</Cpt><Tec>李老师</Tec><Pla>理学楼202</Pla><Share>Y</Share>" +
                "</class></Classes>");

        when(restTemplate.getForEntity(contains("8082"), eq(String.class))).thenReturn(ResponseEntity.ok(bResponse));
        when(restTemplate.getForEntity(contains("8083"), eq(String.class))).thenReturn(ResponseEntity.ok(cResponse));

        String result = mockMvc.perform(get("/api/integrated/course/shared").header("SourceSystem", "A"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        System.out.println("=== [共享课程] 集成服务器返回给 A 院系的 XML ===\n" + result);

        assertTrue(result.contains("<Code>200</Code>"), "响应码应为200");
        // A 格式字段验证
        assertTrue(result.contains("课程编号"), "应包含A格式字段: 课程编号");
        assertTrue(result.contains("课程名称"), "应包含A格式字段: 课程名称");
        assertTrue(result.contains("B0001"), "应包含B院系课程编号 B0001");
        assertTrue(result.contains("高等数学"), "应包含B院系课程名称");
        assertTrue(result.contains("C001"), "应包含C院系课程编号 C001");
        assertTrue(result.contains("线性代数"), "应包含C院系课程名称");
        // 不应出现 B/C 的原始字段名
        assertTrue(!result.contains("<编号>"), "不应包含B原始字段: 编号");
        assertTrue(!result.contains("<Cno>"), "不应包含C原始字段: Cno");
    }

    /**
     * C 院系请求共享课程：A、B 返回各自本地格式，集成服务器应转换为 C 院系格式（英文字段）后合并返回。
     * 预期 C 格式字段：Cno、Cnm、Cpt、Tec、Pla
     */
    @Test
    void getSharedCourses_convertsToRequestingSystemFormat_C() throws Exception {
        String aResponse = wrapData("<Classes><class>" +
                "<课程编号>A0000001</课程编号><课程名称>数据结构</课程名称>" +
                "<学分>4</学分><授课老师>陈老师</授课老师><授课地点>信息楼301</授课地点><共享>Y</共享>" +
                "</class></Classes>");

        when(restTemplate.getForEntity(contains("8081"), eq(String.class))).thenReturn(ResponseEntity.ok(aResponse));
        when(restTemplate.getForEntity(contains("8082"), eq(String.class))).thenReturn(ResponseEntity.ok(wrapData("<Classes/>")));

        String result = mockMvc.perform(get("/api/integrated/course/shared").header("SourceSystem", "C"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        System.out.println("=== [共享课程] 集成服务器返回给 C 院系的 XML ===\n" + result);

        assertTrue(result.contains("<Code>200</Code>"));
        assertTrue(result.contains("Cno"), "应包含C格式字段: Cno");
        assertTrue(result.contains("Cnm"), "应包含C格式字段: Cnm");
        assertTrue(result.contains("A0000001"), "应包含A院系课程编号");
        assertTrue(!result.contains("课程编号"), "不应包含A原始字段: 课程编号");
    }

//     @Test
    void getSharedCourses_whenAllRemotesFail_returns200() throws Exception {
        when(restTemplate.getForEntity(anyString(), eq(String.class)))
                .thenThrow(new RuntimeException("connection refused"));

        String result = mockMvc.perform(get("/api/integrated/course/shared").header("SourceSystem", "A"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        System.out.println("=== [共享课程] 所有远端失败时的响应 ===\n" + result);
        assertTrue(result.contains("<Code>200</Code>"));
    }

    // ── 跨系选课 ──────────────────────────────────────────────────

    /**
     * A 院系学生选 B 院系课程：集成服务器应将统一格式转换为 B 院系格式后转发。
     * 预期 B 格式：学生字段 学号/姓名/性别/专业，选课字段 课程编号/学号/得分
     */
    @Test
    void chooseCourse_AStudentChooseBCourse_transformsToB() throws Exception {
        // Capture what the integration server sends to B
        final String[] capturedPayload = {null};
        when(restTemplate.postForEntity(contains("8082"), any(HttpEntity.class), eq(String.class)))
                .thenAnswer(inv -> {
                    HttpEntity<?> req = inv.getArgument(1);
                    capturedPayload[0] = req.getBody().toString();
                    return ResponseEntity.ok(wrap200("跨系选课成功"));
                });

        String body = """
                <?xml version="1.0" encoding="UTF-8"?>
                <CrossDepartmentChoice>
                    <Student>
                        <学号>A202300</学号>
                        <姓名>张三</姓名>
                        <性别>男</性别>
                        <院系>软件学院</院系>
                    </Student>
                    <Choice>
                        <学生编号>A2023001</学生编号>
                        <课程编号>B0001</课程编号>
                        <成绩>0</成绩>
                    </Choice>
                </CrossDepartmentChoice>
                """;

        String result = mockMvc.perform(post("/api/integrated/course/choose")
                        .contentType("application/xml;charset=UTF-8")
                        .header("SourceSystem", "A")
                        .header("DestinationSystem", "B")
                        .content(body))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        System.out.println("=== [跨系选课] 集成服务器转发给 B 院系的 XML ===\n" + capturedPayload[0]);
        System.out.println("=== [跨系选课] 集成服务器返回给 A 院系的响应 ===\n" + result);
        // 若 capturedPayload 为 null，说明转换抛异常被吞，打印响应中的错误信息
        if (capturedPayload[0] == null) {
            throw new AssertionError("集成服务器未转发请求到B，实际响应: " + result);
        }

        assertTrue(result.contains("<Code>200</Code>"), "最终响应码应为200");
        // B 格式字段验证
        assertTrue(capturedPayload[0].contains("学号"), "B格式应包含: 学号");
        assertTrue(capturedPayload[0].contains("专业"), "B格式应包含: 专业 (not 院系)");
        assertTrue(capturedPayload[0].contains("得分"), "B格式选课应包含: 得分");
        assertTrue(capturedPayload[0].contains("A2023001"), "应包含学号");
        assertTrue(!capturedPayload[0].contains("<id>"), "不应包含统一格式字段: id");
        assertTrue(!capturedPayload[0].contains("<sid>"), "不应包含统一格式字段: sid");
    }

    /**
     * A 院系学生选 C 院系课程：集成服务器应将统一格式转换为 C 院系格式后转发。
     * 预期 C 格式：学生字段 Sno/Snm/Sex/Sde，选课字段 Cno/Sno/Grd
     */
    @Test
    void chooseCourse_AStudentChooseCCourse_transformsToC() throws Exception {
        final String[] capturedPayload = {null};
        when(restTemplate.postForEntity(contains("8083"), any(HttpEntity.class), eq(String.class)))
                .thenAnswer(inv -> {
                    capturedPayload[0] = ((HttpEntity<?>) inv.getArgument(1)).getBody().toString();
                    return ResponseEntity.ok(wrap200("跨系选课成功"));
                });

        String body = """
                <?xml version="1.0" encoding="UTF-8"?>
                <CrossDepartmentChoice>
                    <Student>
                        <学号>A202300</学号>
                        <姓名>张三</姓名>
                        <性别>男</性别>
                        <院系>软件学院</院系>
                    </Student>
                    <Choice>
                        <学生编号>A2023001</学生编号>
                        <课程编号>B0001</课程编号>
                        <成绩>0</成绩>
                    </Choice>
                </CrossDepartmentChoice>
                """;

        String result = mockMvc.perform(post("/api/integrated/course/choose")
                        .contentType("application/xml;charset=UTF-8")
                        .header("SourceSystem", "A")
                        .header("DestinationSystem", "C")
                        .content(body))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        System.out.println("=== [跨系选课] 集成服务器转发给 C 院系的 XML ===\n" + capturedPayload[0]);
        System.out.println("=== [跨系选课] 集成服务器返回给 A 院系的响应 ===\n" + result);

        assertTrue(result.contains("<Code>200</Code>"));
        assertTrue(capturedPayload[0].contains("<Sno>"), "C格式应包含: Sno");
        assertTrue(capturedPayload[0].contains("<Snm>"), "C格式应包含: Snm");
        assertTrue(capturedPayload[0].contains("<Sde>"), "C格式应包含: Sde");
        assertTrue(capturedPayload[0].contains("<Grd>"), "C格式选课应包含: Grd");
        assertTrue(capturedPayload[0].contains("<Cno>"), "C格式选课应包含: Cno");
        assertTrue(!capturedPayload[0].contains("<id>"), "不应包含统一格式字段: id");
    }

    @Test
    void chooseCourse_missingStudentNode_returns400() throws Exception {
        String body = """
                <?xml version="1.0" encoding="UTF-8"?>
                <CrossDepartmentChoice>
                    <Choice><sid>A001</sid><cid>B0001</cid><score>0</score></Choice>
                </CrossDepartmentChoice>
                """;

        String result = mockMvc.perform(post("/api/integrated/course/choose")
                        .contentType("application/xml;charset=UTF-8")
                        .header("SourceSystem", "A")
                        .header("DestinationSystem", "B")
                        .content(body))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        System.out.println("=== [跨系选课] 缺少Student节点的响应 ===\n" + result);
        assertTrue(result.contains("<Code>400</Code>"));
    }

    @Test
    void chooseCourse_unknownDestination_returns400() throws Exception {
        String body = "<CrossDepartmentChoice><Student/><Choice/></CrossDepartmentChoice>";

        String result = mockMvc.perform(post("/api/integrated/course/choose")
                        .contentType("application/xml;charset=UTF-8")
                        .header("SourceSystem", "A")
                        .header("DestinationSystem", "X")
                        .content(body))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);

        System.out.println("=== [跨系选课] 未知目标院系的响应 ===\n" + result);
        assertTrue(result.contains("<Code>400</Code>"));
    }

    // ── helpers ───────────────────────────────────────────────────

    private String wrapData(String dataContent) {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Response><Code>200</Code>" +
                "<Message>获取共享课程列表成功</Message><Data>" + dataContent + "</Data></Response>";
    }

    private String wrap200(String message) {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Response><Code>200</Code>" +
                "<Message>" + message + "</Message><Data></Data></Response>";
    }
}
