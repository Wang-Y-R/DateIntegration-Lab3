package edu.integration.b.repo;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class StatsRepository {
  private final JdbcTemplate jdbcTemplate;

  public StatsRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
  }

  public int studentCount() {
    Integer v = jdbcTemplate.queryForObject("SELECT COUNT(1) FROM B_STUDENT", Integer.class);
    return v == null ? 0 : v;
  }

  public int courseCount() {
    Integer v = jdbcTemplate.queryForObject("SELECT COUNT(1) FROM B_COURSE", Integer.class);
    return v == null ? 0 : v;
  }

  public int choiceCount() {
    Integer v = jdbcTemplate.queryForObject("SELECT COUNT(1) FROM B_CHOICE", Integer.class);
    return v == null ? 0 : v;
  }

  public List<Map<String, Object>> courseChosenCounts() {
    return jdbcTemplate.query(
        "SELECT c.CNO AS cno, c.CNM AS cnm, COUNT(ch.SNO) AS chosenCount " +
            "FROM B_COURSE c LEFT JOIN B_CHOICE ch ON c.CNO = ch.CNO " +
            "GROUP BY c.CNO, c.CNM " +
            "ORDER BY c.CNO",
        (rs, rowNum) -> {
          Map<String, Object> m = new LinkedHashMap<>();
          m.put("cno", rs.getString("cno"));
          m.put("cnm", rs.getString("cnm"));
          m.put("chosenCount", rs.getInt("chosenCount"));
          return m;
        });
  }
}

