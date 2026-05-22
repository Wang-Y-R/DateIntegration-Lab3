package edu.integration.b.web;

public class ApiResponse<T> {
  private int code;
  private String message;
  private T data;

  public ApiResponse() {}

  public ApiResponse(int code, String message, T data) {
    this.code = code;
    this.message = message;
    this.data = data;
  }

  public static <T> ApiResponse<T> ok(String message, T data) {
    return new ApiResponse<>(200, message, data);
  }

  public static <T> ApiResponse<T> ok(String message) {
    return new ApiResponse<>(200, message, null);
  }

  public static <T> ApiResponse<T> badRequest(String message) {
    return new ApiResponse<>(400, message, null);
  }

  public int getCode() {
    return code;
  }

  public String getMessage() {
    return message;
  }

  public T getData() {
    return data;
  }
}

