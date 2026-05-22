package edu.integration.b.xml;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;

@XmlAccessorType(XmlAccessType.FIELD)
public class ClassXml {
  @XmlElement(name = "id")
  private String id;

  @XmlElement(name = "name")
  private String name;

  @XmlElement(name = "time")
  private String time;

  @XmlElement(name = "score")
  private String score;

  @XmlElement(name = "teacher")
  private String teacher;

  @XmlElement(name = "location")
  private String location;

  @XmlElement(name = "share")
  private String share;

  public ClassXml() {}

  public ClassXml(String id, String name, String time, String score, String teacher, String location, String share) {
    this.id = id;
    this.name = name;
    this.time = time;
    this.score = score;
    this.teacher = teacher;
    this.location = location;
    this.share = share;
  }

  public String getId() {
    return id;
  }

  public String getName() {
    return name;
  }

  public String getTime() {
    return time;
  }

  public String getScore() {
    return score;
  }

  public String getTeacher() {
    return teacher;
  }

  public String getLocation() {
    return location;
  }

  public String getShare() {
    return share;
  }
}

