package edu.integration.b.controller;

import edu.integration.b.service.StatsService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/internal")
public class InternalStatsController {
  private final StatsService statsService;

  public InternalStatsController(StatsService statsService) {
    this.statsService = statsService;
  }

  @GetMapping("/statistics")
  public Map<String, Object> statistics() {
    return statsService.integrationStats();
  }
}
