<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
    <!-- A: 课程编号/课程名称/学分/授课老师/授课地点 | B: 编号/名称/课时/学分/老师/地点 | C: Cno/Cnm/Ctm/Cpt/Tec/Pla -->
    <xsl:template match="/Classes">
        <classes>
            <xsl:for-each select="class[共享='Y' or Share='Y']">
                <class>
                    <id>
                        <xsl:choose>
                            <xsl:when test="课程编号"><xsl:value-of select="课程编号"/></xsl:when>
                            <xsl:when test="编号"><xsl:value-of select="编号"/></xsl:when>
                            <xsl:when test="Cno"><xsl:value-of select="Cno"/></xsl:when>
                        </xsl:choose>
                    </id>
                    <name>
                        <xsl:choose>
                            <xsl:when test="课程名称"><xsl:value-of select="课程名称"/></xsl:when>
                            <xsl:when test="名称"><xsl:value-of select="名称"/></xsl:when>
                            <xsl:when test="Cnm"><xsl:value-of select="Cnm"/></xsl:when>
                        </xsl:choose>
                    </name>
                    <time>
                        <xsl:choose>
                            <xsl:when test="课时"><xsl:value-of select="课时"/></xsl:when>
                            <xsl:when test="Ctm"><xsl:value-of select="Ctm"/></xsl:when>
                            <xsl:otherwise>0</xsl:otherwise>
                        </xsl:choose>
                    </time>
                    <score>
                        <xsl:choose>
                            <xsl:when test="学分"><xsl:value-of select="学分"/></xsl:when>
                            <xsl:when test="Cpt"><xsl:value-of select="Cpt"/></xsl:when>
                        </xsl:choose>
                    </score>
                    <teacher>
                        <xsl:choose>
                            <xsl:when test="授课老师"><xsl:value-of select="授课老师"/></xsl:when>
                            <xsl:when test="老师"><xsl:value-of select="老师"/></xsl:when>
                            <xsl:when test="Tec"><xsl:value-of select="Tec"/></xsl:when>
                        </xsl:choose>
                    </teacher>
                    <location>
                        <xsl:choose>
                            <xsl:when test="授课地点"><xsl:value-of select="授课地点"/></xsl:when>
                            <xsl:when test="地点"><xsl:value-of select="地点"/></xsl:when>
                            <xsl:when test="Pla"><xsl:value-of select="Pla"/></xsl:when>
                        </xsl:choose>
                    </location>
                </class>
            </xsl:for-each>
        </classes>
    </xsl:template>
</xsl:stylesheet>
