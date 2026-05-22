package edu.integration.b.controller;

import edu.integration.b.xml.ResponseXml;
import edu.integration.b.web.ApiResponse;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(HttpMessageNotReadableException.class)
  public ResponseXml xmlParseError(HttpMessageNotReadableException ex) {
    return ResponseXml.badRequest("XML解析失败：" + ex.getMostSpecificCause().getMessage());
  }

  @ExceptionHandler(IllegalArgumentException.class)
  public ApiResponse<Void> badArgs(IllegalArgumentException ex) {
    return ApiResponse.badRequest(ex.getMessage());
  }

  @ExceptionHandler(Exception.class)
  public ResponseXml unknown(Exception ex) {
    return ResponseXml.badRequest("服务器异常：" + ex.getMessage());
  }
}

