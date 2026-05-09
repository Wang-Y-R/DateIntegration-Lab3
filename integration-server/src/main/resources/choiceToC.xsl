<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
    <xsl:template match="/choices">
        <choices>
            <xsl:for-each select="choice">
                <choice>
                    <Cno><xsl:value-of select="cid"/></Cno>
                    <Sno><xsl:value-of select="sid"/></Sno>
                    <Grd><xsl:value-of select="score"/></Grd>
                </choice>
            </xsl:for-each>
        </choices>
    </xsl:template>
</xsl:stylesheet>
