package edu.integration.b.repo;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class ChoiceRepository {
  private final JdbcTemplate jdbcTemplate;

  public ChoiceRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
  }

  public boolean insertChoiceIfAbsent(String cno, String sno) {
    try {
      return jdbcTemplate.update("INSERT INTO B_CHOICE (CNO, SNO, GRD) VALUES (?, ?, NULL)", cno, sno) == 1;
    } catch (DuplicateKeyException ex) {
      return false;
    }
  }

  public int deleteChoice(String cno, String sno) {
    return jdbcTemplate.update("DELETE FROM B_CHOICE WHERE CNO = ? AND SNO = ?", cno, sno);
  }

  public java.util.List<java.util.Map<String, Object>> findChoicesByStudent(String sno) {
    return jdbcTemplate.query(
        "SELECT c.CNO, c.CNM, c.CTM, c.CPT, c.TEC, c.PLA, c.SHARE_FLAG, ch.GRD "
            + "FROM B_CHOICE ch JOIN B_COURSE c ON ch.CNO = c.CNO "
            + "WHERE ch.SNO = ? ORDER BY c.CNO",
        (rs, rowNum) -> {
          java.util.Map<String, Object> m = new java.util.LinkedHashMap<>();
          m.put("cno", rs.getString("CNO"));
          m.put("cnm", rs.getString("CNM"));
          m.put("ctm", rs.getString("CTM"));
          m.put("cpt", rs.getString("CPT"));
          m.put("tec", rs.getString("TEC"));
          m.put("pla", rs.getString("PLA"));
          m.put("share", rs.getString("SHARE_FLAG"));
          m.put("grd", rs.getString("GRD"));
          return m;
        },
        sno);
  }
}

