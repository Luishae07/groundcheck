<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:s="http://www.sitemaps.org/schemas/sitemap/0.9"
  xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>
<xsl:template match="/">
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Groundcheck sitemap</title>
<style>
:root{--bg:#eaf2f9;--ink:#132433;--dim:#4a6278;--card:#ffffff;--line:#d3e0ec;--accent:#2f6fb0}
@media (prefers-color-scheme: dark){:root{--bg:#0b1626;--ink:#eaf2fa;--dim:#9db3c8;--card:#12263b;--line:#22405c;--accent:#7fb4ee}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,system-ui,"Segoe UI",sans-serif}
main{max-width:46rem;margin:0 auto;padding:1.6rem 16px 3rem}
h1{font-size:1.7rem;font-weight:600;margin:0 0 .3rem}
.sub{color:var(--dim);margin:0 0 1.2rem}
.list{display:grid;gap:.6rem}
a.row{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:.8rem 1rem;color:inherit;text-decoration:none}
a.row:active{opacity:.7}
.url{color:var(--accent);font-weight:600;overflow-wrap:anywhere}
.meta{display:flex;flex-wrap:wrap;gap:.3rem .9rem;margin-top:.25rem;color:var(--dim);font-size:.85rem}
.pill{border:1px solid var(--line);border-radius:999px;padding:0 .55rem}
</style>
</head>
<body>
<main>
  <h1>Groundcheck sitemap</h1>
  <p class="sub"><xsl:value-of select="count(s:urlset/s:url)"/> pages. This list is for search engines; people can tap any row to open the page.</p>
  <div class="list">
    <xsl:for-each select="s:urlset/s:url">
      <a class="row" href="{s:loc}">
        <div class="url"><xsl:value-of select="s:loc"/></div>
        <div class="meta">
          <xsl:if test="s:lastmod"><span>updated <xsl:value-of select="s:lastmod"/></span></xsl:if>
          <xsl:if test="s:changefreq"><span class="pill"><xsl:value-of select="s:changefreq"/></span></xsl:if>
          <xsl:if test="s:priority"><span class="pill">priority <xsl:value-of select="s:priority"/></span></xsl:if>
          <xsl:if test="image:image"><span class="pill"><xsl:value-of select="count(image:image)"/> image<xsl:if test="count(image:image) &gt; 1">s</xsl:if></span></xsl:if>
        </div>
      </a>
    </xsl:for-each>
  </div>
</main>
</body>
</html>
</xsl:template>
</xsl:stylesheet>
