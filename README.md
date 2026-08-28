# Milestone

A daily guessing game about reading buildings. You see a photograph, you say
when it was built and where it stands. Fifty marks for the date, fifty for the
place, five rounds, so the day's score is out of a hundred.

## Running it

```bash
python3 build.py      # CSVs + photos  ->  data/buildings.json
python3 serve.py      # http://localhost:8000
```

Serve it rather than opening `index.html` directly — the game fetches its data,
and browsers block that on `file://`.

Nothing to install. Pillow is optional and only used to downscale uploads:

```bash
pip3 install Pillow
```

## Adding photographs

Two ways.

**In the browser.** Open <http://localhost:8000/upload.html>, drag a picture
onto a building. It is saved into `photos/` under the right name, downscaled,
and `build.py` re-runs. Reload the game.

**In bulk.** `python3 get_photos.py` pulls one freely-licensed photograph per
building from Wikimedia Commons into `photos/`, with a `credits.csv` beside
them. Then `python3 build.py`. This needs real internet access, so run it on
your own machine rather than in a sandbox.

It asks Commons for a 1600px downscale rather than the original, which for a
cathedral can be a 50MB file. Commons rate-limits hard, so expect it to pause
partway through: a 429 is answered by waiting whatever `Retry-After` asks for
and trying again, which makes a full run take a while but get there.

Photographs are matched to buildings by filename stem, so
`photos/24_Castle_Howard.jpg` belongs to building 24. Buildings without a
photograph still load but never come up in a round, as long as at least five
have one.

Only use pictures you have the right to use. Wikimedia Commons and Geograph are
fine with a credit line; general web search results usually are not. Historic
England's *data* is open under the Open Government Licence, but its Archive
*photographs* are not — they sit under a separate licence and charging scheme.

## Adding buildings

Append a row to `data/extra_buildings.csv` and run `build.py`. The columns that
matter:

| column | what it does |
| --- | --- |
| `no`, `name` | together they make the photo filename stem |
| `date` | free text; the parser reads the spans out of it |
| `function` | what the building is for; this is the **Function** clue |
| `latitude`, `longitude` | where the pin goes, and what place is scored |
| `location` | the last segment becomes the place label |
| `description` | shown under the tell on the reveal |
| `how_to_date_it` | the tell, the most important column in the file. Leave it blank and the building gets a period note for its build date instead, labelled differently on the reveal so a general note never reads as a specific observation |

### How dates are parsed

`build.py` pulls every year span out of the `date` field in order. The **first**
one is the principal build and the one scored against; the rest are recorded as
later phases. It handles a bare year followed by later ranges, so
`1083 onward, Octagon 1322 to 1340` scores against 1083, not 1322.

Anywhere inside the range is full marks. That matters — Durham took forty years,
and nobody should lose points for not knowing which decade of it they landed in.
Outside the range the falloff is measured from the nearer end, with a much wider
tolerance before 1300 where the ruler only asks for a century.

## How it is put together

```
index.html      the game
upload.html     drag-and-drop photograph manager
styles.css      one stylesheet, light and dark
vendor/leaflet/ Leaflet 1.9.4, bundled so the map works offline
js/ruler.js     the non-linear date ruler
js/scoring.js   date and place scoring, no DOM
js/app.js       rounds, map, plate, reveal
build.py        CSVs + photos -> data/buildings.json
serve.py        dev server with a PUT /upload/<stem> endpoint
get_photos.py   bulk fetch from Wikimedia Commons
```

`js/scoring.js` has no DOM in it and exports under CommonJS, so it can be unit
tested directly.

### The ruler

Linear time wastes the slider. Half of what stands in Britain went up after
1945 and almost nothing survives from before 1600, so the ruler compresses the
early centuries and expands the modern decades: centuries before 1300, decades
to 1945, half-decades after. It snaps to whichever grain you are in.

### The map

Leaflet with OpenStreetMap tiles, zoomable to the doorstep. Place scoring is a
hand-drawn curve rather than a formula, since what a near miss is worth is a
judgement about the game and not something an exponential happens to get right.
Full marks anywhere inside 500 m, then 49 at 5 km, 45 at 10, 40 at 15, 35 at 25,
25 at 50 and 15 at 100, interpolating linearly between. Edit `PLACE_CURVE` in
`js/scoring.js` to change it. Getting inside 500 m still means zooming in, which
is what the street-level map is for.

Click to drop the pin, then drag it. Since the last ten marks are won at street
scale, you want to be able to zoom right in and nudge the pin onto the doorstep
without having to re-aim a click. **Expand** throws the map across the full
width of the page and drops the photograph below it, which is what you want once
you are working at that scale.

Leaflet itself sits in `vendor/leaflet/` rather than coming from a CDN, so the
page works with no network: controls, pin, dragging and scoring all run. The
*tiles* still come from openstreetmap.org, so offline you get a working but
blank map.

### The plate

The photograph opens on the whole building and zooms freely, with no score
penalty. The point of the game is to make people look closely at brickwork, so
charging them for it would be perverse.
