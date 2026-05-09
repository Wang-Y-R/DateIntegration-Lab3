<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
    <xsl:template match="/classes">
        <Classes>
            <xsl:for-each select="class">
                <class>
                    <编号><xsl:value-of select="id"/></编号>
                    <名称><xsl:value-of select="name"/></名称>
                    <课时><xsl:value-of select="time"/></课时>
                    <学分><xsl:value-of select="score"/></学分>
                    <老师><xsl:value-of select="teacher"/></老师>
                    <地点><xsl:value-of select="location"/></地点>
                    <共享>Y</共享>
                </class>
            </xsl:for-each>
        </Classes>
    </xsl:template>
</xsl:stylesheet>
