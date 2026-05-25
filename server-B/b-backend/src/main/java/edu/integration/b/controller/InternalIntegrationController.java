package edu.integration.b.controller;

import edu.integration.b.service.InternalIntegrationService;
import edu.integration.b.xml.ResponseXml;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/internal/course")
public class InternalIntegrationController {
  private final InternalIntegrationService internalIntegrationService;

  public InternalIntegrationController(InternalIntegrationService internalIntegrationService) {
    this.internalIntegrationService = internalIntegrationService;
  }

  @GetMapping(value = "/shared", produces = MediaType.APPLICATION_XML_VALUE)
  public ResponseXml sharedCourses() {
    return internalIntegrationService.sharedCourses();
  }

  @PostMapping(value = "/choose", consumes = MediaType.APPLICATION_XML_VALUE, produces = MediaType.APPLICATION_XML_VALUE)
  public ResponseXml choose(@RequestBody String requestXml) {
    return internalIntegrationService.choose(requestXml);
  }

  @PostMapping(value = "/drop", consumes = MediaType.APPLICATION_XML_VALUE, produces = MediaType.APPLICATION_XML_VALUE)
  public ResponseXml drop(@RequestBody String requestXml) {
    return internalIntegrationService.drop(requestXml);
  }
}

