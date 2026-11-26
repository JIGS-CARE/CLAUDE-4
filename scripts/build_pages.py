"""
Build search-engine pages from homes.json (and photos.json / reviews.json if present):

  /homes/                                  all counties
  /homes/<county>/                         every home in a county, grouped by city
  /homes/<county>/<home-name>-<license>/   one page per home (6,854 pages)
  /sitemap.xml                             every page, for Google

Google can't read the "#home-…" addresses the app uses, so these real pages are how the
directory gets found. Each page links into the app for tours, saving and claiming.

Netlify runs this on every deploy (see netlify.toml). To run it yourself:  python scripts/build_pages.py
Standard library only. Set SITE_URL if the domain isn't https://jigscare.com.
"""
import html, json, os, re, shutil, hashlib, unicodedata
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.environ.get("SITE_URL", "https://jigscare.com").rstrip("/")
OUT = os.path.join(ROOT, "homes")

SPEC = {"D": "Dementia", "M": "Mental health", "X": "Developmental disabilities"}
KIND = {"A": "Adult family home", "L": "Assisted living community"}
FALLBACK = ['photo-1787094523866-2556cb09110f', 'photo-1787094497609-5efe6029b950', 'photo-1631458325834-8f678e48912c',
            'photo-1787094517400-ee58a5decd95', 'photo-1625602812206-5ec545ca1231', 'photo-1628624747271-4df6ca1e1ba3',
            'photo-1631149784601-8e6c266b046a', 'photo-1570129477492-45c003edd2be', 'photo-1767832340276-d59223a88d3c',
            'photo-1558036117-15d82a90b9b1', 'photo-1586982599726-11708daaceca', 'photo-1762119594563-fc90dabb6161',
            'photo-1745808930196-e03bf5fe6c02', 'photo-1785108582166-933ba80037fe',
            'photo-1755114203680-d39d95efa82c', 'photo-1761013320045-d29e4f10bcbc', 'photo-1760648984277-2c7ea436a10b']

e = lambda s: html.escape(str(s or ""), quote=True)


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:70].rstrip("-") or "home"


def clean_name(n):
    # same idea as the app: drop list-gaming prefixes like "!!", "00001 ", "1 " at the start
    s = n
    for _ in range(6):
        t = re.sub(r"^(?:[^A-Za-z0-9]+|0\d*\s+|1(?=[^0-9A-Za-z])\s*)\s*", "", s)
        if t == s:
            break
        s = t
    s = s or n
    s = re.sub(r"(\d)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), s)
    return s


def dshs_links(h):
    a = h["type"] == "A"
    return {
        "lookup": "https://fortress.wa.gov/dshs/adsaapps/lookup/" + ("AFHPubLookup.aspx" if a else "BHPubLookup.aspx"),
        "reports": f"https://fortress.wa.gov/dshs/adsaapps/lookup/{'AFH' if a else 'BH'}Forms.aspx?lic={h['lic']}",
        "services": f"https://fortress.wa.gov/dshs/adsaapps/lookup/AFHServices.aspx?lic={h['lic']}" if a else "",
    }


def photo_for(h, ph):
    if ph and h["lic"] in ph.get("map", {}):
        p = ph["photos"][ph["map"][h["lic"]]]
        if p[0] == "p":
            return (f"https://images.pexels.com/photos/{p[1]}/pexels-photo-{p[1]}.jpeg?auto=compress&cs=tinysrgb&fit=crop&w=900&h=563",
                    p[2], "Pexels", f"https://www.pexels.com/photo/{p[1]}/")
        user = p[3] if len(p) > 3 else ""
        return (f"https://images.unsplash.com/{p[1]}?auto=format&fit=crop&w=900&h=563&q=70", p[2], "Unsplash",
                f"https://unsplash.com/@{user}?utm_source=jigscare&utm_medium=referral" if user else "https://unsplash.com/")
    i = int(hashlib.sha1(h["lic"].encode()).hexdigest(), 16) % len(FALLBACK)
    return (f"https://images.unsplash.com/{FALLBACK[i]}?auto=format&fit=crop&w=900&h=563&q=70", "", "Unsplash", "https://unsplash.com/")


HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}"><link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="JIGS CARE"><meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}"><meta property="og:url" content="{url}"><meta property="og:image" content="{image}">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#F8F4EF">
<link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/pages.css">{ld}</head><body>
<header><div class="wrap"><a href="/" class="brand" aria-label="JIGS CARE home"><img src="/brand/jigs-care-logo-horizontal.svg" alt="JIGS CARE" width="210" height="55"></a>
<nav><a href="/#find">Find a home</a><a href="/homes/">By county</a><a href="/#guide">How to choose</a><a href="/#claim" class="cta">Claim your home</a></nav></div></header>
<main class="wrap">"""

FOOT = """</main><footer><div class="wrap"><p><b>JIGS CARE</b> · Intelligent Care. Trusted People. Healthier Families.</p>
<p>Free for families, caregivers and every home to list. Homes pay only to be featured.</p>
<p>Source: Washington DSHS long-term care residential care open data, as of {asof}. License information shows only what was checked, the source, and the date. JIGS CARE does not certify homes.</p>
<p>Sample house photos from Pexels and Unsplash. They are not the actual homes. · <a href="mailto:hello@jigscare.com">hello@jigscare.com</a> · A product of IRUSH GROUP LLC · Washington State</p></div></footer></body></html>"""


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, separators=(",", ":")).replace("</", "<\\/") + "</script>"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    data = json.load(open(os.path.join(ROOT, "homes.json"), encoding="utf-8"))
    ph_path = os.path.join(ROOT, "photos.json")
    ph = json.load(open(ph_path, encoding="utf-8")) if os.path.exists(ph_path) else None
    rv_path = os.path.join(ROOT, "reviews.json")
    reviews = json.load(open(rv_path, encoding="utf-8")) if os.path.exists(rv_path) else []
    asof = data["meta"]["asOf"]
    asof_txt = date.fromisoformat(asof).strftime("%b %d, %Y").replace(" 0", " ")

    homes, seen = [], set()
    for r in data["rows"]:
        if r[0] in seen:          # DSHS file has the odd duplicate license; keep the first
            continue
        seen.add(r[0])
        h = dict(zip(data["meta"]["fields"], r))
        h["name"] = clean_name(h["name"])
        h["cslug"] = slug(h["county"])
        h["url"] = f"/homes/{h['cslug']}/{slug(h['name'])}-{h['lic']}/"
        homes.append(h)

    shutil.rmtree(OUT, ignore_errors=True)
    by_county = defaultdict(list)
    for h in homes:
        by_county[h["county"]].append(h)
    by_city = defaultdict(list)
    for h in homes:
        by_city[(h["county"], h["city"], h["type"])].append(h)

    og_default = SITE + "/og-image.png"
    urls = [SITE + "/", SITE + "/homes/"]

    # ── one page per home ──
    for h in homes:
        kind = KIND[h["type"]]
        specs = [SPEC[c] for c in (h.get("spec") or "") if c in SPEC]
        url = SITE + h["url"]
        img, by, src, page = photo_for(h, ph)
        lk = dshs_links(h)
        rv = [x for x in reviews if str(x.get("lic")) == h["lic"]]
        title = f"{h['name']} · {kind} in {h['city']}, WA | JIGS CARE"
        desc = (f"{h['name']} is a licensed {kind.lower()} in {h['city']}, {h['county']} County, WA, licensed for {h['beds']} residents"
                + (f", with state specialties in {', '.join(specs).lower()}" if specs else "")
                + (", and a Medicaid contract" if h.get("medicaid") else "") + ". See its DSHS license and inspection reports, and request a tour free.")
        biz = {"@context": "https://schema.org", "@type": "LocalBusiness", "name": h["name"], "url": url, "image": img,
               "telephone": h.get("phone") or None,
               "address": {"@type": "PostalAddress", "streetAddress": h["addr"], "addressLocality": h["city"],
                           "addressRegion": "WA", "postalCode": h["zip"], "addressCountry": "US"}}
        if h.get("lat") and h.get("lon"):
            biz["geo"] = {"@type": "GeoCoordinates", "latitude": h["lat"], "longitude": h["lon"]}
        if rv:
            biz["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": round(sum(x["rating"] for x in rv) / len(rv), 1), "reviewCount": len(rv)}
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Homes by county", "item": SITE + "/homes/"},
            {"@type": "ListItem", "position": 2, "name": f"{h['county']} County", "item": f"{SITE}/homes/{h['cslug']}/"},
            {"@type": "ListItem", "position": 3, "name": h["name"], "item": url}]}
        near = [x for x in by_city[(h["county"], h["city"], h["type"])] if x["lic"] != h["lic"]][:8]
        credit = f'Sample photo{f" by <a href={chr(34)}{e(page)}{chr(34)} rel={chr(34)}noopener{chr(34)}>{e(by)}</a> on {src}" if by else ""}, not this home. The owner can replace it with a real photo.'
        body = f"""<nav class="crumbs" aria-label="Breadcrumb"><a href="/homes/">Homes by county</a> › <a href="/homes/{h['cslug']}/">{e(h['county'])} County</a> › <span>{e(h['name'])}</span></nav>
<div class="hero"><div class="info">
<p class="eyebrow">{e(kind)} · {e(h['city'])}, WA</p><h1>{e(h['name'])}</h1>
<p class="addr">{e(h['addr'])}, {e(h['city'])}, WA {e(h['zip'])}{f' · <a href="tel:{re.sub(r"[^0-9]", "", h["phone"])}">{e(h["phone"])}</a>' if h.get('phone') else ''}</p>
<div class="facts"><div><span>Licensed for</span><b>{h['beds']} residents</b></div><div><span>Specialties (state license)</span><b>{e(', '.join(specs) or 'None listed')}</b></div>
<div><span>Medicaid</span><b>{'Has a DSHS contract' if h.get('medicaid') else 'No Medicaid contract listed'}</b></div><div><span>License</span><b>{e(h['lic'])}</b></div></div>
<p class="check">License {e(h['lic'])} checked {asof_txt} · source: Washington DSHS. <a href="{e(lk['reports'])}" rel="noopener">Inspection reports (DSHS)</a>{f' · <a href="{e(lk["services"])}" rel="noopener">Services disclosure (DSHS)</a>' if lk['services'] else ''}</p>
<p class="ctas"><a class="btn pri" href="/#home-{h['lic']}">Request a tour, free</a><a class="btn" href="/#claim-{h['lic']}">Own this home? Claim it free</a></p>
</div><figure class="pic"><div class="phb"><img src="{e(img)}" alt="Sample photo of a house, not {e(h['name'])}" width="900" height="563" loading="eager"><span class="sph">Sample photo</span></div><figcaption>{credit}</figcaption></figure></div>
{('<section><h2>Family reviews</h2>' + ''.join(f'<div class="rev"><p class="rst">{"★" * x["rating"]}{"☆" * (5 - x["rating"])}</p><p>{e(x["text"])}</p><p class="note">{e(x["name"])} · {e(x.get("rel", ""))}</p></div>' for x in rv) + '</section>') if rv else ''}
<section class="help"><h2>Before you choose</h2><p>Ask to see the home's inspection reports, tour at different times of day, and ask who is on duty at night. <a href="/#guide">Read our free guide to choosing a home</a>.</p></section>
{('<section><h2>Other ' + ('adult family homes' if h['type'] == 'A' else 'assisted living communities') + f' in {e(h["city"])}</h2><ul class="near">' + ''.join(f'<li><a href="{x["url"]}">{e(x["name"])}</a> <span>{x["beds"]} beds</span></li>' for x in near) + f'</ul><p><a href="/homes/{h["cslug"]}/">All homes in {e(h["county"])} County</a></p></section>') if near else ''}"""
        write(os.path.join(ROOT, h["url"].strip("/"), "index.html"),
              HEAD.format(title=e(title), desc=e(desc), url=e(url), image=e(img), ld=ld(biz) + ld(crumbs)) + body + FOOT.format(asof=asof_txt))
        urls.append(url)

    # ── one page per county ──
    counties = sorted(by_county)
    for c in counties:
        hs = by_county[c]
        afh = [h for h in hs if h["type"] == "A"]
        alf = [h for h in hs if h["type"] != "A"]
        cslug = hs[0]["cslug"]
        url = f"{SITE}/homes/{cslug}/"

        def block(lst, label):
            if not lst:
                return ""
            cities = defaultdict(list)
            for h in lst:
                cities[h["city"]].append(h)
            out = f"<section><h2>{label} ({len(lst):,})</h2>"
            for city in sorted(cities):
                out += f'<h3>{e(city)}</h3><ul class="near">' + "".join(
                    f'<li><a href="{h["url"]}">{e(h["name"])}</a> <span>{h["beds"]} beds{" · " + ", ".join(SPEC[s] for s in (h.get("spec") or "") if s in SPEC) if h.get("spec") else ""}</span></li>'
                    for h in sorted(cities[city], key=lambda x: x["name"].lower())) + "</ul>"
            return out + "</section>"
        title = f"Adult Family Homes in {c} County, WA: {len(afh):,} Licensed Homes | JIGS CARE"
        desc = f"All {len(afh):,} licensed adult family homes in {c} County, Washington, with state license and inspection links. Free for families."
        body = (f'<nav class="crumbs" aria-label="Breadcrumb"><a href="/homes/">Homes by county</a> › <span>{e(c)} County</span></nav>'
                f'<h1>Adult family homes in {e(c)} County, WA</h1><p class="lede">{len(afh):,} licensed adult family homes'
                + (f" and {len(alf):,} assisted living communities" if alf else "")
                + f', from Washington DSHS records as of {asof_txt}. <a href="/#county-{cslug}">Search and filter these homes</a>, or open any home below.</p>'
                + block(afh, "Adult family homes") + block(alf, "Assisted living communities"))
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Homes by county", "item": SITE + "/homes/"},
            {"@type": "ListItem", "position": 2, "name": f"{c} County", "item": url}]}
        write(os.path.join(OUT, cslug, "index.html"),
              HEAD.format(title=e(title), desc=e(desc), url=e(url), image=e(og_default), ld=ld(crumbs)) + body + FOOT.format(asof=asof_txt))
        urls.append(url)

    # ── all counties ──
    total_afh = sum(1 for h in homes if h["type"] == "A")
    body = (f'<h1>Adult family homes in Washington, by county</h1><p class="lede">{total_afh:,} licensed adult family homes across '
            f'{len(counties)} counties, from Washington DSHS records as of {asof_txt}.</p><ul class="counties">'
            + "".join(f'<li><a href="/homes/{by_county[c][0]["cslug"]}/">{e(c)} County</a> <span>{sum(1 for h in by_county[c] if h["type"] == "A"):,} homes</span></li>' for c in counties)
            + "</ul>")
    write(os.path.join(OUT, "index.html"),
          HEAD.format(title="Adult Family Homes in Washington by County | JIGS CARE",
                      desc=e(f"Browse all {total_afh:,} licensed adult family homes in Washington by county, with DSHS license and inspection links."),
                      url=e(SITE + "/homes/"), image=e(og_default), ld="") + body + FOOT.format(asof=asof_txt))

    # ── sitemap ──
    today = date.today().isoformat()
    write(os.path.join(ROOT, "sitemap.xml"), '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"<url><loc>{e(u)}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    print(f"Built {len(homes):,} home pages, {len(counties)} county pages, sitemap with {len(urls):,} URLs.")


if __name__ == "__main__":
    main()
