package edu.integration.b.controller;

import edu.integration.b.service.StatsService;
import edu.integration.b.web.ApiResponse;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/local")
public class StatsController {
  private final StatsService statsService;

  public StatsController(StatsService statsService) {
    this.statsService = statsService;
  }

  @GetMapping("/stats/overview")
  public ApiResponse<Map<String, Object>> overview() {
    return ApiResponse.ok("ok", statsService.overview());
  }
}

