package edu.integration.b.xml;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;

@XmlAccessorType(XmlAccessType.FIELD)
public class ClassXml {
  @XmlElement(name = "编号")
  private String id;

  @XmlElement(name = "名称")
  private String name;

  @XmlElement(name = "课时")
  private String time;

  @XmlElement(name = "学分")
  private String score;

  @XmlElement(name = "老师")
  private String teacher;

  @XmlElement(name = "地点")
  private String location;

  @XmlElement(name = "共享")
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

