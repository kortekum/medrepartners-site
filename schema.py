#!/usr/bin/env python3
"""JSON-LD structured data for medrepartners.com.

Single source of truth for the schema layer specified in the SEO
Implementation Plan: Organization + WebSite sitewide, AboutPage + Person on
About, FAQPage on How It Works, Article + BreadcrumbList on Library articles,
CollectionPage on the Library hub, ContactPage on Book a Call.

Used two ways:
- imported by build.py at build time (inject(html, slug))
- run directly to patch an existing dist/ in place:  python3 schema.py

Rules honored (SEO Implementation Plan, Sections 2-3):
- markup mirrors on-page text; FAQ questions/answers are extracted from the
  page itself, never paraphrased
- author attribution lives in schema (no visible bylines, a deliberate
  owner decision recorded in SEO Audit Stage 2)
- sameAs only for real profiles; none exist yet, so none are emitted
"""
import json
import os
import re

BASE = "https://medrepartners.com"
ORG_ID = BASE + "/#organization"
SITE_ID = BASE + "/#website"
ERIKA_ID = BASE + "/about/#erika-christiansen"
STEVE_ID = BASE + "/about/#steve-christiansen"
LOGO = BASE + "/assets/medre_logo.png"

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")

# The classifier sentence (Metadata Master Sheet, Home definition block).
ORG_DESCRIPTION = (
    "Medre is a healthcare real estate company founded by a commercial real "
    "estate broker and a practicing physician. It buys the building a "
    "practice needs, leases it to the practice at fair market rent plus a "
    "small premium, and writes a purchase option into the documents at year "
    "5 or year 10."
)

ERIKA = {
    "@type": "Person",
    "@id": ERIKA_ID,
    "name": "Erika Christiansen",
    "jobTitle": "Commercial real estate broker",
    "description": "Licensed Colorado commercial real estate broker and co-founder of Medre.",
    "hasCredential": {
        "@type": "EducationalOccupationalCredential",
        "credentialCategory": "license",
        "name": "Colorado commercial real estate broker license",
    },
    "url": BASE + "/about/",
    "worksFor": {"@id": ORG_ID},
}

STEVE = {
    "@type": "Person",
    "@id": STEVE_ID,
    "name": "Steve Christiansen",
    "honorificSuffix": "MD",
    "jobTitle": "Retina specialist",
    "description": "Practicing retina specialist running a multi-location practice in Colorado, and co-founder of Medre.",
    "url": BASE + "/about/",
    "worksFor": {"@id": ORG_ID},
}


def org_node():
    return {
        "@type": "Organization",
        "@id": ORG_ID,
        "name": "Medre",
        "legalName": "MedRe Partners, LLC",
        "url": BASE + "/",
        "logo": {"@type": "ImageObject", "url": LOGO},
        "description": ORG_DESCRIPTION,
        "email": "hello@medrepartners.com",
        "founder": [{"@id": ERIKA_ID}, {"@id": STEVE_ID}],
        "address": {
            "@type": "PostalAddress",
            "addressRegion": "CO",
            "addressCountry": "US",
        },
        "areaServed": "US",
    }


def website_node():
    return {
        "@type": "WebSite",
        "@id": SITE_ID,
        "name": "Medre",
        "url": BASE + "/",
        "publisher": {"@id": ORG_ID},
    }


# Article author overrides (Metadata Master Sheet bylines). Everything else
# is credited to both founders, matching the Library's "Who writes this".
AUTHOR_OVERRIDES = {
    "library/rent-buy-or-wait": [ERIKA],
    "library/sale-leaseback-explained": [ERIKA],
    "library/personal-guarantee": [STEVE],
}

LAUNCH_DATE = "2026-07-10"

PAGE_TYPES = {
    "": "WebPage",
    "how-it-works": "WebPage",
    "for-practice-owners": "WebPage",
    "about": "AboutPage",
    "library": "CollectionPage",
    "book-a-call": "ContactPage",
    "privacy": "WebPage",
}


def _meta(html, pattern):
    m = re.search(pattern, html)
    return m.group(1).strip() if m else None


def _faq_entities(html):
    """Extract the FAQ Q&As that follow the 'Questions' section heading.
    Markup and text are taken verbatim from the page (tags stripped)."""
    m = re.search(r"<h2[^>]*>\s*The fine print, in plain English\.\s*</h2>", html)
    if not m:
        return []
    tail = html[m.end():]
    pairs = re.findall(r"<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>", tail, re.S)
    entities = []
    for q, a in pairs:
        q = re.sub(r"<[^>]+>", "", q)
        a = re.sub(r"<[^>]+>", "", a)
        q = re.sub(r"\s+", " ", q).strip()
        a = re.sub(r"\s+", " ", a).strip()
        if q and a:
            entities.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            })
    return entities


def graph_for(slug, html):
    """Build the @graph for one page. Returns None for pages that get no
    structured data (404, redirect stubs, print pieces)."""
    if slug.startswith("print/") or slug == "404":
        return None

    url = BASE + "/" + (slug + "/" if slug else "")
    title = _meta(html, r"<title>(.*?)</title>") or "Medre"
    desc = _meta(html, r'<meta name="description" content="([^"]*)"') or ""

    graph = [org_node(), website_node()]

    if slug.startswith("library/"):
        og_title = _meta(html, r'<meta property="og:title" content="([^"]*)"')
        graph.append({
            "@type": "Article",
            "@id": url + "#article",
            "headline": og_title or title,
            "description": desc,
            "url": url,
            "mainEntityOfPage": url,
            "author": AUTHOR_OVERRIDES.get(slug, [ERIKA, STEVE]),
            "publisher": {"@id": ORG_ID},
            "datePublished": LAUNCH_DATE,
            "dateModified": LAUNCH_DATE,
            "image": LOGO,
            "isPartOf": {"@id": SITE_ID},
        })
        graph.append({
            "@type": "BreadcrumbList",
            "@id": url + "#breadcrumbs",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Library",
                 "item": BASE + "/library/"},
                {"@type": "ListItem", "position": 2,
                 "name": (og_title or title), "item": url},
            ],
        })
        return graph

    page_type = PAGE_TYPES.get(slug, "WebPage")
    page = {
        "@type": page_type,
        "@id": url + "#webpage",
        "name": title,
        "description": desc,
        "url": url,
        "isPartOf": {"@id": SITE_ID},
        "about": {"@id": ORG_ID},
    }
    graph.append(page)

    if slug == "about":
        graph.append(ERIKA)
        graph.append(STEVE)

    if slug == "how-it-works":
        faqs = _faq_entities(html)
        if faqs:
            graph.append({
                "@type": "FAQPage",
                "@id": url + "#faq",
                "mainEntity": faqs,
            })

    return graph


def inject(html, slug):
    """Insert the JSON-LD block before </head>. Idempotent."""
    if 'application/ld+json' in html:
        return html
    graph = graph_for(slug, html)
    if not graph:
        return html
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         ensure_ascii=False, indent=1)
    block = f'<script type="application/ld+json">\n{payload}\n</script>\n'
    return html.replace("</head>", block + "</head>", 1)


def patch_dist():
    """Patch an already-built dist/ in place (used until build.py runs in CI)."""
    patched = []
    for root, _dirs, files in os.walk(DIST):
        for f in files:
            if f != "index.html" and f != "404.html":
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, DIST)
            if rel == "index.html":
                slug = ""
            elif rel == "404.html":
                slug = "404"
            else:
                slug = os.path.dirname(rel).replace(os.sep, "/")
            if slug in ("for-physicians", "resources"):  # redirect stubs
                continue
            html = open(path, encoding="utf-8").read()
            new = inject(html, slug)
            if new != html:
                open(path, "w", encoding="utf-8").write(new)
                patched.append(slug or "/")
    print(f"Injected JSON-LD into {len(patched)} pages:")
    for s in sorted(patched):
        print("  ", s)


if __name__ == "__main__":
    patch_dist()
