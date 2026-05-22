package edu.integration.b.xml;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;
import java.util.ArrayList;
import java.util.List;

@XmlRootElement(name = "Classes")
@XmlAccessorType(XmlAccessType.FIELD)
public class ClassesXml {
  @XmlElement(name = "class")
  private List<ClassXml> classes = new ArrayList<>();

  public ClassesXml() {}

  public ClassesXml(List<ClassXml> classes) {
    this.classes = classes;
  }

  public List<ClassXml> getClasses() {
    return classes;
  }
}

