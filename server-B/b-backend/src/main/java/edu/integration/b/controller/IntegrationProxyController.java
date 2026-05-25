package edu.integration.b.controller;

import edu.integration.b.service.IntegrationProxyService;
import org.springframework.http.MediaType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(value = "/api/proxy/integrated/course", produces = MediaType.APPLICATION_XML_VALUE)
public class IntegrationProxyController {
  private final IntegrationProxyService proxyService;
  private static final Logger log = LoggerFactory.getLogger(IntegrationProxyController.class);

  public IntegrationProxyController(IntegrationProxyService proxyService) {
    this.proxyService = proxyService;
  }

  @GetMapping(value = "/shared")
  public String sharedCourses(@RequestHeader(value = "SourceSystem", required = false) String sourceSystem) {
    log.info("proxy: sharedCourses called, SourceSystem={}", sourceSystem);
    String resp = proxyService.fetchSharedCourses(sourceSystem);
    log.info("proxy: sharedCourses returned length={}", resp == null ? 0 : resp.length());
    return resp;
  }

  @PostMapping(value = "/choose", consumes = MediaType.APPLICATION_XML_VALUE)
  public String choose(
      @RequestHeader(value = "SourceSystem", required = false) String sourceSystem,
      @RequestHeader(value = "DestinationSystem", required = false) String destinationSystem,
      @RequestBody String requestXml) {
    log.info("proxy: choose called SourceSystem={} DestinationSystem={} payloadLen={}", sourceSystem, destinationSystem,
        requestXml == null ? 0 : requestXml.length());
    String resp = proxyService.submitCourseChoice(sourceSystem, destinationSystem, requestXml, false);
    log.info("proxy: choose returned length={}", resp == null ? 0 : resp.length());
    return resp;
  }

  @PostMapping(value = "/drop", consumes = MediaType.APPLICATION_XML_VALUE)
  public String drop(
      @RequestHeader(value = "SourceSystem", required = false) String sourceSystem,
      @RequestHeader(value = "DestinationSystem", required = false) String destinationSystem,
      @RequestBody String requestXml) {
    log.info("proxy: drop called SourceSystem={} DestinationSystem={} payloadLen={}", sourceSystem, destinationSystem,
        requestXml == null ? 0 : requestXml.length());
    String resp = proxyService.submitCourseChoice(sourceSystem, destinationSystem, requestXml, true);
    log.info("proxy: drop returned length={}", resp == null ? 0 : resp.length());
    return resp;
  }
}