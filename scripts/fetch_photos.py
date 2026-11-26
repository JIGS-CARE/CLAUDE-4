"""
Build photos.json: one different real house photo for every home in homes.json.

Photos come from free stock libraries (Pexels, and Unsplash if you add a key). They are NOT
pictures of the actual homes, so the site always tags them "Sample photo" until an owner
uploads a real one. Never use photos copied from Zillow, Redfin, MLS or Google Street View:
those are copyrighted or licensed and can't be reused here.

Usage (needs Python 3.9+, no extra packages):
    set PEXELS_API_KEY=your_key            (Windows)   export PEXELS_API_KEY=your_key   (Mac/Linux)
    set UNSPLASH_ACCESS_KEY=your_key       (optional, adds more variety)
    python scripts/fetch_photos.py

Free keys: https://www.pexels.com/api/  and  https://unsplash.com/developers
Runs again safely: homes keep the photo they already have, and only new homes get new photos.
"""
import json, os, sys, time, hashlib, urllib.request, urllib.parse, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOMES = os.path.join(ROOT, "homes.json")
OUT = os.path.join(ROOT, "photos.json")

# Many angles on "a normal, well-kept house", so we get thousands of different photos.
QUERIES = [
    "house exterior", "suburban house", "family home exterior", "ranch house", "craftsman house",
    "bungalow house", "cottage house", "house with porch", "front porch house", "single family home",
    "two story house", "modern farmhouse exterior", "brick house", "white house exterior", "gray house exterior",
    "blue house exterior", "house front yard", "house with garden", "house with garage", "residential house",
    "house curb appeal", "split level house", "cape cod house", "colonial house exterior", "victorian house exterior",
    "townhouse exterior", "house in neighborhood", "house with trees", "house driveway", "pacific northwest house",
    "house in autumn", "house in spring", "house with lawn", "small house exterior", "wooden house exterior",
    "house with fence", "house facade", "home exterior daytime", "house with flowers", "starter home",
]
# Skip photos whose description suggests the wrong thing for an adult family home listing.
BAD = ["interior", "living room", "kitchen", "bedroom", "bathroom", "room", "sofa", "couch", "mansion", "luxury",
       "castle", "villa", "palace", "pool", "resort", "hotel", "abandoned", "ruin", "derelict", "fire", "burn",
       "night", "christmas lights", "halloween", "construction", "skyscraper", "apartment building", "office",
       "aerial", "drone", "model", "miniature", "toy", "drawing", "illustration", "render", "3d", "people", "person",
       "woman", "man ", "child", "dog", "cat", "beach", "snow storm", "flood", "for sale", "sign",
       "gothic", "manor", "estate", "chateau", "cathedral", "church", "haunted", "dark", "moody", "fog", "misty", "stormy", "dusk", "black and white"]
GOOD = ["house", "home", "cottage", "bungalow", "porch", "residence", "residential", "building", "facade", "exterior"]


def get(url, headers):
    req = urllib.request.Request(url, headers={"User-Agent": "jigscare-photos/1.0", **headers})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:                         # rate limit: wait and retry
                wait = 60 * (attempt + 1)
                print(f"  rate limited, waiting {wait}s"); time.sleep(wait); continue
            if e.code in (401, 403):
                sys.exit(f"The API key was refused ({e.code}). Check the key and try again.")
            print(f"  HTTP {e.code} for {url[:80]}"); return None
        except Exception as e:                        # network hiccup
            print(f"  retry after error: {e}"); time.sleep(5)
    return None


def ok_text(text):
    t = (text or "").lower()
    return not any(b in t for b in BAD) and (not t or any(g in t for g in GOOD))


def from_pexels(key, need):
    found = {}
    for q in QUERIES:
        page = 1
        while page <= 40 and len(found) < need:
            url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
                {"query": q, "per_page": 80, "page": page, "orientation": "landscape"})
            d = get(url, {"Authorization": key})
            if not d or not d.get("photos"): break
            for p in d["photos"]:
                if not ok_text(p.get("alt")): continue
                if p.get("width", 0) < 1200: continue
                found[f"p{p['id']}"] = ["p", str(p["id"]), p.get("photographer", "")[:40]]
            print(f"  Pexels '{q}' page {page}: {len(found)} photos so far")
            if not d.get("next_page"): break
            page += 1
            time.sleep(0.4)
        if len(found) >= need: break
    return found


def from_unsplash(key, need):
    found = {}
    for q in QUERIES:
        page = 1
        while page <= 30 and len(found) < need:
            url = "https://api.unsplash.com/search/photos?" + urllib.parse.urlencode(
                {"query": q, "per_page": 30, "page": page, "orientation": "landscape", "content_filter": "high"})
            d = get(url, {"Authorization": f"Client-ID {key}", "Accept-Version": "v1"})
            if not d or not d.get("results"): break
            for p in d["results"]:
                if p.get("premium") or p.get("plus"): continue
                if not ok_text(p.get("alt_description") or p.get("description")): continue
                raw = (p.get("urls") or {}).get("raw", "")
                path = urllib.parse.urlparse(raw).path.lstrip("/")     # e.g. photo-1568605114967-8130f3a36994
                if not path.startswith("photo-"): continue
                user = p.get("user") or {}
                found["u" + path] = ["u", path, (user.get("name") or "")[:40], user.get("username", "")]
            print(f"  Unsplash '{q}' page {page}: {len(found)} photos so far")
            if page >= (d.get("total_pages") or 0): break
            page += 1
            time.sleep(1.0)
        if len(found) >= need: break
    return found


def stable_order(lics):
    # The same home always lands in the same place, so reruns don't reshuffle photos.
    return sorted(lics, key=lambda l: hashlib.sha1(l.encode()).hexdigest())


def main():
    homes = json.load(open(HOMES, encoding="utf-8"))
    rows = homes["rows"]
    afh = [r[0] for r in rows if r[1] == "A"]
    alf = [r[0] for r in rows if r[1] != "A"]
    need = len(afh) + len(alf)

    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"photos": [], "map": {}}
    pool = {(p[0] + p[1]): p for p in old["photos"]}            # keep every photo we already had

    pk, uk = os.environ.get("PEXELS_API_KEY"), os.environ.get("UNSPLASH_ACCESS_KEY")
    if not pk and not uk:
        sys.exit("Add PEXELS_API_KEY (and optionally UNSPLASH_ACCESS_KEY) first. See the top of this file.")
    want = need + 600                                            # extra, since some get filtered
    if pk and len(pool) < want:
        print("Collecting from Pexels…"); pool.update(from_pexels(pk, want - len(pool)))
    if uk and len(pool) < want:
        print("Collecting from Unsplash…"); pool.update(from_unsplash(uk, want - len(pool)))

    photos = list(pool.values())
    index = {p[0] + p[1]: i for i, p in enumerate(photos)}
    used, mapping, all_lics = set(), {}, set(afh + alf)
    # 1) homes keep last run's photo if it still exists
    for lic, i in old.get("map", {}).items():
        p = old["photos"][i] if i < len(old["photos"]) else None
        if p and (p[0] + p[1]) in index and lic in all_lics and index[p[0] + p[1]] not in used:
            mapping[lic] = index[p[0] + p[1]]; used.add(mapping[lic])
    # 2) new homes get an unused photo; adult family homes first
    free = [i for i in range(len(photos)) if i not in used]
    for lic in stable_order([l for l in afh if l not in mapping]) + stable_order([l for l in alf if l not in mapping]):
        if free:
            mapping[lic] = free.pop(0)
        else:                                                    # ran out: reuse, spread far apart
            mapping[lic] = int(hashlib.sha1(lic.encode()).hexdigest(), 16) % len(photos)

    unique_afh = len({mapping[l] for l in afh if l in mapping})
    json.dump({"asOf": time.strftime("%Y-%m-%d"), "photos": photos, "map": mapping},
              open(OUT, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"\nDone. {len(photos)} photos; {unique_afh} of {len(afh)} adult family homes have their own photo.")
    if unique_afh < len(afh):
        print("Not every home has a unique photo yet. Run again later (rate limits reset hourly), or add an Unsplash key.")
    print(f"Saved {OUT}. Upload it to GitHub next to homes.json.")


if __name__ == "__main__":
    main()
