package edu.integration.b.xml;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement(name = "Response")
@XmlAccessorType(XmlAccessType.FIELD)
public class ResponseXml {
  @XmlElement(name = "Code")
  private int code;

  @XmlElement(name = "Message")
  private String message;

  @XmlElement(name = "Data")
  private DataXml data;

  public ResponseXml() {}

  public ResponseXml(int code, String message, DataXml data) {
    this.code = code;
    this.message = message;
    this.data = data;
  }

  public static ResponseXml ok(String message, Object payload) {
    return new ResponseXml(200, message, DataXml.of(payload));
  }

  public static ResponseXml okEmpty(String message) {
    return new ResponseXml(200, message, DataXml.empty());
  }

  public static ResponseXml badRequest(String message) {
    return new ResponseXml(400, message, DataXml.empty());
  }

  public int getCode() {
    return code;
  }

  public String getMessage() {
    return message;
  }

  public DataXml getData() {
    return data;
  }
}

