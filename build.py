#!/usr/bin/env python3
"""Build script: converts Claude Design (.dc.html) source pages into a
deployable static site in dist/.

- Extracts each page's <helmet> into a real <head>
- Unwraps the <x-dc> template into the <body> (no client-side runtime needed;
  all pages are static templates)
- Print pages: <x-import doc-page> becomes a real <doc-page> element backed
  by doc-page.js
- Rewrites internal links from "Page Name.dc.html" to the locked slugs from
  the Metadata Master Sheet
- Emits sitemap.xml, robots.txt, 404.html, and meta-refresh redirect stubs
"""
import os
import re
import shutil
import urllib.parse

import schema

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source")
DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
BASE = "https://medrepartners.com"

# filename -> slug ('' = site root, '404' = error page)
SLUGS = {
    "Home.dc.html": "",
    "How It Works.dc.html": "how-it-works",
    "For Practice Owners.dc.html": "for-practice-owners",
    "About.dc.html": "about",
    "Resources.dc.html": "library",
    "Book a Call.dc.html": "book-a-call",
    "Privacy.dc.html": "privacy",
    "404.dc.html": "404",
    "Rent Buy or Wait.dc.html": "library/rent-buy-or-wait",
    "Sale-Leaseback Explained.dc.html": "library/sale-leaseback-explained",
    "Personal Guarantee.dc.html": "library/personal-guarantee",
    "Is a Purchase Option Real.dc.html": "library/purchase-options",
    "Renewal Calendar.dc.html": "library/lease-renewal",
    "When Owning Is Cheaper.dc.html": "library/when-owning-is-cheaper",
    "How Much Space.dc.html": "library/how-much-space",
    "Outgrowing Your Space.dc.html": "library/outgrowing-your-space",
    "Estate Attorney Questions.dc.html": "library/estate-attorney-questions",
    "Expansion and Real Estate Risk.dc.html": "library/expansion-and-real-estate-risk",
    "Building and Practice Sale.dc.html": "library/building-and-practice-sale",
    "Short Lease or Long Lease.dc.html": "library/short-lease-or-long-lease",
    "First Lease vs Logo.dc.html": "library/first-lease-vs-logo",
    "Refinance or Sale-Leaseback.dc.html": "library/refinance-or-sale-leaseback",
    "Reading a Sale-Leaseback Offer.dc.html": "library/reading-a-sale-leaseback-offer",
    "Renewal When Moving Is Not Realistic.dc.html": "library/renewal-when-moving-is-not-realistic",
    "Medre One-Page Guide (Print).dc.html": "print/one-page-guide",
    "Sale-Leaseback Checklist (Print).dc.html": "print/sale-leaseback-checklist",
}

REDIRECTS = {
    "for-physicians": "/for-practice-owners/",
    "resources": "/library/",
}

NOINDEX = {"404", "print/one-page-guide", "print/sale-leaseback-checklist"}  # slugs excluded from sitemap


def slug_to_url(slug):
    if slug == "":
        return "/"
    return f"/{slug}/"


def rewrite_links(html):
    """Rewrite href/src that point at .dc.html files or bare assets/ paths."""

    def repl(m):
        attr, quote, val = m.group(1), m.group(2), m.group(3)
        raw = val
        anchor = ""
        if "#" in raw:
            raw, anchor = raw.split("#", 1)
            anchor = "#" + anchor
        decoded = urllib.parse.unquote(raw)
        if decoded in SLUGS:
            target = slug_to_url(SLUGS[decoded])
            if SLUGS[decoded] == "404":
                target = "/404.html"
            return f"{attr}={quote}{target}{anchor}{quote}"
        if decoded.startswith("assets/") or decoded.startswith("./assets/"):
            return f"{attr}={quote}/{decoded.lstrip('./')}{quote}"
        if decoded in ("./doc-page.js", "doc-page.js"):
            return f"{attr}={quote}/doc-page.js{quote}"
        return m.group(0)

    return re.sub(r'(href|src)=("|\')([^"\']+)(\2)',
                  lambda m: repl(m), html)


def build_page(fname, slug):
    src = open(os.path.join(SRC, fname), encoding="utf-8").read()

    m = re.search(r"<x-dc(?:\s[^>]*)?>(.*)</x-dc>", src, re.S)
    if not m:
        raise SystemExit(f"{fname}: no <x-dc> template found")
    inner = m.group(1)

    hm = re.search(r"<helmet>(.*?)</helmet>", inner, re.S)
    helmet = hm.group(1).strip() if hm else ""
    body = inner.replace(hm.group(0), "", 1) if hm else inner

    # strip the inert data-dc-script blocks (all are empty scaffolds)
    body = re.sub(r"<script[^>]*data-dc-script[^>]*>.*?</script>", "", body, flags=re.S)

    # print pages: <x-import ... from="./doc-page.js" size=... margin=...> -> <doc-page>
    doc_page = False
    xi = re.search(r"<x-import([^>]*)>", body)
    if xi and "doc-page" in xi.group(1):
        doc_page = True
        attrs = xi.group(1)
        size = re.search(r'size="([^"]*)"', attrs)
        margin = re.search(r'margin="([^"]*)"', attrs)
        dp_attrs = ""
        if size:
            dp_attrs += f' size="{size.group(1)}"'
        if margin:
            dp_attrs += f' margin="{margin.group(1)}"'
        body = body.replace(xi.group(0), f"<doc-page{dp_attrs}>", 1)
        body = body.replace("</x-import>", "</doc-page>", 1)

    # retired-domain references in visible copy (print footers)
    body = body.replace("medre.co", "medrepartners.com")
    body = rewrite_links(body).strip()
    helmet = rewrite_links(helmet)

    url = BASE + slug_to_url(slug) if slug != "404" else None

    title_m = re.search(r"<title>(.*?)</title>", helmet, re.S)
    desc_m = re.search(r'<meta name="description" content="([^"]*)"', helmet)
    title = title_m.group(1).strip() if title_m else "Medre"
    desc = desc_m.group(1) if desc_m else ""

    head_extra = []
    if url:
        # helmet og:url values point at the retired medre.co domain with old
        # slugs; rewrite them to the real canonical URL instead of duplicating
        helmet = re.sub(r'(<meta property="og:url" content=")[^"]*(")',
                        lambda m: m.group(1) + url + m.group(2), helmet)
        head_extra.append(f'<link rel="canonical" href="{url}">')
        if 'property="og:title"' not in helmet:
            head_extra.append(f'<meta property="og:title" content="{title}">')
        if desc and 'property="og:description"' not in helmet:
            head_extra.append(f'<meta property="og:description" content="{desc}">')
        if 'property="og:url"' not in helmet:
            head_extra.append(f'<meta property="og:url" content="{url}">')
        if 'property="og:type"' not in helmet:
            head_extra.append('<meta property="og:type" content="website">')
        head_extra.append(f'<meta property="og:site_name" content="Medre">')
        head_extra.append(f'<meta property="og:image" content="{BASE}/assets/medre_logo.png">')
        head_extra.append('<meta name="twitter:card" content="summary">')
        if slug.startswith("print/"):
            head_extra.append('<meta name="robots" content="noindex">')
    else:
        head_extra.append('<meta name="robots" content="noindex">')

    dp_style = "<style>doc-page:not(:defined){visibility:hidden}</style>\n" if doc_page else ""
    dp_script = '<script src="/doc-page.js"></script>\n' if doc_page else ""

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{helmet}
{chr(10).join(head_extra)}
{dp_style}</head>
<body>
{body}
{dp_script}</body>
</html>
"""

    if slug == "404":
        out = os.path.join(DIST, "404.html")
    elif slug == "":
        out = os.path.join(DIST, "index.html")
    else:
        os.makedirs(os.path.join(DIST, slug), exist_ok=True)
        out = os.path.join(DIST, slug, "index.html")
    page = schema.inject(page, slug)
    open(out, "w", encoding="utf-8").write(page)
    return url


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    urls = []
    for fname, slug in SLUGS.items():
        url = build_page(fname, slug)
        if url and slug not in NOINDEX:
            urls.append(url)

    shutil.copytree(os.path.join(SRC, "assets"), os.path.join(DIST, "assets"))
    shutil.copy(os.path.join(SRC, "doc-page.js"), os.path.join(DIST, "doc-page.js"))

    # defensive redirects (static host: meta refresh + canonical)
    for frm, to in REDIRECTS.items():
        os.makedirs(os.path.join(DIST, frm), exist_ok=True)
        stub = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url={to}">
<link rel="canonical" href="{BASE}{to}">
<meta name="robots" content="noindex">
<title>Redirecting</title></head>
<body><p>This page has moved to <a href="{to}">{BASE}{to}</a>.</p></body></html>
"""
        open(os.path.join(DIST, frm, "index.html"), "w").write(stub)

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in sorted(urls):
        sitemap.append(f"  <url><loc>{u}</loc></url>")
    sitemap.append("</urlset>")
    open(os.path.join(DIST, "sitemap.xml"), "w").write("\n".join(sitemap) + "\n")

    open(os.path.join(DIST, "robots.txt"), "w").write(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")

    print(f"Built {len(SLUGS)} pages + {len(REDIRECTS)} redirects -> dist/")


if __name__ == "__main__":
    main()
