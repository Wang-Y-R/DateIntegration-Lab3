package edu.integration.b.service;

import edu.integration.b.repo.ChoiceRepository;
import edu.integration.b.repo.CourseRepository;
import edu.integration.b.repo.StudentRepository;
import edu.integration.b.xml.ClassesXml;
import edu.integration.b.xml.ResponseXml;
import edu.integration.b.xml.StudentXml;
import java.io.StringReader;
import java.io.StringWriter;
import java.util.Objects;
import javax.xml.XMLConstants;
import javax.xml.bind.JAXBContext;
import javax.xml.bind.JAXBException;
import javax.xml.bind.Marshaller;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;

@Service
public class InternalIntegrationService {
  private static final String CROSS_DEPARTMENT_CHOICE_XSD = "xsd/crossDepartmentChoiceB.xsd";

  private final CourseRepository courseRepository;
  private final StudentRepository studentRepository;
  private final ChoiceRepository choiceRepository;
  private final Schema crossDepartmentChoiceSchema;

  public InternalIntegrationService(
      CourseRepository courseRepository, StudentRepository studentRepository, ChoiceRepository choiceRepository) {
    this.courseRepository = courseRepository;
    this.studentRepository = studentRepository;
    this.choiceRepository = choiceRepository;
    this.crossDepartmentChoiceSchema = loadSchema(CROSS_DEPARTMENT_CHOICE_XSD);
  }

  public ResponseXml sharedCourses() {
    return ResponseXml.ok("获取共享课程列表成功", new ClassesXml(courseRepository.findSharedCoursesAsXml()));
  }

  public ClassesXml sharedCoursesRaw() {
    return new ClassesXml(courseRepository.findSharedCoursesAsXml());
  }

  @Transactional
  public ResponseXml choose(String requestXml) {
    ResponseXml schemaError = validateCrossDepartmentChoiceXml(requestXml);
    if (schemaError != null) {
      return schemaError;
    }

    CrossDepartmentPayload payload = parseCrossDepartmentChoice(requestXml);
    if (payload == null) {
      return ResponseXml.badRequest("XML格式校验失败：请求体缺失Student或Choice");
    }
    if (payload.studentId == null || payload.studentId.trim().isEmpty()) {
      return ResponseXml.badRequest("XML格式校验失败：学号字段缺失");
    }
    if (payload.courseId == null || payload.courseId.trim().isEmpty()) {
      return ResponseXml.badRequest("XML格式校验失败：课程编号字段缺失");
    }
    if (payload.studentName == null || payload.studentName.trim().isEmpty()) {
      return ResponseXml.badRequest("XML格式校验失败：姓名字段缺失");
    }
    if (payload.studentSex == null || payload.studentSex.trim().isEmpty()) {
      return ResponseXml.badRequest("XML格式校验失败：性别字段缺失");
    }
    if (payload.studentMajor == null || payload.studentMajor.trim().isEmpty()) {
      return ResponseXml.badRequest("XML格式校验失败：院系字段缺失");
    }
    if (!Objects.equals(payload.studentId, payload.choiceStudentId)) {
      return ResponseXml.badRequest("XML格式校验失败：学号与选课记录不一致");
    }

    if (!courseRepository.existsCourse(payload.courseId)) return ResponseXml.badRequest("选课失败：课程不存在");
    // 只允许别人选到B端“对外共享”的课程（符合课程共享场景）
    if (!courseRepository.isShared(payload.courseId)) return ResponseXml.badRequest("选课失败：该课程不开放共享");

    studentRepository.insertMirrorStudentIfAbsent(
        new StudentXml(payload.studentId, payload.studentName, payload.studentSex, payload.studentMajor, payload.studentOrigin));

    boolean inserted = choiceRepository.insertChoiceIfAbsent(payload.courseId, payload.studentId);
    if (!inserted) return ResponseXml.badRequest("选课失败：已选过该课程");

    return ResponseXml.okEmpty("跨系选课成功");
  }

  @Transactional
  public ResponseXml drop(String requestXml) {
    ResponseXml schemaError = validateCrossDepartmentChoiceXml(requestXml);
    if (schemaError != null) {
      return schemaError;
    }

    CrossDepartmentPayload payload = parseCrossDepartmentChoice(requestXml);
    if (payload == null) {
      return ResponseXml.badRequest("XML格式校验失败：请求体缺失Choice");
    }
    if (payload.choiceStudentId == null || payload.choiceStudentId.trim().isEmpty()) {
      return ResponseXml.badRequest("XML格式校验失败：学号字段缺失");
    }
    if (payload.courseId == null || payload.courseId.trim().isEmpty()) {
      return ResponseXml.badRequest("XML格式校验失败：课程编号字段缺失");
    }
    if (!courseRepository.existsCourse(payload.courseId)) return ResponseXml.badRequest("退课失败：课程不存在");

    int deleted = choiceRepository.deleteChoice(payload.courseId, payload.choiceStudentId);
    if (deleted == 0) return ResponseXml.badRequest("退课失败：未找到该选课记录");
    return ResponseXml.okEmpty("跨系退课成功");
  }

  private CrossDepartmentPayload parseCrossDepartmentChoice(String requestXml) {
    if (requestXml == null || requestXml.trim().isEmpty()) {
      return null;
    }

    Document document = parseDocument(requestXml);
    if (document == null) {
      return null;
    }

    Element root = document.getDocumentElement();
    Element studentElement = findChildElement(root, "Student");
    Element choiceElement = findChildElement(root, "Choice");
    if (studentElement == null || choiceElement == null) {
      return null;
    }

    CrossDepartmentPayload payload = new CrossDepartmentPayload();
    payload.studentId = directText(studentElement, "学号");
    payload.studentName = directText(studentElement, "姓名");
    payload.studentSex = directText(studentElement, "性别");
    payload.studentMajor = directText(studentElement, "专业");
    payload.studentOrigin = null;
    payload.courseId = directText(choiceElement, "课程编号");
    payload.choiceStudentId = directText(choiceElement, "学号");
    payload.score = directText(choiceElement, "得分");

    return payload;
  }

  private ResponseXml validateCrossDepartmentChoiceXml(String requestXml) {
    if (requestXml == null || requestXml.trim().isEmpty()) {
      return ResponseXml.badRequest("XML格式校验失败：请求体不能为空");
    }

    try {
      crossDepartmentChoiceSchema.newValidator().validate(new StreamSource(new StringReader(requestXml)));
      return null;
    } catch (SAXException ex) {
      return ResponseXml.badRequest("XML格式校验失败：不符合B端XSD约束");
    } catch (Exception ex) {
      return ResponseXml.badRequest("XML格式校验失败：无法完成XSD校验");
    }
  }

  private Schema loadSchema(String classpathLocation) {
    try {
      SchemaFactory schemaFactory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
      try (java.io.InputStream inputStream =
          Thread.currentThread().getContextClassLoader().getResourceAsStream(classpathLocation)) {
        if (inputStream == null) {
          throw new IllegalStateException("找不到XSD文件: " + classpathLocation);
        }
        return schemaFactory.newSchema(new StreamSource(inputStream));
      }
    } catch (Exception ex) {
      throw new IllegalStateException("加载XSD失败: " + classpathLocation, ex);
    }
  }

  private Document parseDocument(String xml) {
    try {
      DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
      factory.setNamespaceAware(false);
      factory.setExpandEntityReferences(false);
      factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
      factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
      factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
      return factory.newDocumentBuilder().parse(new InputSource(new StringReader(xml)));
    } catch (Exception ex) {
      return null;
    }
  }

  private Element findChildElement(Element parent, String tagName) {
    if (parent == null) {
      return null;
    }
    NodeList nodes = parent.getElementsByTagName(tagName);
    for (int index = 0; index < nodes.getLength(); index++) {
      Node node = nodes.item(index);
      if (node instanceof Element && node.getParentNode() == parent) {
        return (Element) node;
      }
    }
    return null;
  }

  private String directText(Element parent, String... tagNames) {
    if (parent == null || tagNames == null) {
      return null;
    }
    for (String tagName : tagNames) {
      if (tagName == null || tagName.trim().isEmpty()) {
        continue;
      }
      NodeList nodes = parent.getElementsByTagName(tagName);
      for (int index = 0; index < nodes.getLength(); index++) {
        Node node = nodes.item(index);
        if (node instanceof Element && node.getParentNode() == parent) {
          String textContent = node.getTextContent();
          if (textContent != null && !textContent.trim().isEmpty()) {
            return textContent.trim();
          }
        }
      }
    }
    return null;
  }
  public String sharedCoursesXml() {
    ClassesXml payload = new ClassesXml(courseRepository.findSharedCoursesAsXml());
    try {
      JAXBContext ctx = JAXBContext.newInstance(ClassesXml.class);
      Marshaller marshaller = ctx.createMarshaller();
      marshaller.setProperty(Marshaller.JAXB_ENCODING, "UTF-8");
      marshaller.setProperty(Marshaller.JAXB_FORMATTED_OUTPUT, Boolean.FALSE);
      marshaller.setProperty(Marshaller.JAXB_FRAGMENT, Boolean.TRUE); // no <?xml ...?>
      StringWriter sw = new StringWriter();
      marshaller.marshal(payload, sw);
      return sw.toString();
    } catch (JAXBException ex) {
      throw new IllegalStateException("marshal ClassesXml failed", ex);
    }
  }

  private static class CrossDepartmentPayload {
    private String studentId;
    private String studentName;
    private String studentSex;
    private String studentMajor;
    private String studentOrigin;
    private String courseId;
    private String choiceStudentId;
    private String score;
  }
}

