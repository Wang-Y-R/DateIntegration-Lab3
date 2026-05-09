<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
    <xsl:template match="/choices">
        <choices>
            <xsl:for-each select="choice">
                <choice>
                    <课程编号><xsl:value-of select="cid"/></课程编号>
                    <学号><xsl:value-of select="sid"/></学号>
                    <得分><xsl:value-of select="score"/></得分>
                </choice>
            </xsl:for-each>
        </choices>
    </xsl:template>
</xsl:stylesheet>
