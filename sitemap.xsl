<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:sm="http://www.sitemaps.org/schemas/sitemap/0.9"
  xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
  exclude-result-prefixes="sm image">
<xsl:output method="html" encoding="UTF-8" indent="no" doctype-system="about:legacy-compat"/>

<xsl:template match="/">
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="robots" content="noindex"/>
<title>Groundcheck sitemap</title>
<style>
:root{--bg:#f4f7fb;--card:#ffffff;--ink:#16202c;--dim:#667587;--line:#e1e8f0;--acc:#1f6fd6;--acc2:#15a8a0;--bar:#e6edf5;--code:#eef3f9}
@media (prefers-color-scheme: dark){:root{--bg:#0d1218;--card:#151c25;--ink:#e4ebf3;--dim:#8a98a8;--line:#243040;--acc:#6fb0ff;--acc2:#4fd8cf;--bar:#222d3a;--code:#1b2530}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1000px;margin:0 auto;padding:34px 16px 60px}
h1{font-size:30px;margin:0 0 6px;letter-spacing:-.4px}
h1:before{content:"";display:inline-block;width:26px;height:26px;border-radius:8px;margin-right:12px;vertical-align:-3px;background:linear-gradient(135deg,var(--acc),var(--acc2))}
.lead{color:var(--dim);margin:0 0 22px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 20px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 18px;min-width:130px}
.stat b{display:block;font-size:26px;line-height:1.1;font-variant-numeric:tabular-nums}
.stat small{color:var(--dim);text-transform:uppercase;letter-spacing:.08em;font-size:11px;font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden}
table{border-collapse:collapse;width:100%}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--dim);padding:12px 16px;border-bottom:1px solid var(--line);background:var(--code)}
td{padding:14px 16px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
tr:hover td{background:var(--code)}
a{color:var(--acc);text-decoration:none;font-weight:600;overflow-wrap:anywhere}
a:hover{text-decoration:underline}
.note{display:block;color:var(--dim);font-size:13px;font-weight:400;margin-top:4px;max-width:60ch}
.mono{font-variant-numeric:tabular-nums;white-space:nowrap}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;background:var(--code);font-size:12px;color:var(--dim)}
.bar{display:inline-block;width:70px;height:7px;border-radius:9px;background:var(--bar);vertical-align:middle;margin-right:8px;overflow:hidden}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--acc),var(--acc2));border-radius:9px}
details{margin:22px 0 0;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 18px}
summary{cursor:pointer;font-weight:600}
pre{margin:12px 0 0;white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.55 ui-monospace,Menlo,Consolas,monospace;color:var(--dim)}
.foot{color:var(--dim);font-size:13px;margin-top:22px}
@media (max-width:700px){
  thead{display:none}
  table,tbody,tr,td{display:block;width:100%}
  tr{padding:12px 14px;border-bottom:1px solid var(--line)}
  tr:last-child{border-bottom:0}
  td{padding:3px 0;border:0}
  td:before{content:attr(data-l);display:inline-block;min-width:76px;color:var(--dim);font-size:12px}
  td.u:before{display:none}
  tr:hover td{background:none}
}
</style>
</head>
<body>
<main>
  <h1>Groundcheck sitemap</h1>
  <p class="lead">Every page of the site, as search engines see it. This is the human view of <code>sitemap.xml</code>.</p>
  <div class="stats">
    <div class="stat"><b><xsl:value-of select="count(sm:urlset/sm:url)"/></b><small>pages</small></div>
    <div class="stat"><b><xsl:value-of select="count(sm:urlset/sm:url/image:image)"/></b><small>images</small></div>
    <div class="stat"><b>
      <xsl:for-each select="sm:urlset/sm:url/sm:lastmod">
        <xsl:sort select="." order="descending"/>
        <xsl:if test="position()=1"><xsl:value-of select="."/></xsl:if>
      </xsl:for-each>
    </b><small>last change</small></div>
  </div>
  <div class="card">
    <table>
      <thead><tr><th>Page</th><th>Updated</th><th>Changes</th><th>Priority</th><th>Images</th></tr></thead>
      <tbody>
        <xsl:for-each select="sm:urlset/sm:url">
          <xsl:variable name="note" select="preceding-sibling::node()[not(self::text())][1][self::comment()]"/>
          <tr>
            <td class="u">
              <a href="{sm:loc}"><xsl:value-of select="substring-after(sm:loc,'://')"/></a>
              <xsl:if test="$note"><span class="note"><xsl:value-of select="normalize-space($note)"/></span></xsl:if>
            </td>
            <td class="mono" data-l="Updated"><xsl:value-of select="sm:lastmod"/></td>
            <td data-l="Changes"><xsl:if test="sm:changefreq"><span class="pill"><xsl:value-of select="sm:changefreq"/></span></xsl:if></td>
            <td class="mono" data-l="Priority"><xsl:if test="sm:priority"><span class="bar"><i style="width:{sm:priority * 100}%"></i></span><xsl:value-of select="sm:priority"/></xsl:if></td>
            <td class="mono" data-l="Images"><xsl:value-of select="count(image:image)"/></td>
          </tr>
        </xsl:for-each>
      </tbody>
    </table>
  </div>
  <xsl:if test="/comment()">
    <details>
      <summary>About this file</summary>
      <pre><xsl:value-of select="/comment()[1]"/></pre>
    </details>
  </xsl:if>
  <p class="foot">Looking for the raw XML? Use your browser's “view source” (Ctrl+U).</p>
</main>
</body>
</html>
</xsl:template>
</xsl:stylesheet>
