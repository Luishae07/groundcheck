<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="no"/>

<xsl:template match="/">
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>sitemap.xml</title>
<style>
:root{--bg:#ffffff;--ink:#1d2733;--tag:#1f5fa8;--attr:#a0521c;--val:#1a7a45;--note:#7a8794;--pun:#7a8794}
@media (prefers-color-scheme: dark){:root{--bg:#10151c;--ink:#d8e1ea;--tag:#7fb4ee;--attr:#e0a36a;--val:#7fd39a;--note:#7f8c99;--pun:#7f8c99}}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.55 ui-monospace,Menlo,Consolas,monospace}
main{padding:14px 12px 40px}
.n{margin-left:14px;white-space:pre-wrap;overflow-wrap:anywhere}
.root{margin-left:0}
.t{color:var(--tag)}.a{color:var(--attr)}.v{color:var(--val)}.p{color:var(--pun)}.c{color:var(--note);white-space:pre-wrap}
</style>
</head>
<body>
<main>
<div class="n root"><span class="p">&lt;?xml version="1.0" encoding="UTF-8"?&gt;</span></div>
<xsl:apply-templates select="node()"/>
</main>
</body>
</html>
</xsl:template>

<xsl:template match="comment()">
  <div class="n c"><xsl:if test="not(parent::*)"><xsl:attribute name="class">n root c</xsl:attribute></xsl:if>&lt;!--<xsl:value-of select="."/>--&gt;</div>
</xsl:template>

<xsl:template name="open">
  <span class="p">&lt;</span><span class="t"><xsl:value-of select="name()"/></span>
  <xsl:if test="not(parent::*)">
    <xsl:for-each select="namespace::*[name()!='xml']">
      <xsl:text> </xsl:text><span class="a">xmlns<xsl:if test="name()!=''">:<xsl:value-of select="name()"/></xsl:if></span><span class="p">=</span><span class="v">"<xsl:value-of select="."/>"</span>
    </xsl:for-each>
  </xsl:if>
  <xsl:for-each select="@*">
    <xsl:text> </xsl:text><span class="a"><xsl:value-of select="name()"/></span><span class="p">=</span><span class="v">"<xsl:value-of select="."/>"</span>
  </xsl:for-each>
</xsl:template>

<xsl:template match="*">
  <div class="n"><xsl:if test="not(parent::*)"><xsl:attribute name="class">n root</xsl:attribute></xsl:if>
    <xsl:choose>
      <xsl:when test="not(*) and not(comment())">
        <xsl:call-template name="open"/><span class="p">&gt;</span><xsl:value-of select="."/><span class="p">&lt;/</span><span class="t"><xsl:value-of select="name()"/></span><span class="p">&gt;</span>
      </xsl:when>
      <xsl:otherwise>
        <xsl:call-template name="open"/><span class="p">&gt;</span>
        <xsl:apply-templates select="*|comment()"/>
        <div class="n root"><span class="p">&lt;/</span><span class="t"><xsl:value-of select="name()"/></span><span class="p">&gt;</span></div>
      </xsl:otherwise>
    </xsl:choose>
  </div>
</xsl:template>

</xsl:stylesheet>
