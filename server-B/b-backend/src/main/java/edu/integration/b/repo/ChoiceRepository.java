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
      int updated = jdbcTemplate.update("INSERT INTO B_CHOICE (CNO, SNO, GRD) VALUES (?, ?, NULL)", cno, sno);
      return updated == 1;
    } catch (DuplicateKeyException ex) {
      return false;
    }
  }

  public int deleteChoice(String cno, String sno) {
    int deleted = jdbcTemplate.update("DELETE FROM B_CHOICE WHERE CNO = ? AND SNO = ?", cno, sno);
    return deleted;
  }

  public java.util.List<java.util.Map<String, Object>> findChoicesByStudent(String sno) {
    return jdbcTemplate.query(
        "SELECT c.CNO, c.CNM, c.CTM, c.CPT, c.TEC, c.PLA, c.SHARE_FLAG, ch.GRD, 'LOCAL' AS SOURCE, NULL AS DEST_SYSTEM "
            + "FROM B_CHOICE ch JOIN B_COURSE c ON ch.CNO = c.CNO "
            + "WHERE ch.SNO = ? "
            + "UNION ALL "
            + "SELECT x.CNO, x.CNM, x.CTM, x.CPT, x.TEC, x.PLA, x.SHARE_FLAG, x.GRD, 'CROSS' AS SOURCE, x.DEST_SYSTEM "
            + "FROM B_CROSS_CHOICE x WHERE x.SNO = ? "
            + "ORDER BY 1",
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
          m.put("source", rs.getString("SOURCE"));
          m.put("destSystem", rs.getString("DEST_SYSTEM"));
          return m;
        },
        sno,
        sno);
  }

  public boolean insertCrossChoiceIfAbsent(
      String cno,
      String sno,
      String cnm,
      String ctm,
      String cpt,
      String tec,
      String pla,
      String shareFlag,
      String destSystem,
      String grd) {
    try {
      int updated =
          jdbcTemplate.update(
              "INSERT INTO B_CROSS_CHOICE (CNO, SNO, CNM, CTM, CPT, TEC, PLA, SHARE_FLAG, DEST_SYSTEM, GRD) "
                  + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              cno,
              sno,
              cnm,
              ctm,
              cpt,
              tec,
              pla,
              shareFlag,
              destSystem,
              grd);
      return updated == 1;
    } catch (DuplicateKeyException ex) {
      return false;
    }
  }

  public int deleteCrossChoice(String cno, String sno, String destSystem) {
    return jdbcTemplate.update(
        "DELETE FROM B_CROSS_CHOICE WHERE CNO = ? AND SNO = ? AND DEST_SYSTEM = ?", cno, sno, destSystem);
  }

  public java.util.List<java.util.Map<String, Object>> findCrossChoicesByStudent(String sno) {
    return jdbcTemplate.query(
        "SELECT CNO, CNM, CTM, CPT, TEC, PLA, SHARE_FLAG, GRD, DEST_SYSTEM FROM B_CROSS_CHOICE WHERE SNO = ? ORDER BY CNO",
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
          m.put("source", "CROSS");
          m.put("destSystem", rs.getString("DEST_SYSTEM"));
          return m;
        },
        sno);
  }
}

