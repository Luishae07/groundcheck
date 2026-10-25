<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" encoding="UTF-8" indent="no" doctype-system="about:legacy-compat"/>

<xsl:template match="/">
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="robots" content="noindex"/>
<title>sitemap.xml</title>
<style>
:root{--bg:#fbfcfe;--ink:#24303d;--tag:#1b57a6;--attr:#a8531b;--val:#17703f;--note:#7b8794;--pun:#8995a2;--link:#0a6e57;--sel:#cfe3ff}
@media (prefers-color-scheme: dark){:root{--bg:#0f141b;--ink:#d6dfe9;--tag:#7db3ee;--attr:#e3a56d;--val:#80d29b;--note:#7e8b98;--pun:#7b8896;--link:#80e0bf;--sel:#27406a}}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.7 ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace;tab-size:2}
::selection{background:var(--sel)}
main{max-width:1200px;margin:0 auto;padding:20px 18px 70px}
.n{margin-left:2ch;white-space:pre-wrap;overflow-wrap:anywhere}
.root{margin-left:0}
.c{color:var(--note);margin-top:.9em}
.c:first-child{margin-top:0}
.t{color:var(--tag);font-weight:600}.a{color:var(--attr)}.v{color:var(--val)}.p{color:var(--pun)}
a{color:var(--link);text-decoration:underline;text-decoration-color:color-mix(in srgb,var(--link) 35%,transparent);text-underline-offset:3px}
a:hover{text-decoration-color:currentColor}
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

<xsl:template match="processing-instruction()">
  <div class="n root"><span class="p">&lt;?</span><span class="t"><xsl:value-of select="name()"/></span><xsl:text> </xsl:text><span class="v"><xsl:value-of select="."/></span><span class="p">?&gt;</span></div>
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
        <xsl:call-template name="open"/><span class="p">&gt;</span>
        <xsl:choose>
          <xsl:when test="local-name()='loc' and (starts-with(., 'http://') or starts-with(., 'https://'))"><a href="{.}"><xsl:value-of select="."/></a></xsl:when>
          <xsl:otherwise><xsl:value-of select="."/></xsl:otherwise>
        </xsl:choose>
        <span class="p">&lt;/</span><span class="t"><xsl:value-of select="name()"/></span><span class="p">&gt;</span>
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
