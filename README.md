# JIGS CARE Directory

Warm design (cream, deep teal, soft coral, sage, gold · Playfair Display + Inter).

Washington's licensed adult family homes and assisted living communities, from DSHS licensing data.
Live site: jigscare.com · Contact: hello@jigscare.com

## What's here

| Path | What it is |
| --- | --- |
| `index.html` | The whole site: search (with budget, open beds and services filters), home pages, claim flow, owner dashboard, occupancy & inquiries, job posting, inspection readiness, caregiver profile and job search, privacy, JIGS Quality, providers page, background check tracker |
| `homes.json` | 6,854 licensed homes (6,296 adult family homes + 558 assisted living), DSHS data as of 2026-11-21 |
| `logo-mark.svg`, `logo-mark-white.svg` | Heart-house logo mark for light and dark backgrounds |
| `scripts/build_data.py` | Rebuilds `homes.json` from a new DSHS export |
| `netlify.toml` | Hosting settings for Netlify (no build step) |
| `react-hero/` | Earlier dark React hero. **Not used by the live site**; superseded by the warm design |

## Publish on Netlify

1. Netlify → Add new site → Import an existing project → GitHub → pick this repository.
2. Leave the build command empty. Publish directory: `.` (already set in `netlify.toml`).
3. Deploy. Every push to `main` republishes the site automatically.
4. Domain: Netlify → Domain management → add `jigscare.com` and follow the DNS steps.

## Refresh the home data

1. Download the "Long-Term Care Residential Care" CSV from the DSHS open data portal.
2. Run: `python3 scripts/build_data.py path/to/export.csv homes.json`
3. Commit and push `homes.json`. The "as of" date updates automatically from the file.

## Still prototype

Claims, tour requests, owner tools, posted jobs, caregiver profiles, policy notes and the background check tracker work in the browser only:
nothing is saved to a server or sent yet. Next step: a database, owner accounts, text messages and email.


## Nov 2026: aligned with the JIGS CARE MVP
- Logo: exact trace of the approved logo (teal house, coral caring hand, navy "JIGS CARE"). Files in `brand/`, plus `favicon.svg`.
- Colours from the logo: navy #04324F headings, teal #007A80 buttons/links (logo teal #06A3A8 for the logo itself), coral #FA746E.
- Type: Montserrat headings, Inter text. Playfair removed.
- Search sits right under the headline, then stats, then filters (same order as the MVP).
- Each home shows a free Unsplash sample house photo, picked from its license number and labelled "Sample photo". If a photo can't load, the drawn illustration shows.
- Desktop menu matches the phone bar: Find a home · Saved · Caregiver jobs · For owners, plus "Claim your home".
- The MVP's design-system pages (Cards, Type & logo, Colours, Home hero) are NOT part of the live site.
- Featured homes strip (paid placement): scrolls right to left near the top of search, soft fade at both edges, pauses on hover, on keyboard focus, or with its Pause button. People who turn off motion get a swipeable row instead.
  - A home appears only when its owner turns on Featured placement (Owner dashboard). Until any home has, the strip shows labelled fictional examples.
  - Price shown: $49/month add-on (change it in the pricing section and owner dashboard text).

## Nov 2026: DM Sans + free listing
- Font: DM Sans throughout (600 headings, 400/500 text). Montserrat, Inter and Figtree removed.
- Pricing: listing is free for every home (claim, photos, openings, job posts, readiness, background check tracker). The only paid product is Featured placement, $49/month (placeholder price).
- Main buttons are teal; coral is kept for hearts, badges and "Claim your home".
- Caregiver jobs show in two columns on desktop. Neighbouring homes never show the same sample photo.

## A different sample house photo for every home (photos.json)
Every home gets its own real house photo from Pexels (and Unsplash if you add a key), tagged "SAMPLE PHOTO" on the right edge, with the photographer credited on the home's page. Owners replace it from the Owner dashboard ("Your home's photo"), and the tag disappears.

**Make photos.json (one time, about 30–60 minutes, all automatic):**
1. Get a free key at https://www.pexels.com/api/ (optional second key: https://unsplash.com/developers).
2. In GitHub: Settings → Secrets and variables → Actions → New repository secret → name `PEXELS_API_KEY`, paste the key. (Optional: `UNSPLASH_ACCESS_KEY`.)
3. Actions tab → "Collect house photos" → Run workflow. When it finishes it saves `photos.json`, and Netlify republishes.
4. If it says not every home has a unique photo yet, run it again an hour later. Homes keep the photo they already have.

Until photos.json exists, the site uses the 18 built-in photos (never the same photo on two cards next to each other).
Never use Zillow, Redfin, MLS or Google Street View photos of these homes: they are copyrighted or licensed.

## Nov 2026: review recommendations, implemented

### 1. Forms now send (Netlify Forms)
Tour requests, claims, job posts, job applications and reviews are sent to JIGS CARE.
- **Turn on email alerts:** Netlify → your site → Forms → Form notifications → Add notification → Email → hello@jigscare.com (one per form, or "Any form").
- Spam: each form has a hidden honeypot field. Netlify also filters spam automatically.
- If sending fails (or on a preview that isn't Netlify), the page says so and shows the home's phone number instead.
- **Your daily job:** pass each tour request and job application to the home (phone or email) within one business day, as the page promises.

### 2. Claims are confirmed by phone
A claim no longer goes live straight away. JIGS CARE calls the phone number **on the DSHS record** (it's included in each claim email), confirms the person is the licensed provider, then marks the home verified.
Until there's a database, "verified" is set by you: the Owner-verified badge shows only when `verified: true` (coming with the backend).

### 3. Search-engine pages
`scripts/build_pages.py` runs on every Netlify deploy (see netlify.toml) and builds:
`/homes/` · `/homes/<county>/` · `/homes/<county>/<home>-<license>/` (6,853 pages) · `/sitemap.xml`.
Each page has its own title, description, Google business details (schema.org) and links into the app.
After going live on jigscare.com: add the site in Google Search Console and submit `https://jigscare.com/sitemap.xml`.
If your domain is different, set an environment variable `SITE_URL` in Netlify.

### 4. Fresh openings
Open beds show "updated X days ago" and disappear after 14 days without an update. Owners see a reminder to confirm.

### 5. Caregiver jobs
Pay is required. Each job shows pay, job type, credential (HCA, NAC, nurse or training provided), shifts, days and bonus.
Filters for city, credential, type and shift. Owners can tick "Feature this job" ($19 for 30 days: placeholder price, not charged yet).

### 6. Reviews, compare, map, guide
- **Reviews:** families send reviews from each home's page. You check them, then publish by adding them to `reviews.json`:
  `[{"lic":"754405","name":"Maria","rel":"Family member of a resident","rating":5,"text":"…","date":"2026-12-01","reply":"…"}]`
  Never publish a review that names a resident's health details.
- **Compare:** Saved homes page compares up to 3 homes side by side.
- **Map:** "Map" button on search results (OpenStreetMap, free). For heavy traffic, switch to a paid map tile provider.
- **Guide:** `#guide`, "How to choose an adult family home", linked from search and the footer.

## Nov 2026: visibility pass
- **Homes on the first screen:** one search bar with a Filters drawer (county, type, budget, open beds), chips in one row, a short trust line, then results. The first home now appears within the first screen on laptop and phone (it used to take 1.8 and 2.6 screens).
- The search bar stays pinned under the header while scrolling.
- Featured homes, stats and the explanation text moved below the first results.
- **Colours:** page #F3EDE4 with white cards and stronger borders (cards used to blend in), no paper texture, darker greys (#4E4943, 8:1) at 14px+, deep teal (#036A70) for text links.
- **Cards:** city, beds, price and openings first; the long license line is now "✓ DSHS licensed" (full details on hover and on the home's page).
- **Photos:** quieter light "Sample photo" tag on the edge; a gentle brightening on photos; the dark castle photo removed; the collector now skips dark, gothic, manor or estate photos.
