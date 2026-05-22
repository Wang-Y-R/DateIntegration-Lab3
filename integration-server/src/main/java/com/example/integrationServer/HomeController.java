package com.example.integrationServer;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HomeController {

    @GetMapping(value = "/", produces = "text/html;charset=UTF-8")
    public String home() {
        return """
                <!DOCTYPE html>
                <html lang="zh-CN">
                <head>
                  <meta charset="UTF-8"/>
                  <title>集成教务服务器</title>
                  <style>
                    body { font-family: "Segoe UI", sans-serif; margin: 40px; line-height: 1.6; }
                    h1 { color: #17324d; }
                    code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }
                    li { margin: 8px 0; }
                    .ok { color: #059669; font-weight: bold; }
                  </style>
                </head>
                <body>
                  <h1>XML 集成教务服务器</h1>
                  <p class="ok">服务已启动（端口 8080）。根路径不是错误，请使用下方 API。</p>
                  <h2>主要接口</h2>
                  <ul>
                    <li><code>GET /api/integrated/course/shared</code> — Header: <code>SourceSystem: A|B|C</code></li>
                    <li><code>POST /api/integrated/course/choose</code> — XML，Headers: SourceSystem、DestinationSystem</li>
                    <li><code>POST /api/integrated/course/drop</code> — 跨院退选</li>
                    <li><code>GET /api/integrated/statistics</code> — 全院统计（JSON）</li>
                  </ul>
                  <h2>下游院系（application.yml）</h2>
                  <ul>
                    <li>A: <code>http://localhost:8081</code></li>
                    <li>B: <code>http://localhost:8082</code></li>
                    <li>C: <code>http://localhost:8083</code></li>
                  </ul>
                  <p>系统 C GUI 拉取共享课时，需同时启动院系 A 与系统 C（Internal API 8083）。</p>
                </body>
                </html>
                """;
    }

    @GetMapping("/health")
    public String health() {
        return "OK";
    }
}
