package edu.integration.b.service;

import java.util.Collections;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;

@Service
public class IntegrationProxyService {
  private final RestTemplate restTemplate;
  private final String integrationBaseUrl;

  public IntegrationProxyService(RestTemplate restTemplate, @Value("${integration.server.base-url}") String integrationBaseUrl) {
    this.restTemplate = restTemplate;
    this.integrationBaseUrl = integrationBaseUrl;
  }

  public String fetchSharedCourses(String sourceSystem) {
    HttpHeaders headers = new HttpHeaders();
    headers.set("SourceSystem", normalizeSystem(sourceSystem, "B"));
    headers.setAccept(Collections.singletonList(MediaType.APPLICATION_XML));
    try {
      ResponseEntity<String> response = restTemplate.exchange(
          integrationBaseUrl + "/api/integrated/course/shared",
          HttpMethod.GET,
          new HttpEntity<>(headers),
          String.class);
      return response.getBody() == null ? xmlErrorResponse("500", "集成服务器无响应") : response.getBody();
    } catch (HttpStatusCodeException ex) {
      return ex.getResponseBodyAsString();
    }
  }

  public String submitCourseChoice(String sourceSystem, String destinationSystem, String requestXml, boolean drop) {
    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.parseMediaType("application/xml;charset=UTF-8"));
    headers.setAccept(Collections.singletonList(MediaType.APPLICATION_XML));
    headers.set("SourceSystem", normalizeSystem(sourceSystem, "B"));
    headers.set("DestinationSystem", normalizeSystem(destinationSystem, "A"));

    String path = drop ? "/api/integrated/course/drop" : "/api/integrated/course/choose";
    try {
      ResponseEntity<String> response = restTemplate.exchange(
          integrationBaseUrl + path,
          HttpMethod.POST,
          new HttpEntity<>(requestXml, headers),
          String.class);
      return response.getBody() == null ? xmlErrorResponse("500", "集成服务器无响应") : response.getBody();
    } catch (HttpStatusCodeException ex) {
      return ex.getResponseBodyAsString();
    }
  }

  private String normalizeSystem(String candidate, String fallback) {
    if (candidate == null) {
      return fallback;
    }
    String value = candidate.trim();
    if (value.isEmpty()) {
      return fallback;
    }
    if ("Integrated".equalsIgnoreCase(value) || "A".equalsIgnoreCase(value) || "B".equalsIgnoreCase(value) || "C".equalsIgnoreCase(value)) {
      return value;
    }
    return fallback;
  }

  private String xmlErrorResponse(String code, String message) {
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        + "<Response><Code>"
        + code
        + "</Code><Message>"
        + message
        + "</Message><Data></Data></Response>";
  }
}