package edu.integration.b.web.dto;

public class StudentProfileRequest {
  private String sno;
  private String phone;
  private String email;

  public StudentProfileRequest() {}

  public String getSno() {
    return sno;
  }

  public void setSno(String sno) {
    this.sno = sno;
  }

  public String getPhone() {
    return phone;
  }

  public void setPhone(String phone) {
    this.phone = phone;
  }

  public String getEmail() {
    return email;
  }

  public void setEmail(String email) {
    this.email = email;
  }
}
