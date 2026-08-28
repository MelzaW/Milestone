#!/usr/bin/env python3
"""
Builds data/buildings.json from the CSVs in data/ and whatever is in photos/.

    python3 build.py

Every row of data/fifty_buildings.csv and data/extra_buildings.csv becomes a
puzzle. A photograph is matched to a building by filename stem, so
photos/24_Castle_Howard.jpg belongs to building 24. Credits come from
photos/credits.csv if get_photos.py wrote one.
"""
import csv, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA, PHOTOS = os.path.join(HERE, "data"), os.path.join(HERE, "photos")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")

COUNTY_FIX = {"County Durham": "Durham", "Richmond upon Thames": "London",
              "City of London": "London", "Westminster": "London"}

def slug(no, name):
    return f'{int(no):02d}_' + re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")

def place_of(loc):
    """Short label for the map pin: drop the postcode, take the last segment."""
    s = re.sub(r",?\s*[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\s*$", "", loc.strip())
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if not parts:
        return loc
    last = re.sub(r"^(near|nr)\s+", "", parts[-1], flags=re.I)
    return COUNTY_FIX.get(last, last)

def ranges_of(datestr):
    """Every span in the date field, in order. The first is the principal build
       and the one the game scores against. Handles '1083 onward, Octagon 1322
       to 1340' by taking whichever comes first, a range or a bare year."""
    pat = r"(?:c\.\s*)?\b(1\d{3}|20\d{2})\b(?:\s*(?:to|and)\s*(?:c\.\s*)?\b(1\d{3}|20\d{2})\b)?"
    out = []
    for m in re.finditer(pat, datestr):
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        if a <= b:
            out.append([a, b])
    return out

def load_credits():
    path = os.path.join(PHOTOS, "credits.csv")
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stem = os.path.splitext(row.get("file", ""))[0]
            who = re.sub(r"\s+", " ", row.get("photographer", "")).strip()
            lic = row.get("licence", "").strip()
            out[stem] = ", ".join(x for x in (who, lic) if x)
    return out

def find_photos():
    """Keyed by the leading number, so both naming schemes work: the short
       stems get_photos.py writes (01_White_Tower.jpg) and the longer ones the
       uploader uses (01_The_White_Tower_Tower_of_London.jpg)."""
    out = {}
    for p in sorted(glob.glob(os.path.join(PHOTOS, "*"))):
        if os.path.splitext(p)[1].lower() not in IMG_EXT:
            continue
        base = os.path.basename(p)
        m = re.match(r"(\d{1,3})_", base)
        if m:
            out[int(m.group(1))] = "photos/" + base
    return out

def main():
    rows = []
    for name in ("fifty_buildings.csv", "extra_buildings.csv"):
        path = os.path.join(DATA, name)
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as f:
                rows += [r for r in csv.DictReader(f) if r.get("name")]

    photos, credits = find_photos(), load_credits()
    out, undated, unphotographed = [], [], []

    for r in rows:
        rng = ranges_of(r["date"])
        if not rng:
            undated.append(r["name"]); continue
        stem = slug(r["no"], r["name"])
        photo = photos.get(int(r["no"]))
        if not photo:
            unphotographed.append(stem)
        out.append({
            "id": stem,
            "title": r["name"],
            "place": place_of(r["location"]),
            "address": r["location"],
            "lat": float(r["latitude"]), "lon": float(r["longitude"]),
            "dates": r["date"], "range": rng[0], "phases": rng[1:],
            "architect": r["architect"], "materials": r["materials"],
            "use": r.get("function", ""),
            "grade": r.get("grade", ""), "nhle": r.get("nhle_list_entry", ""),
            "note": r["description"], "tell": r["how_to_date_it"],
            "photo": photo,
            "credit": credits.get(os.path.splitext(os.path.basename(photo))[0], "") if photo else "",
        })

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "buildings.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"{len(out)} buildings, {len(out)-len(unphotographed)} with photographs")
    if undated:
        print("no date parsed:", ", ".join(undated))
    if unphotographed:
        print(f"still need a photograph ({len(unphotographed)}):")
        for s in unphotographed:
            print("   ", s)

if __name__ == "__main__":
    main()
