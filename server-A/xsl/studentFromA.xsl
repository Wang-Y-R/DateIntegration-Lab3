<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/">
    <students>
      <xsl:for-each select="Students/student">
        <student>
          <id><xsl:value-of select="学号"/></id>
          <name><xsl:value-of select="姓名"/></name>
          <sex><xsl:value-of select="性别"/></sex>
          <major><xsl:value-of select="院系"/></major>
        </student>
      </xsl:for-each>
    </students>
  </xsl:template>

</xsl:stylesheet>
