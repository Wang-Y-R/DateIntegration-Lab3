package edu.integration.b.service;

import edu.integration.b.repo.AccountRepository;
import edu.integration.b.repo.StudentRepository;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class AuthService {
  private final StudentRepository studentRepository;
  private final AccountRepository accountRepository;

  public AuthService(StudentRepository studentRepository, AccountRepository accountRepository) {
    this.studentRepository = studentRepository;
    this.accountRepository = accountRepository;
  }

  public Optional<Map<String, Object>> loginStudent(String sno, String pwd) {
    if (!studentRepository.checkStudentPassword(sno, pwd)) return Optional.empty();
    Optional<Map<String, Object>> stu = studentRepository.findStudent(sno);
    if (!stu.isPresent()) return Optional.empty();
    Map<String, Object> data = new LinkedHashMap<>();
    data.put("role", "STUDENT");
    data.put("userId", sno);
    data.put("profile", stu.get());
    return Optional.of(data);
  }

  public Optional<Map<String, Object>> loginAdmin(String acc, String pass) {
    Optional<Integer> lvl = accountRepository.findAdminLevelByAccPass(acc, pass);
    if (!lvl.isPresent()) return Optional.empty();
    Map<String, Object> data = new LinkedHashMap<>();
    data.put("role", "ADMIN");
    data.put("userId", acc);
    data.put("level", lvl.get());
    return Optional.of(data);
  }
}

