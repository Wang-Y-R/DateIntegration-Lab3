package edu.integration.b.controller;

import edu.integration.b.service.LocalAcademicService;
import edu.integration.b.web.ApiResponse;
import edu.integration.b.web.dto.ChooseRequest;
import edu.integration.b.web.dto.StudentProfileRequest;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/local")
public class LocalAcademicController {
  private final LocalAcademicService localAcademicService;

  public LocalAcademicController(LocalAcademicService localAcademicService) {
    this.localAcademicService = localAcademicService;
  }

  @GetMapping("/courses")
  public ApiResponse<List<Map<String, Object>>> listCourses() {
    return ApiResponse.ok("ok", localAcademicService.listCourses());
  }

  @GetMapping("/students")
  public ApiResponse<List<Map<String, Object>>> listStudents(@RequestParam(defaultValue = "50") int limit) {
    return ApiResponse.ok("ok", localAcademicService.listStudents(limit));
  }

  @GetMapping("/students/profile")
  public ApiResponse<Map<String, Object>> getStudentProfile(@RequestParam String sno) {
    return ApiResponse.ok("ok", localAcademicService.getStudentProfile(sno));
  }

  @PostMapping("/students/profile")
  public ApiResponse<Map<String, Object>> updateStudentProfile(@RequestBody StudentProfileRequest req) {
    if (req == null) return ApiResponse.badRequest("请求体不能为空");
    return ApiResponse.ok(
        "保存成功",
        localAcademicService.updateStudentProfile(req.getSno(), req.getPhone(), req.getEmail()));
  }

  @GetMapping("/choices")
  public ApiResponse<List<Map<String, Object>>> listChoices(@RequestParam String sno) {
    return ApiResponse.ok("ok", localAcademicService.listStudentChoices(sno));
  }

  @PostMapping("/choice/choose")
  public ApiResponse<Map<String, Object>> choose(@RequestBody ChooseRequest req) {
    if (req == null) return ApiResponse.badRequest("请求体不能为空");
    return ApiResponse.ok("选课成功", localAcademicService.chooseLocalCourse(req.getSno(), req.getCno()));
  }

  @PostMapping("/choice/drop")
  public ApiResponse<Map<String, Object>> drop(@RequestBody ChooseRequest req) {
    if (req == null) return ApiResponse.badRequest("请求体不能为空");
    return ApiResponse.ok("退课成功", localAcademicService.dropLocalCourse(req.getSno(), req.getCno()));
  }
}

