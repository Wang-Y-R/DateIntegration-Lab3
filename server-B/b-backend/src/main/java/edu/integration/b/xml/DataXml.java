package edu.integration.b.xml;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlAnyElement;

@XmlAccessorType(XmlAccessType.FIELD)
public class DataXml {
  @XmlAnyElement(lax = true)
  private Object any;

  public DataXml() {}

  private DataXml(Object any) {
    this.any = any;
  }

  public static DataXml empty() {
    return new DataXml(null);
  }

  public static DataXml of(Object payload) {
    return new DataXml(payload);
  }

  public Object getAny() {
    return any;
  }
}

