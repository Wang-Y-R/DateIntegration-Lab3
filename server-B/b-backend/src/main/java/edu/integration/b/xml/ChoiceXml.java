package edu.integration.b.xml;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;

@XmlAccessorType(XmlAccessType.FIELD)
public class ChoiceXml {
  @XmlElement(name = "Cid", required = true)
  private String cid;

  @XmlElement(name = "Sno", required = true)
  private String sid;

  @XmlElement(name = "Grd")
  private String score;

  public ChoiceXml() {}

  public ChoiceXml(String cid, String sid, String score) {
    this.cid = cid;
    this.sid = sid;
    this.score = score;
  }

  public String getCid() {
    return cid;
  }

  public String getSid() {
    return sid;
  }

  public String getScore() {
    return score;
  }
}

