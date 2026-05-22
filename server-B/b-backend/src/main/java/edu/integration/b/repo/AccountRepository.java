package edu.integration.b.repo;

import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class AccountRepository {
  private final JdbcTemplate jdbcTemplate;

  public AccountRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
  }

  public Optional<Integer> findAdminLevelByAccPass(String acc, String pass) {
    return jdbcTemplate
        .query(
            "SELECT LVL FROM B_ACCOUNT WHERE ACC = ? AND PASS = ?",
            (rs, rowNum) -> rs.getInt("LVL"),
            acc,
            pass)
        .stream()
        .findFirst();
  }
}

