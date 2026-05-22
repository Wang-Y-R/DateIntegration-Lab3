<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/">
    <choices>
      <xsl:for-each select="choices/choice">
        <choice>
          <sid><xsl:value-of select="学生编号"/></sid>
          <cid><xsl:value-of select="课程编号"/></cid>
          <score><xsl:value-of select="成绩"/></score>
        </choice>
      </xsl:for-each>
    </choices>
  </xsl:template>

</xsl:stylesheet>
