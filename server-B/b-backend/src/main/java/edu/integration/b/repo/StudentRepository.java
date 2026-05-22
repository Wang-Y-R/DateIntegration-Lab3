package edu.integration.b.repo;

import edu.integration.b.xml.StudentXml;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class StudentRepository {
  private final JdbcTemplate jdbcTemplate;

  public StudentRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
  }

  public boolean exists(String sno) {
    Integer cnt = jdbcTemplate.queryForObject("SELECT COUNT(1) FROM B_STUDENT WHERE SNO = ?", Integer.class, sno);
    return cnt != null && cnt > 0;
  }

  public void insertMirrorStudentIfAbsent(StudentXml s) {
    if (exists(s.getId())) return;
    String origin = (s.getOrigin() == null || s.getOrigin().trim().isEmpty()) ? "X" : s.getOrigin();
    // Mirror student: set a default password (not used for external students)
    jdbcTemplate.update(
        "INSERT INTO B_STUDENT (SNO, SNM, SEX, MAJOR, PWD, ORIGIN) VALUES (?, ?, ?, ?, ?, ?)",
        s.getId(),
        s.getName(),
        s.getSex(),
        s.getMajor(),
        "000000",
        origin);
  }

  public java.util.Optional<java.util.Map<String, Object>> findStudent(String sno) {
    return jdbcTemplate
        .query(
            "SELECT SNO, SNM, SEX, MAJOR, PHONE, EMAIL, ORIGIN FROM B_STUDENT WHERE SNO = ?",
            (rs, rowNum) -> {
              java.util.Map<String, Object> m = new java.util.LinkedHashMap<>();
              m.put("sno", rs.getString("SNO"));
              m.put("snm", rs.getString("SNM"));
              m.put("sex", rs.getString("SEX"));
              m.put("major", rs.getString("MAJOR"));
              m.put("phone", rs.getString("PHONE"));
              m.put("email", rs.getString("EMAIL"));
              m.put("origin", rs.getString("ORIGIN"));
              return m;
            },
            sno)
        .stream()
        .findFirst();
  }

  public int updateContact(String sno, String phone, String email) {
    return jdbcTemplate.update(
        "UPDATE B_STUDENT SET PHONE = ?, EMAIL = ? WHERE SNO = ?",
        phone,
        email,
        sno);
  }

  public boolean checkStudentPassword(String sno, String pwd) {
    Integer cnt =
        jdbcTemplate.queryForObject(
            "SELECT COUNT(1) FROM B_STUDENT WHERE SNO = ? AND PWD = ?", Integer.class, sno, pwd);
    return cnt != null && cnt > 0;
  }

  public java.util.List<java.util.Map<String, Object>> listStudents(int limit) {
    int safeLimit = Math.max(1, Math.min(200, limit));
    return jdbcTemplate.query(
        "SELECT SNO, SNM, SEX, MAJOR, PHONE, EMAIL, ORIGIN FROM B_STUDENT ORDER BY SNO FETCH FIRST "
            + safeLimit
            + " ROWS ONLY",
        (rs, rowNum) -> {
          java.util.Map<String, Object> m = new java.util.LinkedHashMap<>();
          m.put("sno", rs.getString("SNO"));
          m.put("snm", rs.getString("SNM"));
          m.put("sex", rs.getString("SEX"));
          m.put("major", rs.getString("MAJOR"));
          m.put("phone", rs.getString("PHONE"));
          m.put("email", rs.getString("EMAIL"));
          m.put("origin", rs.getString("ORIGIN"));
          return m;
        });
  }
}

