#!/usr/bin/env python3
"""
Downloads one freely-licensed photograph for each of the 50 buildings from
Wikimedia Commons, and writes a credits file.

Usage:
    python3 get_photos.py

Needs only the Python standard library. Creates ./photos/ and ./photos/credits.csv
Every image it keeps is CC0, public domain, CC BY or CC BY-SA, so all of them are
usable in a published project provided you carry the credit line from credits.csv.
"""

import csv, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "VernacularChums-photo-fetch/1.0 (educational project; contact via GitHub)"
OUT = "photos"
THUMB_W = 1600   # ask Commons to downscale; the originals run to 50MB

FREE = ("cc0", "cc-zero", "public domain", "pd-", "cc by", "cc-by")
BAD_LICENCE = ("fair use", "non-free", "nc", "nd")

# Words that usually mean an interior, a detail or the wrong thing entirely.
REJECT = ("interior", "inside", "nave", "choir", "vault", "ceiling", "stained",
          "window", "tomb", "monument", "plaque", "sign", "map", "plan",
          "drawing", "engraving", "painting", "portrait", "coat of arms",
          "detail", "capital", "gargoyle", "misericord", "organ", "pulpit",
          "font", "screen", "crypt", "staircase", "stairs", "room", "hall of",
          "garden", "grounds", "park", "statue", "memorial", "gate", "lodge",
          "diagram", "chart", "logo", "icon", "aerial view of the city",
          # townscapes: a view *from* the building is not a view *of* it
          "view of", "view from", "views from", "seen from", "viewed from",
          "looking towards", "panorama", "panoramic", "skyline", "cityscape",
          "townscape", "streetscape", "aerial", "from the air")

# search term, plus a word that must appear in the filename to count as a hit
TARGETS = [
 ("White Tower Tower of London", "white tower"),
 ("Durham Cathedral exterior", "durham"),
 ("Ely Cathedral exterior", "ely"),
 ("Castle Rising Castle Norfolk", "castle rising"),
 ("Wells Cathedral west front", ("wells", "cathedral")),
 ("Salisbury Cathedral exterior", "salisbury"),
 ("Westminster Abbey exterior", "westminster abbey"),
 ("Exeter Cathedral exterior", "exeter"),
 ("Stokesay Castle", "stokesay"),
 ("Gloucester Cathedral exterior", "gloucester"),
 ("Bodiam Castle", "bodiam"),
 ("King's College Chapel Cambridge exterior", ("king", "college")),
 ("Little Moreton Hall", "moreton"),
 ("Hampton Court Palace exterior", "hampton court"),
 ("Layer Marney Tower", "layer marney"),
 ("Burghley House", "burghley"),
 ("Hardwick Hall Derbyshire", "hardwick"),
 ("Hatfield House Hertfordshire", "hatfield"),
 ("Queen's House Greenwich", ("queen", "greenwich")),
 ("Banqueting House Whitehall", "banqueting"),
 ("St Paul's Cathedral London exterior", ("paul", "cathedral")),
 ("Royal Hospital Chelsea", "royal hospital"),
 ("Chatsworth House", "chatsworth"),
 ("Castle Howard", "castle howard"),
 ("Blenheim Palace", "blenheim"),
 ("Christ Church Spitalfields", ("christ church", "spitalfields")),
 ("Chiswick House", "chiswick"),
 ("Holkham Hall", "holkham"),
 ("Strawberry Hill House Twickenham", "strawberry hill"),
 ("Royal Crescent Bath", "royal crescent"),
 ("Somerset House London", "somerset house"),
 ("Iron Bridge Ironbridge Shropshire", ("iron", "bridge")),
 ("Royal Pavilion Brighton", ("pavilion", "brighton")),
 ("British Museum facade", "british museum"),
 ("Cumberland Terrace Regent's Park", "cumberland terrace"),
 ("Palace of Westminster exterior", ("palace", "westminster")),
 ("Red House Bexleyheath", "red house"),
 ("Crossness Pumping Station", "crossness"),
 ("St Pancras railway station exterior", "pancras"),
 ("Manchester Town Hall", "manchester town hall"),
 ("Cragside Northumberland", "cragside"),
 ("Natural History Museum London exterior", "natural history"),
 ("Tower Bridge London", "tower bridge"),
 ("Michelin House London", "michelin"),
 ("Battersea Power Station", "battersea"),
 ("De La Warr Pavilion Bexhill", ("warr", "pavilion")),
 ("Royal Festival Hall London", "festival hall"),
 ("Park Hill flats Sheffield", "park hill"),
 ("National Theatre London Lasdun", "national theatre"),
 ("Lloyd's building London", ("lloyd", "building")),
]

NAMES = [
 "01_White_Tower","02_Durham_Cathedral","03_Ely_Cathedral","04_Castle_Rising",
 "05_Wells_Cathedral","06_Salisbury_Cathedral","07_Westminster_Abbey","08_Exeter_Cathedral",
 "09_Stokesay_Castle","10_Gloucester_Cathedral","11_Bodiam_Castle","12_Kings_College_Chapel",
 "13_Little_Moreton_Hall","14_Hampton_Court","15_Layer_Marney_Tower","16_Burghley_House",
 "17_Hardwick_Hall","18_Hatfield_House","19_Queens_House","20_Banqueting_House",
 "21_St_Pauls_Cathedral","22_Royal_Hospital_Chelsea","23_Chatsworth_House","24_Castle_Howard",
 "25_Blenheim_Palace","26_Christ_Church_Spitalfields","27_Chiswick_House","28_Holkham_Hall",
 "29_Strawberry_Hill","30_Royal_Crescent_Bath","31_Somerset_House","32_The_Iron_Bridge",
 "33_Royal_Pavilion","34_British_Museum","35_Cumberland_Terrace","36_Palace_of_Westminster",
 "37_Red_House","38_Crossness","39_St_Pancras","40_Manchester_Town_Hall",
 "41_Cragside","42_Natural_History_Museum","43_Tower_Bridge","44_Michelin_House",
 "45_Battersea_Power_Station","46_De_La_Warr_Pavilion","47_Royal_Festival_Hall",
 "48_Park_Hill","49_National_Theatre","50_Lloyds_Building",
]


def fetch(url, timeout=45, tries=5):
    """One request, with backoff. Commons throttles hard (429) if you go at it
    flat out, and a 429 is not a failure, it is a request to wait."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    delay = 2.0
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == tries - 1:
                raise
            wait = float(e.headers.get("Retry-After") or 0) or delay
            print(f"   {e.code}, waiting {wait:.0f}s", flush=True)
            time.sleep(wait); delay *= 2
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
            time.sleep(delay); delay *= 2


def api(params):
    params = dict(params); params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    return json.loads(fetch(url))


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def is_free(lic):
    l = (lic or "").lower()
    if any(b in l.split() for b in ("nc", "nd")):
        return False
    if "fair use" in l or "non-free" in l:
        return False
    return any(f in l for f in FREE)


def looks_like_artwork(path):
    """True for engravings, lithographs and scanned book plates.

    Commons is full of Victorian steel engravings of exactly these buildings,
    and the filenames rarely say so. They are almost colourless and use very
    few distinct colours compared with a photograph, which is enough to tell
    them apart. Needs Pillow; without it we let everything through."""
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return False
    try:
        im = Image.open(path).convert("RGB"); im.thumbnail((260, 260))
        sat = ImageStat.Stat(im.convert("HSV")).mean[1]
        variety = len(set(im.getdata())) / float(im.width * im.height)
        return sat < 42 and variety < 0.55
    except Exception:
        return False


def badly_shaped(path):
    """The plate is 4:3. A 5:1 panorama or a very tall portrait crops down to a
       sliver of the building, which defeats the point of showing it."""
    try:
        from PIL import Image
        w, h = Image.open(path).size
        r = w / float(h)
        return r > 2.4 or r < 0.62
    except Exception:
        return False


def looks_wrong(title, must=()):
    """Reject interiors and details, matching whole words only.

    Naked substring matching was catching real buildings: "park" inside
    "Park Hill", "plan" inside "Esplanade", "sign" inside "designed", "icon"
    inside "iconic", "organ" inside "Glamorgan", "gate" inside "Gatehouse".
    A reject word that appears in the target's own name is also exempted, so
    Park Hill is not rejected for being called Park Hill."""
    t = title.lower()
    wanted = " ".join(must).lower()
    for w in REJECT:
        if w in wanted:
            continue
        if re.search(r"\b" + re.escape(w) + r"\b", t):
            return True
    return False


def pick(term, must_contain):
    """Search Commons and return every free, large, exterior-looking candidate,
       best first, so the caller can reject one and fall through to the next."""
    try:
        res = api({"action": "query", "list": "search", "srsearch": term,
                   "srnamespace": 6, "srlimit": 30})
    except Exception as e:
        print("   search failed:", e); return []
    titles = [h["title"] for h in res.get("query", {}).get("search", [])]
    must = (must_contain,) if isinstance(must_contain, str) else must_contain
    titles = [t for t in titles
              if t.lower().endswith((".jpg", ".jpeg", ".png"))
              and all(m in t.lower() for m in must)
              and not looks_wrong(t, must)]
    if not titles:
        return []
    out = []
    for chunk in [titles[i:i+20] for i in range(0, len(titles), 20)]:
        try:
            info = api({"action": "query", "titles": "|".join(chunk),
                        "prop": "imageinfo",
                        "iiurlwidth": THUMB_W,
                        "iiprop": "url|size|extmetadata"})
        except Exception:
            continue
        for page in info.get("query", {}).get("pages", {}).values():
            ii = (page.get("imageinfo") or [None])[0]
            if not ii:
                continue
            meta = ii.get("extmetadata", {})
            lic = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
            if not is_free(lic):
                continue
            w = ii.get("width", 0)
            if w < 1200:
                continue
            cand = {
                "title": page["title"],
                # thumburl is a server-side downscale; the originals run to 50MB
                "url": ii.get("thumburl") or ii["url"],
                "full_url": ii["url"],
                "page": ii.get("descriptionurl", ""),
                "author": strip_html(meta.get("Artist", {}).get("value", "")) or "Unknown",
                "licence": lic,
                "width": w, "height": ii.get("height", 0),
            }
            # prefer the widest, capped so we do not grab a 60MB panorama
            cand["_score"] = min(w, 6000)   # widest wins, capped
            out.append(cand)
    out.sort(key=lambda c: -c["_score"])
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, missing = [], []
    for i, ((term, must), stem) in enumerate(zip(TARGETS, NAMES), start=1):
        have = [e for e in (".jpg", ".jpeg", ".png")
                if os.path.exists(os.path.join(OUT, stem + e))]
        if have and "--force" not in sys.argv:
            print(f"[{i:2}/50] {stem} ... already have one, skipping", flush=True)
            continue
        print(f"[{i:2}/50] {stem} ...", flush=True)
        cands = pick(term, must)
        if not cands:
            print("   nothing suitable found"); missing.append(stem); continue
        got = None
        # Commons urls carry a ?utm_source=... query, so split the path alone —
        # otherwise the extension comes out as ".org&utm_campaign=..." and
        # build.py never matches the file to its building.
        # Try candidates in order and keep the first that is a real photograph.
        dest = None
        for cand in cands[:6]:
            path = urllib.parse.urlsplit(cand["full_url"]).path
            ext = os.path.splitext(path)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png"):
                ext = ".jpg"
            trial = os.path.join(OUT, stem + ext)
            try:
                with open(trial, "wb") as f:
                    f.write(fetch(cand["url"], timeout=120))
            except Exception as e:
                print("   download failed:", e); continue
            if looks_like_artwork(trial):
                print(f"   skipped an engraving: {os.path.basename(cand['full_url'])[:52]}")
                os.remove(trial); time.sleep(1.5); continue
            if badly_shaped(trial):
                print(f"   skipped a panorama: {os.path.basename(cand['full_url'])[:52]}")
                os.remove(trial); time.sleep(1.5); continue
            got, dest = cand, trial
            break
        if not dest:
            print("   nothing suitable found"); missing.append(stem); continue
        size = os.path.getsize(dest) // 1024
        print(f"   {os.path.basename(dest)}  {got['width']}x{got['height']}  {size} KB  {got['licence']}")
        rows.append({
            "file": os.path.basename(dest),
            "building": stem[3:].replace("_", " "),
            "photographer": got["author"],
            "licence": got["licence"],
            "commons_page": got["page"],
            "direct_url": got["full_url"],
            "width": got["width"], "height": got["height"],
        })
        time.sleep(1.5)

    # Merge into any existing credits rather than replacing them. A gap-filling
    # run only produces rows for what it fetched, and these are CC BY and
    # CC BY-SA images, so dropping the other credit lines breaks the licence.
    cols = ["file","building","photographer","licence","commons_page","direct_url","width","height"]
    path = os.path.join(OUT, "credits.csv")
    merged = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("file"):
                    merged[r["file"]] = r
    for r in rows:
        merged[r["file"]] = r
    # keep only credits whose photograph is still on disk
    merged = {k: v for k, v in merged.items() if os.path.exists(os.path.join(OUT, k))}
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for k in sorted(merged):
            w.writerow({c: merged[k].get(c, "") for c in cols})

    print(f"\nDone. {len(rows)} images in ./{OUT}/, credits in {OUT}/credits.csv")
    if missing:
        print("No image found for:", ", ".join(missing))
        print("Search those by hand at https://commons.wikimedia.org")


if __name__ == "__main__":
    main()
