package edu.integration.b.service;

import edu.integration.b.repo.ChoiceRepository;
import edu.integration.b.repo.CourseRepository;
import edu.integration.b.repo.StudentRepository;
import edu.integration.b.xml.ClassesXml;
import edu.integration.b.xml.CrossDepartmentChoiceXml;
import edu.integration.b.xml.ResponseXml;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class InternalIntegrationService {
  private final CourseRepository courseRepository;
  private final StudentRepository studentRepository;
  private final ChoiceRepository choiceRepository;

  public InternalIntegrationService(
      CourseRepository courseRepository, StudentRepository studentRepository, ChoiceRepository choiceRepository) {
    this.courseRepository = courseRepository;
    this.studentRepository = studentRepository;
    this.choiceRepository = choiceRepository;
  }

  public ResponseXml sharedCourses() {
    return ResponseXml.ok("获取共享课程列表成功", new ClassesXml(courseRepository.findSharedCoursesAsXml()));
  }

  @Transactional
  public ResponseXml choose(CrossDepartmentChoiceXml req) {
    if (req == null || req.getStudent() == null || req.getChoice() == null) {
      return ResponseXml.badRequest("XML格式校验失败：请求体缺失Student或Choice");
    }
    String sid = req.getChoice().getSid();
    String cid = req.getChoice().getCid();
    if (sid == null || sid.trim().isEmpty()) return ResponseXml.badRequest("XML格式校验失败：sid字段缺失");
    if (cid == null || cid.trim().isEmpty()) return ResponseXml.badRequest("XML格式校验失败：cid字段缺失");
    if (!Objects.equals(sid, req.getStudent().getId())) {
      return ResponseXml.badRequest("XML格式校验失败：sid与Student.id不一致");
    }

    if (!courseRepository.existsCourse(cid)) return ResponseXml.badRequest("选课失败：课程不存在");
    // 只允许别人选到B端“对外共享”的课程（符合课程共享场景）
    if (!courseRepository.isShared(cid)) return ResponseXml.badRequest("选课失败：该课程不开放共享");

    studentRepository.insertMirrorStudentIfAbsent(req.getStudent());

    boolean inserted = choiceRepository.insertChoiceIfAbsent(cid, sid);
    if (!inserted) return ResponseXml.badRequest("选课失败：已选过该课程");

    return ResponseXml.okEmpty("跨系选课成功");
  }

  @Transactional
  public ResponseXml drop(CrossDepartmentChoiceXml req) {
    if (req == null || req.getChoice() == null) {
      return ResponseXml.badRequest("XML格式校验失败：请求体缺失Choice");
    }
    String sid = req.getChoice().getSid();
    String cid = req.getChoice().getCid();
    if (sid == null || sid.trim().isEmpty()) return ResponseXml.badRequest("XML格式校验失败：sid字段缺失");
    if (cid == null || cid.trim().isEmpty()) return ResponseXml.badRequest("XML格式校验失败：cid字段缺失");
    if (!courseRepository.existsCourse(cid)) return ResponseXml.badRequest("退课失败：课程不存在");

    int deleted = choiceRepository.deleteChoice(cid, sid);
    if (deleted == 0) return ResponseXml.badRequest("退课失败：未找到该选课记录");
    return ResponseXml.okEmpty("跨系退课成功");
  }
}

