package edu.integration.b.repo;

import edu.integration.b.xml.ClassXml;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

@Repository
public class CourseRepository {
  private final JdbcTemplate jdbcTemplate;

  public CourseRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
  }

  public boolean existsCourse(String cno) {
    Integer cnt = jdbcTemplate.queryForObject("SELECT COUNT(1) FROM B_COURSE WHERE CNO = ?", Integer.class, cno);
    return cnt != null && cnt > 0;
  }

  public boolean isShared(String cno) {
    String share = jdbcTemplate.queryForObject("SELECT SHARE_FLAG FROM B_COURSE WHERE CNO = ?", String.class, cno);
    return "1".equals(share);
  }

  public List<ClassXml> findSharedCoursesAsXml() {
    return jdbcTemplate.query(
        "SELECT CNO, CNM, CTM, CPT, TEC, PLA, SHARE_FLAG FROM B_COURSE WHERE SHARE_FLAG = '1' ORDER BY CNO",
        new RowMapper<ClassXml>() {
          @Override
          public ClassXml mapRow(ResultSet rs, int rowNum) throws SQLException {
            String shareFlag = rs.getString("SHARE_FLAG");
            String share = "1".equals(shareFlag) ? "Y" : "N";
            return new ClassXml(
              rs.getString("CNO"),
              rs.getString("CNM"),
              rs.getString("CTM"),
              rs.getString("CPT"),
              rs.getString("TEC"),
              rs.getString("PLA"),
              share);
          }
        });
  }

  public List<java.util.Map<String, Object>> findAllCourses() {
    return jdbcTemplate.query(
        "SELECT CNO, CNM, CTM, CPT, TEC, PLA, SHARE_FLAG FROM B_COURSE ORDER BY CNO",
        (rs, rowNum) -> {
          java.util.Map<String, Object> m = new java.util.LinkedHashMap<>();
          m.put("cno", rs.getString("CNO"));
          m.put("cnm", rs.getString("CNM"));
          m.put("ctm", rs.getString("CTM"));
          m.put("cpt", rs.getString("CPT"));
          m.put("tec", rs.getString("TEC"));
          m.put("pla", rs.getString("PLA"));
          m.put("share", rs.getString("SHARE_FLAG"));
          return m;
        });
  }
}

