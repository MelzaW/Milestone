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

# ---------------------------------------------------------------------------
# Period notes.
#
# Every building in the original set carries a tell written for it: a specific
# observation about that fabric. Bulk-added buildings cannot, so where the tell
# is blank they get one of these instead, keyed to the build date. They are
# honest general guidance on dating a British building of that period rather
# than a claim about this one, and the reveal labels them differently so the
# difference is never hidden from the player.
PERIOD_NOTES = [
 (1066, 1200, "Norman", "Round arches, walls thick enough to show their depth in every opening, "
  "small windows set high, flat pilaster buttresses that die into the wall, and cushion "
  "capitals with no carved foliage. Ornament is geometric: chevron, billet, lozenge."),
 (1200, 1300, "Early English", "Pointed arches with tall narrow lancet windows and no tracery "
  "in them at all. Deeply cut mouldings, slender detached shafts often in dark marble, and "
  "stiff leaf foliage carved as though it grew out of the capital."),
 (1300, 1350, "Decorated", "Tracery becomes curvilinear and starts to flow. Look for the ogee, "
  "the double curve, in arch heads and canopies, and for naturalistic carved foliage where "
  "you can identify the species. Ballflower ornament runs in the mouldings."),
 (1350, 1550, "Perpendicular", "Mullions run straight up into the arch head and grids of panels "
  "cover the wall. Arches flatten to four centres, windows grow very large, and the roof is "
  "often a low pitch hidden behind a battlemented parapet."),
 (1550, 1620, "Elizabethan and Jacobean", "Symmetry arrives but the detail is still native. "
  "Mullioned and transomed windows in long ranges, shaped or stepped gables, strapwork carved "
  "like cut leather, and tall chimneystacks treated as ornament."),
 (1620, 1700, "Stuart", "Classical proportion applied for the first time with real correctness: "
  "hipped roofs, dormers, modillion cornices, and sash windows appearing late in the period with "
  "thick glazing bars. Brick becomes fashionable, often with rubbed brick dressings."),
 (1700, 1765, "Early Georgian and Palladian", "Flat, regular, and calm. Sash windows in plain "
  "openings diminishing storey by storey, a string course between floors, a pedimented centre, "
  "and almost no carved ornament. Venetian windows are the giveaway detail."),
 (1765, 1830, "Late Georgian and Regency", "Glazing bars thin markedly, fanlights appear over "
  "doorways, and stucco scored to imitate ashlar spreads across whole terraces. Cast iron "
  "balconies and railings, shallow bow windows, and a low parapet hiding the roof."),
 (1830, 1875, "Early Victorian", "Sharply cut, machine-finished stone or hard red and blue brick "
  "used in bands. Steep roofs, plate tracery, and archaeologically correct Gothic detail applied "
  "to buildings that are planned symmetrically underneath. Plate glass replaces glazing bars."),
 (1875, 1901, "Late Victorian", "Red brick and moulded terracotta, gables and turrets, tall "
  "chimneys, and sash windows with a single large pane over one below. Repeated identical "
  "ornament means it was moulded rather than carved, which itself dates the technique."),
 (1901, 1918, "Edwardian", "Baroque revival at civic scale: heavy stone dressings against red "
  "brick, banded rustication, segmental pediments and domed corner turrets. Faience and glazed "
  "tile appear on commercial buildings because they wash clean of soot."),
 (1918, 1939, "Interwar", "Flat roofs, white render and horizontal window bands where the mood "
  "is modern; brick, tile hanging and leaded lights where it is not. Steel Crittall windows, "
  "and Art Deco stepping and fluting on anything public."),
 (1939, 1970, "Post-war", "Reinforced concrete left exposed, often board marked so the timber "
  "shuttering grain is printed into it. Curtain walling, repetitive bays, and flat roofs. "
  "Brick infill panels within a visible frame rather than load-bearing walls."),
 (1970, 2000, "Late twentieth century", "Brown brick and mansard-ish roofs on housing; exposed "
  "steel, glass and externalised services on commercial work. Postmodern buildings quote "
  "classical detail at the wrong scale and usually in the wrong material."),
 (2000, 2030, "Contemporary", "Large sealed glazed panels with minimal framing, flush detailing "
  "with no visible sills or lintels, and cladding in zinc, timber or render laid as flat planes. "
  "Nothing is load-bearing that looks it."),
]

def period_note(year):
    for lo, hi, name, text in PERIOD_NOTES:
        if lo <= year < hi:
            return name, text
    return "", ""


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

def _tell_fields(r, rng):
    """A written tell if the CSV has one, otherwise a period note for the build
       date. `tellkind` lets the reveal label the two differently."""
    written = (r.get("how_to_date_it") or "").strip()
    if written:
        return {"tell": written, "tellkind": "written", "period": ""}
    year = rng[0][0] if rng else 0
    name, text = period_note(year)
    return {"tell": text, "tellkind": "period", "period": name}


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
            "note": r["description"],
            **_tell_fields(r, rng),
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
