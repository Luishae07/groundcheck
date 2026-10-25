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
:root{--bg:#ffffff;--bar:#f3f6fa;--ink:#1d2733;--tag:#1f5fa8;--attr:#a0521c;--val:#1a7a45;--note:#7a8794;--pun:#8895a3;--guide:#e3e9f0;--hover:#eef4fb;--link:#0d6b55;--acc:#1f6fd6}
@media (prefers-color-scheme: dark){:root{--bg:#10151c;--bar:#171e27;--ink:#d8e1ea;--tag:#7fb4ee;--attr:#e0a36a;--val:#7fd39a;--note:#7f8c99;--pun:#7f8c99;--guide:#243040;--hover:#18222e;--link:#7fe0bd;--acc:#6fb0ff}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.65 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;background:var(--bar);border-bottom:1px solid var(--guide)}
.top b{font-size:14px}
.top span.m{color:var(--note);flex:1}
.top button{font:inherit;color:var(--acc);background:none;border:1px solid var(--guide);border-radius:7px;padding:3px 10px;cursor:pointer}
.top button:hover{background:var(--hover)}
main{padding:14px 12px 50px}
.l{white-space:pre-wrap;overflow-wrap:anywhere;padding:0 4px;border-radius:4px}
.l:hover{background:var(--hover)}
.in{margin-left:7px;padding-left:15px;border-left:1px solid var(--guide)}
details{margin:0}
summary{list-style:none;cursor:pointer;white-space:pre-wrap;overflow-wrap:anywhere;padding:0 4px;border-radius:4px}
summary::-webkit-details-marker{display:none}
summary:hover{background:var(--hover)}
summary:before{content:"\25BE";display:inline-block;width:14px;margin-left:-14px;color:var(--pun);font-size:11px}
details:not([open])>summary:before{content:"\25B8"}
details:not([open])>summary:after{content:" \2026 &lt;/" attr(data-n) "&gt;";color:var(--pun)}
details[data-n="--"]:not([open])>summary:after{content:" \2026 --&gt;"}
.e{margin-left:14px}
.root{margin-left:0}
.t{color:var(--tag)}.a{color:var(--attr)}.v{color:var(--val)}.p{color:var(--pun)}.c{color:var(--note);font-style:italic}
a{color:var(--link);text-decoration:underline;text-decoration-color:var(--guide);text-underline-offset:3px}
a:hover{text-decoration-color:currentColor}
</style>
</head>
<body>
<div class="top">
  <b>sitemap.xml</b>
  <span class="m"><xsl:value-of select="count(//*[local-name()='url'])"/> pages · click a tag to fold it</span>
  <button type="button" onclick="document.querySelectorAll('details').forEach(function(d){{d.open=true}})">Expand all</button>
  <button type="button" onclick="document.querySelectorAll('details').forEach(function(d){{d.open=false}});document.querySelector('details[data-n=urlset]').open=true">Collapse all</button>
</div>
<main>
<div class="l"><span class="p">&lt;?xml version="1.0" encoding="UTF-8"?&gt;</span></div>
<xsl:apply-templates select="node()"/>
</main>
</body>
</html>
</xsl:template>

<xsl:template match="processing-instruction()">
  <div class="l"><span class="p">&lt;?</span><span class="t"><xsl:value-of select="name()"/></span><xsl:text> </xsl:text><span class="v"><xsl:value-of select="."/></span><span class="p">?&gt;</span></div>
</xsl:template>

<xsl:template match="comment()">
  <xsl:choose>
    <xsl:when test="contains(., '&#10;')">
      <details class="e"><xsl:attribute name="data-n">--</xsl:attribute>
        <xsl:if test="not(parent::*)"><xsl:attribute name="class">e root</xsl:attribute></xsl:if>
        <xsl:if test="parent::*"><xsl:attribute name="open">open</xsl:attribute></xsl:if>
        <summary class="c"><xsl:text>&lt;!-- comment · </xsl:text><xsl:value-of select="string-length(.) - string-length(translate(., '&#10;', '')) + 1"/><xsl:text> lines</xsl:text></summary>
        <div class="l c"><xsl:value-of select="."/></div>
        <div class="l c">--&gt;</div>
      </details>
    </xsl:when>
    <xsl:otherwise>
      <div class="l c">&lt;!-- <xsl:value-of select="normalize-space(.)"/> --&gt;</div>
    </xsl:otherwise>
  </xsl:choose>
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
  <xsl:choose>
    <xsl:when test="*">
      <details open="open" class="e">
        <xsl:attribute name="data-n"><xsl:value-of select="name()"/></xsl:attribute>
        <xsl:if test="not(parent::*)"><xsl:attribute name="class">e root</xsl:attribute></xsl:if>
        <summary><xsl:call-template name="open"/><span class="p">&gt;</span></summary>
        <div class="in"><xsl:apply-templates select="*|comment()"/></div>
        <div class="l"><span class="p">&lt;/</span><span class="t"><xsl:value-of select="name()"/></span><span class="p">&gt;</span></div>
      </details>
    </xsl:when>
    <xsl:otherwise>
      <div class="l">
        <xsl:call-template name="open"/><span class="p">&gt;</span>
        <xsl:choose>
          <xsl:when test="local-name()='loc' and (starts-with(., 'http://') or starts-with(., 'https://'))"><a href="{.}"><xsl:value-of select="."/></a></xsl:when>
          <xsl:otherwise><xsl:value-of select="."/></xsl:otherwise>
        </xsl:choose>
        <span class="p">&lt;/</span><span class="t"><xsl:value-of select="name()"/></span><span class="p">&gt;</span>
      </div>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

</xsl:stylesheet>
