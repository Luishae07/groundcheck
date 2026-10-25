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
:root{--bg:#eef2f7;--card:#ffffff;--bar:#ffffffd9;--ink:#1d2733;--tag:#1f5fa8;--attr:#b15a1b;--val:#18794a;--note:#7a8794;--pun:#8d99a7;--guide:#e4eaf1;--hover:#eef4fb;--link:#0b7a5f;--acc:#1f6fd6;--acc2:#15a8a0;--date:#7a3fb0;--num:#c0392b;--shadow:0 1px 2px #0f172a10,0 14px 40px -24px #0f172a40}
@media (prefers-color-scheme: dark){:root{--bg:#0b1016;--card:#111821;--bar:#111821d9;--ink:#dbe4ee;--tag:#7fb4ee;--attr:#e0a36a;--val:#7fd39a;--note:#7f8c99;--pun:#7a8796;--guide:#223041;--hover:#172230;--link:#7fe0bd;--acc:#6fb0ff;--acc2:#4fd8cf;--date:#c39bf0;--num:#ff9b8a;--shadow:0 1px 2px #0006,0 20px 50px -30px #000}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:13.5px/1.7 ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace}
.top{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 16px;background:var(--bar);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--guide)}
.top b{font-size:15px;display:flex;align-items:center;gap:9px}
.top b:before{content:"";width:16px;height:16px;border-radius:5px;background:linear-gradient(135deg,var(--acc),var(--acc2))}
.top .m{color:var(--note);flex:1;min-width:140px}
.top input{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--guide);border-radius:9px;padding:5px 11px;width:200px;outline:none}
.top input:focus{border-color:var(--acc);box-shadow:0 0 0 3px #1f6fd62a}
.top button{font:inherit;color:var(--acc);background:var(--card);border:1px solid var(--guide);border-radius:9px;padding:5px 12px;cursor:pointer}
.top button:hover{background:var(--hover);border-color:var(--acc)}
main{max-width:1100px;margin:22px auto 60px;padding:0 14px}
.code{background:var(--card);border:1px solid var(--guide);border-radius:16px;padding:18px 20px 20px;box-shadow:var(--shadow);overflow:hidden}
.l{white-space:pre-wrap;overflow-wrap:anywhere;padding:0 6px;border-radius:5px}
.l:hover{background:var(--hover)}
.in{margin-left:8px;padding-left:18px;border-left:1px solid var(--guide)}
.in .in{border-left-color:#1f6fd638}
.in .in .in{border-left-color:#15a8a038}
details{margin:0}
details[data-n=url]{margin:6px 0;border-radius:8px}
details[data-n=url]>.in{border-left:2px solid var(--acc);border-left-color:color-mix(in srgb,var(--acc) 45%,transparent)}
summary{list-style:none;cursor:pointer;white-space:pre-wrap;overflow-wrap:anywhere;padding:0 6px;border-radius:5px}
summary::-webkit-details-marker{display:none}
summary:hover{background:var(--hover)}
summary:before{content:"\25BE";display:inline-block;width:15px;margin-left:-15px;color:var(--pun);font-size:11px;transition:transform .15s}
details:not([open])>summary:before{content:"\25B8"}
details:not([open])>summary:after{content:" \2026 &lt;/" attr(data-n) "&gt;";color:var(--pun)}
details[data-n="--"]:not([open])>summary:after{content:" \2026 --&gt;"}
.e{margin-left:15px}
.root{margin-left:0}
.t{color:var(--tag);font-weight:600}.a{color:var(--attr)}.v{color:var(--val)}.p{color:var(--pun)}.c{color:var(--note);font-style:italic}
.d{color:var(--date)}.n{color:var(--num)}
a{color:var(--link);font-weight:600;text-decoration:underline;text-decoration-color:var(--guide);text-decoration-thickness:2px;text-underline-offset:3px}
a:hover{text-decoration-color:currentColor}
.hide{display:none}
.foot{color:var(--note);text-align:center;margin:18px 0 0;font-size:12px}
kbd{font:inherit;background:var(--card);border:1px solid var(--guide);border-bottom-width:2px;border-radius:5px;padding:0 6px}
@media (max-width:640px){.top input{width:100%;order:9}.code{padding:12px 10px 14px;border-radius:12px}main{margin-top:12px}}
</style>
</head>
<body>
<div class="top">
  <b>sitemap.xml</b>
  <span class="m"><xsl:value-of select="count(//*[local-name()='url'])"/> pages · <xsl:value-of select="count(//*[local-name()='image'])"/> images</span>
  <input id="q" type="search" placeholder="Filter pages (press /)" autocomplete="off" aria-label="Filter pages"/>
  <button type="button" onclick="document.querySelectorAll('details').forEach(function(d){{d.open=true}})">Expand all</button>
  <button type="button" onclick="document.querySelectorAll('details').forEach(function(d){{d.open=false}});document.querySelector('details[data-n=urlset]').open=true">Collapse all</button>
</div>
<main>
<div class="code">
<div class="l"><span class="p">&lt;?xml version="1.0" encoding="UTF-8"?&gt;</span></div>
<xsl:apply-templates select="node()"/>
</div>
<p class="foot">This is the plain <code>sitemap.xml</code> with colours, folding and links. Search engines read the XML underneath. <kbd>/</kbd> filters, click any tag to fold it.</p>
</main>
<script>
(function(){
  var q=document.getElementById('q');
  q.addEventListener('input',function(){
    var v=q.value.toLowerCase();
    document.querySelectorAll('details[data-n=url]').forEach(function(d){
      d.style.display=(!v || d.textContent.toLowerCase().indexOf(v)&gt;=0)?'':'none';
    });
  });
  document.addEventListener('keydown',function(e){
    if(e.key==='/' &amp;&amp; document.activeElement!==q){e.preventDefault();q.focus();}
    if(e.key==='Escape' &amp;&amp; document.activeElement===q){q.value='';q.dispatchEvent(new Event('input'));q.blur();}
  });
})();
</script>
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
          <xsl:when test="local-name()='lastmod'"><span class="d"><xsl:value-of select="."/></span></xsl:when>
          <xsl:when test="local-name()='priority' or local-name()='changefreq'"><span class="n"><xsl:value-of select="."/></span></xsl:when>
          <xsl:otherwise><xsl:value-of select="."/></xsl:otherwise>
        </xsl:choose>
        <span class="p">&lt;/</span><span class="t"><xsl:value-of select="name()"/></span><span class="p">&gt;</span>
      </div>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

</xsl:stylesheet>
