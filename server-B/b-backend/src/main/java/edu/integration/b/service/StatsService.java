package edu.integration.b.service;

import edu.integration.b.repo.StatsRepository;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class StatsService {
  private final StatsRepository statsRepository;

  public StatsService(StatsRepository statsRepository) {
    this.statsRepository = statsRepository;
  }

  public Map<String, Object> overview() {
    Map<String, Object> m = new LinkedHashMap<>();
    m.put("studentCount", statsRepository.studentCount());
    m.put("courseCount", statsRepository.courseCount());
    m.put("choiceCount", statsRepository.choiceCount());
    m.put("courseChosenCounts", statsRepository.courseChosenCounts());
    return m;
  }
}

