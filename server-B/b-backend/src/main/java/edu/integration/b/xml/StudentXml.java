package edu.integration.b.xml;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;

@XmlAccessorType(XmlAccessType.FIELD)
public class StudentXml {
  @XmlElement(name = "Sno", required = true)
  private String id;

  @XmlElement(name = "Snm", required = true)
  private String name;

  @XmlElement(name = "Sex", required = true)
  private String sex;

  @XmlElement(name = "Sde", required = true)
  private String major;

  @XmlElement(name = "Origin")
  private String origin;

  public StudentXml() {}

  public StudentXml(String id, String name, String sex, String major, String origin) {
    this.id = id;
    this.name = name;
    this.sex = sex;
    this.major = major;
    this.origin = origin;
  }

  public String getId() {
    return id;
  }

  public String getName() {
    return name;
  }

  public String getSex() {
    return sex;
  }

  public String getMajor() {
    return major;
  }

  public String getOrigin() {
    return origin;
  }
}

