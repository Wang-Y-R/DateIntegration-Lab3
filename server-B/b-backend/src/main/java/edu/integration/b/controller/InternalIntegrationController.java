package edu.integration.b.controller;

import edu.integration.b.service.InternalIntegrationService;
import edu.integration.b.service.StatsService;
import edu.integration.b.xml.ClassesXml;
import edu.integration.b.xml.ResponseXml;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.Map;

@RestController
@RequestMapping("/api/internal/course")
public class InternalIntegrationController {
  private final InternalIntegrationService internalIntegrationService;
  private final StatsService statsService;
  private static final Logger log = LoggerFactory.getLogger(InternalIntegrationController.class);

  public InternalIntegrationController(
      InternalIntegrationService internalIntegrationService,
      StatsService statsService) {
    this.internalIntegrationService = internalIntegrationService;
    this.statsService = statsService;
  }

  @GetMapping(value = "/shared", produces = MediaType.APPLICATION_XML_VALUE)
  public String sharedCourses() {
    log.info("B internal /shared called");
    return internalIntegrationService.sharedCoursesXml();
  }

  @PostMapping(value = "/choose", consumes = MediaType.APPLICATION_XML_VALUE, produces = MediaType.APPLICATION_XML_VALUE)
  public ResponseXml choose(@RequestBody String requestXml) {
    return internalIntegrationService.choose(requestXml);
  }

  @PostMapping(value = "/drop", consumes = MediaType.APPLICATION_XML_VALUE, produces = MediaType.APPLICATION_XML_VALUE)
  public ResponseXml drop(@RequestBody String requestXml) {
    return internalIntegrationService.drop(requestXml);
  }

  @GetMapping(value = "/statistics", produces = MediaType.APPLICATION_JSON_VALUE)
  public Map<String, Object> statistics() {
    return statsService.integrationStats();
  }
}

