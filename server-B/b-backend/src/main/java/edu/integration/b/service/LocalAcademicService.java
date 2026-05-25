package edu.integration.b.service;

import edu.integration.b.repo.ChoiceRepository;
import edu.integration.b.repo.CourseRepository;
import edu.integration.b.repo.StudentRepository;
import edu.integration.b.web.dto.CrossChoiceSyncRequest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LocalAcademicService {
  private final StudentRepository studentRepository;
  private final CourseRepository courseRepository;
  private final ChoiceRepository choiceRepository;

  public LocalAcademicService(
      StudentRepository studentRepository, CourseRepository courseRepository, ChoiceRepository choiceRepository) {
    this.studentRepository = studentRepository;
    this.courseRepository = courseRepository;
    this.choiceRepository = choiceRepository;
  }

  public List<Map<String, Object>> listCourses() {
    return courseRepository.findAllCourses();
  }

  public List<Map<String, Object>> listStudents(int limit) {
    return studentRepository.listStudents(limit);
  }

  public Map<String, Object> getStudentProfile(String sno) {
    if (sno == null || sno.trim().isEmpty()) throw new IllegalArgumentException("sno不能为空");
    return studentRepository
        .findStudent(sno)
        .orElseThrow(() -> new IllegalArgumentException("学生不存在"));
  }

  public Map<String, Object> updateStudentProfile(String sno, String phone, String email) {
    if (sno == null || sno.trim().isEmpty()) throw new IllegalArgumentException("sno不能为空");
    if (!studentRepository.exists(sno)) throw new IllegalArgumentException("学生不存在");
    int updated = studentRepository.updateContact(sno, phone, email);
    if (updated == 0) throw new IllegalArgumentException("保存失败");
    return getStudentProfile(sno);
  }

  public List<Map<String, Object>> listStudentChoices(String sno) {
    if (sno == null || sno.trim().isEmpty()) throw new IllegalArgumentException("sno不能为空");
    if (!studentRepository.exists(sno)) throw new IllegalArgumentException("学生不存在");
    return choiceRepository.findChoicesByStudent(sno);
  }

  @Transactional
  public Map<String, Object> chooseLocalCourse(String sno, String cno) {
    if (sno == null || sno.trim().isEmpty()) throw new IllegalArgumentException("sno不能为空");
    if (cno == null || cno.trim().isEmpty()) throw new IllegalArgumentException("cno不能为空");
    if (!studentRepository.exists(sno)) throw new IllegalArgumentException("学生不存在");
    if (!courseRepository.existsCourse(cno)) throw new IllegalArgumentException("课程不存在");
    boolean ok = choiceRepository.insertChoiceIfAbsent(cno, sno);
    if (!ok) throw new IllegalArgumentException("已选过该课程");
    Map<String, Object> m = new LinkedHashMap<>();
    m.put("sno", sno);
    m.put("cno", cno);
    return m;
  }

  @Transactional
  public Map<String, Object> dropLocalCourse(String sno, String cno) {
    if (sno == null || sno.trim().isEmpty()) throw new IllegalArgumentException("sno不能为空");
    if (cno == null || cno.trim().isEmpty()) throw new IllegalArgumentException("cno不能为空");
    int n = choiceRepository.deleteChoice(cno, sno);
    if (n == 0) throw new IllegalArgumentException("未找到该选课记录");
    Map<String, Object> m = new LinkedHashMap<>();
    m.put("sno", sno);
    m.put("cno", cno);
    return m;
  }

  @Transactional
  public Map<String, Object> syncCrossChoice(CrossChoiceSyncRequest req) {
    if (req == null) throw new IllegalArgumentException("请求体不能为空");
    if (req.getSno() == null || req.getSno().trim().isEmpty()) throw new IllegalArgumentException("sno不能为空");
    if (req.getCno() == null || req.getCno().trim().isEmpty()) throw new IllegalArgumentException("cno不能为空");
    if (req.getDestSystem() == null || req.getDestSystem().trim().isEmpty()) throw new IllegalArgumentException("destSystem不能为空");

    String action = req.getAction() == null ? "choose" : req.getAction().trim().toLowerCase();
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("sno", req.getSno());
    result.put("cno", req.getCno());
    result.put("destSystem", req.getDestSystem());

    if ("drop".equals(action)) {
      int deleted = choiceRepository.deleteCrossChoice(req.getCno(), req.getSno(), req.getDestSystem());
      if (deleted == 0) throw new IllegalArgumentException("未找到该跨院系选课记录");
      result.put("deleted", deleted);
      return result;
    }

    boolean ok =
        choiceRepository.insertCrossChoiceIfAbsent(
            req.getCno(),
            req.getSno(),
            safeValue(req.getCnm()),
            safeValue(req.getCtm()),
            safeValue(req.getCpt()),
            safeValue(req.getTec()),
            safeValue(req.getPla()),
            normalizeShare(req.getShare()),
            req.getDestSystem(),
            safeValue(req.getGrd()));
    if (!ok) throw new IllegalArgumentException("已存在该跨院系选课记录");
    result.put("created", true);
    return result;
  }

  private String safeValue(String value) {
    return value == null ? "" : value.trim();
  }

  private String normalizeShare(String value) {
    String trimmed = safeValue(value);
    return trimmed.isEmpty() ? "1" : trimmed;
  }
}

