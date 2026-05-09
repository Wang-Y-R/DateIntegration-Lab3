<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
    <!-- A: 课程编号/学生编号/成绩 | B: 课程编号/学号/得分 | C: Cno/Sno/Grd -->
    <xsl:template match="/choices">
        <choices>
            <xsl:for-each select="choice">
                <choice>
                    <sid>
                        <xsl:choose>
                            <xsl:when test="学生编号"><xsl:value-of select="学生编号"/></xsl:when>
                            <xsl:when test="学号"><xsl:value-of select="学号"/></xsl:when>
                            <xsl:when test="Sno"><xsl:value-of select="Sno"/></xsl:when>
                        </xsl:choose>
                    </sid>
                    <cid>
                        <xsl:value-of select="课程编号"/><xsl:value-of select="Cno"/>
                    </cid>
                    <score>
                        <xsl:choose>
                            <xsl:when test="成绩"><xsl:value-of select="成绩"/></xsl:when>
                            <xsl:when test="得分"><xsl:value-of select="得分"/></xsl:when>
                            <xsl:when test="Grd"><xsl:value-of select="Grd"/></xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>
                    </score>
                </choice>
            </xsl:for-each>
        </choices>
    </xsl:template>
</xsl:stylesheet>
