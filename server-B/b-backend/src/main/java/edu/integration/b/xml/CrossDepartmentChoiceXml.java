package edu.integration.b.xml;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement(name = "CrossDepartmentChoice")
@XmlAccessorType(XmlAccessType.FIELD)
public class CrossDepartmentChoiceXml {
  @XmlElement(name = "Student", required = true)
  private StudentXml student;

  @XmlElement(name = "Choice", required = true)
  private ChoiceXml choice;

  public CrossDepartmentChoiceXml() {}

  public StudentXml getStudent() {
    return student;
  }

  public ChoiceXml getChoice() {
    return choice;
  }
}

