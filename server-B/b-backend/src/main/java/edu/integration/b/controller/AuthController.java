package edu.integration.b.controller;

import edu.integration.b.service.AuthService;
import edu.integration.b.web.ApiResponse;
import edu.integration.b.web.dto.LoginRequest;
import java.util.Map;
import java.util.Optional;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
  private final AuthService authService;

  public AuthController(AuthService authService) {
    this.authService = authService;
  }

  @PostMapping("/login")
  public ApiResponse<Map<String, Object>> login(@RequestBody LoginRequest req) {
    if (req == null) return ApiResponse.badRequest("请求体不能为空");
    String type = req.getType() == null ? "" : req.getType().trim().toUpperCase();
    String username = req.getUsername() == null ? "" : req.getUsername().trim();
    String password = req.getPassword() == null ? "" : req.getPassword().trim();
    if (username.isEmpty() || password.isEmpty()) return ApiResponse.badRequest("用户名或密码不能为空");

    if ("ADMIN".equals(type)) {
      Optional<Map<String, Object>> ok = authService.loginAdmin(username, password);
      return ok.map(d -> ApiResponse.ok("登录成功", d)).orElseGet(() -> ApiResponse.badRequest("账号或密码错误"));
    }

    // 默认按学生登录
    Optional<Map<String, Object>> ok = authService.loginStudent(username, password);
    return ok.map(d -> ApiResponse.ok("登录成功", d)).orElseGet(() -> ApiResponse.badRequest("账号或密码错误"));
  }
}

