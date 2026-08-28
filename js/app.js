/* ============================================================
   Milestone
   ============================================================ */

const ROUNDS = 5;
const CLUES_PER_GAME = 3;   // shared across all five rounds, not per round
const UK_VIEW = {center: [54.4, -3.2], zoom: 5};

let BUILDINGS = [], POOL = [], deck = [], idx = 0, setNo = 0;
let pin = null, year = 1780, locked = false;
let cluesLeft = CLUES_PER_GAME;
const results = [];

/* ---------- map ---------- */
let map, pinMarker, truthMarker, missLine;

function pinIcon(colour, caption){
  const html = `<svg class="pin-svg" width="30" height="42" viewBox="0 0 30 42">
    <path d="M15,41 C15,41 3,24 3,15 a12,12 0 1 1 24,0 C27,24 15,41 15,41 Z"
          fill="${colour}" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>
    <circle cx="15" cy="15" r="4.5" fill="#fff"/></svg>
    <span class="pin-cap" style="color:${colour}">${caption}</span>`;
  return L.divIcon({html, className:'pin-wrap', iconSize:[30,42], iconAnchor:[15,41]});
}

function initMap(){
  map = L.map('map', {zoomControl:true, worldCopyJump:false})
        .setView(UK_VIEW.center, UK_VIEW.zoom);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  map.on('click', e=>{
    if (locked) return;
    setPin(e.latlng);
  });
}

/* Place or move the pin. Once dropped it stays draggable, so you can zoom to
   the street and nudge it onto the actual doorstep without re-clicking. */
function setPin(latlng){
  pin = [latlng.lat, latlng.lng];
  if (pinMarker){
    pinMarker.setLatLng(latlng);
  } else {
    pinMarker = L.marker(latlng, {icon: pinIcon('#1B1E20', 'You'), draggable: true,
                                  autoPan: true, keyboard: true}).addTo(map);
    pinMarker.on('drag', ()=>{ if (!locked) { pin = [pinMarker.getLatLng().lat,
                                                    pinMarker.getLatLng().lng]; pinNote(); } });
    pinMarker.on('dragend', ()=>{ if (!locked) refresh(); });
  }
  pinNote();
  refresh();
}
function pinNote(){
  if (!pin) return;
  document.getElementById('mapnote').textContent =
    `${Math.abs(pin[0]).toFixed(4)}°${pin[0]>=0?'N':'S'}  ${Math.abs(pin[1]).toFixed(4)}°${pin[1]>=0?'E':'W'}`
    + `  ·  zoom ${map.getZoom()}  ·  drag to adjust`;
}
function clearMap(){
  for (const l of [pinMarker, truthMarker, missLine]) if (l) map.removeLayer(l);
  pinMarker = truthMarker = missLine = null;
  map.setView(UK_VIEW.center, UK_VIEW.zoom);
}
document.getElementById('mapreset').addEventListener('click', ()=>
  map.setView(UK_VIEW.center, UK_VIEW.zoom));

/* Expand: the map takes the full column width and the photograph drops below
   it. Leaflet has to be told the box changed size, and it must be told after
   the CSS transition has actually applied, hence the rAF. */
document.getElementById('mapexpand').addEventListener('click', e=>{
  const stage = document.querySelector('.stage');
  const on = stage.classList.toggle('mapfull');
  e.currentTarget.textContent = on ? 'Shrink' : 'Expand';
  e.currentTarget.setAttribute('aria-pressed', String(on));
  requestAnimationFrame(()=>{
    const c = map.getCenter();
    map.invalidateSize({animate:false});
    map.setView(c, map.getZoom(), {animate:false});
  });
});

/* ---------- plate: full frame first, free zoom ---------- */
const PW = 1000, PH = 750, PK_MAX = 8;
let pk = 1, pc = {x: PW/2, y: PH/2}, pdrag = null;
const plateHost = document.getElementById('plateimg');

function plateView(){
  const w = PW/pk, h = PH/pk;
  return {x: Math.max(0, Math.min(PW-w, pc.x-w/2)),
          y: Math.max(0, Math.min(PH-h, pc.y-h/2)), w, h, k: pk};
}
function setPlateZoom(k, focus){
  const v0 = plateView();
  pk = Math.max(1, Math.min(PK_MAX, k));
  if (focus){
    const v1 = plateView();
    pc = {x: focus.x - (focus.x - (v0.x+v0.w/2))*(v1.w/v0.w),
          y: focus.y - (focus.y - (v0.y+v0.h/2))*(v1.h/v0.h)};
  }
  drawPlate();
}
function drawPlate(){
  const b = deck[idx], v = plateView();
  const old = plateHost.querySelector('svg'); if (old) old.remove();
  const body = b.photo
    ? `<image href="${b.photo}" x="0" y="0" width="${PW}" height="${PH}" preserveAspectRatio="xMidYMid slice"/>`
    : `<rect width="${PW}" height="${PH}" fill="var(--hair)"/>
       <text x="${PW/2}" y="${PH/2}" text-anchor="middle" fill="var(--lead)"
             font-family="IBM Plex Mono, monospace" font-size="22" letter-spacing="3">NO PHOTOGRAPH YET</text>`;
  plateHost.insertAdjacentHTML('beforeend',
    `<svg viewBox="${v.x.toFixed(1)} ${v.y.toFixed(1)} ${v.w.toFixed(1)} ${v.h.toFixed(1)}"
          preserveAspectRatio="xMidYMid meet">${body}</svg>`);
  plateHost.classList.toggle('zoomed', pk > 1);
  document.getElementById('platecap').textContent = pk > 1 ? 'Looking closer' : 'Full frame';
  document.getElementById('pzlab').textContent = pk.toFixed(1) + '×';
  document.getElementById('pzin').disabled = pk >= PK_MAX - 0.01;
  document.getElementById('pzout').disabled = pk <= 1.01;
}
function atPlate(cx, cy){
  const svg = plateHost.querySelector('svg');
  const r = svg.getBoundingClientRect(), v = plateView();
  return {x: v.x + (cx-r.left)/r.width*v.w, y: v.y + (cy-r.top)/r.height*v.h};
}
plateHost.addEventListener('pointerdown', e=>{
  if (pk <= 1) return;
  plateHost.setPointerCapture(e.pointerId);
  pdrag = {sx:e.clientX, sy:e.clientY, c0:{...pc}};
});
plateHost.addEventListener('pointermove', e=>{
  if (!pdrag) return;
  const svg = plateHost.querySelector('svg');
  const r = svg.getBoundingClientRect(), v = plateView();
  pc = {x: pdrag.c0.x - (e.clientX-pdrag.sx)/r.width*v.w,
        y: pdrag.c0.y - (e.clientY-pdrag.sy)/r.height*v.h};
  drawPlate();
});
plateHost.addEventListener('pointerup',    ()=>{ pdrag = null; });
plateHost.addEventListener('pointercancel',()=>{ pdrag = null; });
plateHost.addEventListener('wheel', e=>{
  e.preventDefault();
  setPlateZoom(pk*Math.exp(-e.deltaY*0.0016), atPlate(e.clientX, e.clientY));
}, {passive:false});
document.getElementById('pzin').addEventListener('click',  ()=> setPlateZoom(pk*1.8, null));
document.getElementById('pzout').addEventListener('click', ()=> setPlateZoom(pk/1.8, null));

/* ---------- ruler ---------- */
const rulerEl = document.getElementById('ruler');
function paintRuler(){
  drawRuler(rulerEl, year, locked ? deck[idx].range : null);
  document.getElementById('readout').innerHTML =
    labelForYear(year) + `<small>${grainName(year)}</small>`;
}
function setFromClientX(cx){
  const r = rulerEl.getBoundingClientRect();
  year = snapYear(xToYear((cx - r.left)/r.width*R_W));
  paintRuler(); refresh();
}
let dragging = false;
rulerEl.addEventListener('pointerdown', e=>{
  if (locked) return;
  dragging = true; rulerEl.setPointerCapture(e.pointerId); setFromClientX(e.clientX);
});
rulerEl.addEventListener('pointermove', e=>{ if (dragging && !locked) setFromClientX(e.clientX); });
rulerEl.addEventListener('pointerup', ()=>{ dragging = false; });
rulerEl.addEventListener('keydown', e=>{
  if (locked) return;
  const g = grainFor(year);
  if (e.key === 'ArrowLeft')       year = snapYear(Math.max(1000, year - g));
  else if (e.key === 'ArrowRight') year = snapYear(Math.min(2025, year + g));
  else return;
  e.preventDefault(); paintRuler(); refresh();
});

/* ---------- clues ----------
   Three for the whole five-round game, not three per round. Scarcity is the
   cost, so nothing is deducted from your score: spend all three on one
   stubborn building or eke them out, but when they are gone they are gone.
   None of them names the county or the town, so the place half of the score is
   always yours to work out. */
const clip = (t, n) => {
  t = (t || '').trim();
  if (t.length <= n) return t;
  const cut = t.slice(0, n);
  return cut.slice(0, cut.lastIndexOf(' ')) + '\u2026';
};
/* Some material and architect fields name the county, which would hand over
   the place half for four marks. Strip it. */
const redact = (t, b) => {
  if (!t || !b.place) return t;
  const bits = b.place.split(/[,\s]+/).filter(w => w.length > 3);
  for (const w of bits)
    t = t.replace(new RegExp('\\b' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + "'?s?\\b", 'gi'), '');
  return t.replace(/\s{2,}/g, ' ').replace(/\s+([,;.])/g, '$1').trim();
};

const CLUES = [
  {label: 'Fabric',
   text: b => clip(redact((b.materials || '').split(/,| with /)[0], b), 90) || 'Not recorded'},
  {label: 'Hand',
   text: b => clip(redact(b.architect, b), 110) || 'Architect unknown'},
  {label: 'Century',
   text: b => b.range && b.range[0]
        ? `Begun in the ${ordinal(Math.floor((b.range[0] - 1) / 100) + 1)} century`
        : 'Not recorded'},
];

function paintClues(){
  const host = document.getElementById('clues');
  host.innerHTML = CLUES.map((c, i) =>
    `<button class="clue" data-i="${i}">
       <span class="ct">${c.label}</span>
       <span class="cb">Reveal</span>
     </button>`).join('');
  host.querySelectorAll('.clue').forEach(btn =>
    btn.addEventListener('click', () => takeClue(+btn.dataset.i, btn)));
  noteClues();
}
function takeClue(i, btn){
  if (locked || cluesLeft <= 0 || btn.classList.contains('open')) return;
  cluesLeft--;
  btn.classList.add('open');
  btn.querySelector('.cb').textContent = CLUES[i].text(deck[idx]);
  noteClues();
}
/* Disable what cannot be used: everything once the round is locked, and the
   unopened ones once the game's three clues are spent. Opened ones stay
   readable for the rest of the round. */
function noteClues(){
  document.querySelectorAll('.clue').forEach(el => {
    el.disabled = locked || (cluesLeft <= 0 && !el.classList.contains('open'));
  });
  document.getElementById('cluecost').textContent =
    cluesLeft > 0 ? `${cluesLeft} clue${cluesLeft > 1 ? 's' : ''} left this game`
                  : 'No clues left this game';
}

/* ---------- rounds ---------- */
const seedDay = () => Math.floor(Date.parse(new Date().toDateString())/86400000);
let seen = new Set();

/* The day's hand is seeded off the date, so offset 0 is the same five for
   everyone all day. Later offsets, drawn with the New five button, deal
   buildings you have not had yet this session before repeating any, so you can
   work through the whole collection instead of drawing blind each time. */
function pickRound(offset){
  const ordered = POOL
    .map((b,i)=>({b, k:(Math.sin(seedDay() + offset*97 + i*31.7)*10000)%1}))
    .sort((x,y)=>x.k-y.k)
    .map(o=>o.b);
  const fresh = ordered.filter(b => !seen.has(b.id));
  const used  = ordered.filter(b =>  seen.has(b.id));
  const hand  = fresh.concat(used).slice(0, Math.min(ROUNDS, POOL.length));
  hand.forEach(b => seen.add(b.id));
  if (seen.size >= POOL.length) seen = new Set(hand.map(b => b.id));  // been all the way round
  return hand;
}
function refresh(){
  document.getElementById('submit').disabled = locked || !pin;
  document.getElementById('hint').textContent = locked ? ''
    : (pin ? 'Adjust either guess, then commit' : 'Drop a pin and set the date');
}
function newRound(){
  pin = null; locked = false; year = 1780;
  pk = 1; pc = {x: PW/2, y: PH/2};
  document.getElementById('reveal').classList.remove('on');
  document.getElementById('mapnote').textContent = 'Click the map to drop a pin, then drag it to fine-tune.';
  document.getElementById('roundlab').textContent = `Round ${idx+1} / ${deck.length}`;
  document.getElementById('pips').innerHTML =
    deck.map((_,i)=>`<span class="pip ${i<idx?'done':(i===idx?'now':'')}"></span>`).join('');
  clearMap(); drawPlate(); paintRuler(); paintClues(); refresh();
  window.scrollTo({top:0, behavior:'smooth'});
}

document.getElementById('submit').addEventListener('click', ()=>{
  if (!pin || locked) return;
  locked = true;
  const b = deck[idx];
  const d = dateScore(year, b.range);
  const p = placeScore(pin, [b.lat, b.lon]);
  const total = d.pts + p.pts;
  results.push({d, p, total, b});
  noteClues();

  if (pinMarker && pinMarker.dragging) pinMarker.dragging.disable();
  truthMarker = L.marker([b.lat, b.lon], {icon: pinIcon('#8A7040', b.place)}).addTo(map);
  missLine = L.polyline([pin, [b.lat, b.lon]],
    {color:'#A4442B', weight:2, dashArray:'5 6'}).addTo(map);
  map.fitBounds(L.latLngBounds([pin, [b.lat, b.lon]]).pad(0.35), {maxZoom: 16});

  pk = 1; pc = {x: PW/2, y: PH/2}; drawPlate(); paintRuler();

  document.getElementById('revtitle').textContent = `${b.title}, ${b.dates}`;
  document.getElementById('revsub').textContent =
    [b.place, b.architect, b.materials].filter(Boolean).join(' · ');
  document.getElementById('sdate').innerHTML =
    `${d.pts}<span class="den">/50</span><span class="sub">${
      d.err === 0 ? 'inside the build range' : d.err + (d.err===1?' year':' years') + ' out'}</span>`;
  document.getElementById('splace').innerHTML =
    `${p.pts}<span class="den">/50</span><span class="sub">${prettyDistance(p.km)}</span>`;
  document.getElementById('sround').innerHTML =
    `${total}<span class="den">/100</span><span class="sub">date plus place</span>`;
  document.getElementById('telltext').innerHTML = `<b>How to date it.</b> ${b.tell}`;
  document.getElementById('revnote').textContent = b.note;
  document.getElementById('revcredit').textContent = b.credit ? `Photograph: ${b.credit}` : '';
  document.getElementById('reveal').classList.add('on');
  document.getElementById('next').textContent =
    idx === deck.length-1 ? 'See today’s score' : 'Next building';
  refresh();
});

document.getElementById('next').addEventListener('click', ()=>{
  if (idx < deck.length-1){ idx++; newRound(); } else showFinal();
});

/* ---------- final ---------- */
function band(pts){ return pts >= 42 ? 3 : pts >= 30 ? 2 : pts >= 15 ? 1 : 0; }
const SQ = ['⬜','🟧','🟨','🟩'];
function showFinal(){
  const avg = Math.round(results.reduce((a,r)=>a+r.total,0)/results.length);
  document.getElementById('final').classList.add('on');
  document.getElementById('totaltxt').innerHTML = avg + '<span class="den"> / 100</span>';
  document.getElementById('sharegrid').innerHTML =
    results.map(r=>SQ[band(r.d.pts)]).join('') + '<br>' +
    results.map(r=>SQ[band(r.p.pts)]).join('');
  document.getElementById('final').scrollIntoView({behavior:'smooth', block:'center'});
}
document.getElementById('copy').addEventListener('click', async ()=>{
  const avg = Math.round(results.reduce((a,r)=>a+r.total,0)/results.length);
  const txt = `Milestone ${avg}/100\n`
    + results.map(r=>SQ[band(r.d.pts)]).join('') + '\n'
    + results.map(r=>SQ[band(r.p.pts)]).join('');
  const btn = document.getElementById('copy');
  try { await navigator.clipboard.writeText(txt); btn.textContent = 'Copied'; }
  catch { btn.textContent = 'Copy failed'; }
  setTimeout(()=>{ btn.textContent = 'Copy result'; }, 1800);
});
/* The day's five are seeded off the date, so every reload gives the same
   buildings — that is the point of a daily game, but you need a way out of it
   while testing or when you simply want to keep playing. */
function startNewSet(){
  setNo++;
  cluesLeft = CLUES_PER_GAME;
  deck = pickRound(setNo);
  idx = 0; results.length = 0;
  document.getElementById('final').classList.remove('on');
  newRound();
}
document.getElementById('again').addEventListener('click', startNewSet);
document.getElementById('reshuffle').addEventListener('click', startNewSet);

/* ---------- boot ---------- */
function fatal(msg){
  document.querySelector('.wrap').insertAdjacentHTML('afterbegin',
    `<p style="color:var(--ochre);border:1px solid var(--ochre);border-radius:2px;padding:12px">${msg}</p>`);
}
if (typeof L === 'undefined')
  fatal('Leaflet did not load. It ships in <code>vendor/leaflet/</code>, so this usually '
      + 'means the folder is being opened directly rather than served — run '
      + '<code>python3 serve.py</code>.');

fetch('data/buildings.json')
  .then(r => r.json())
  .then(data => {
    BUILDINGS = data;
    const withPhoto = BUILDINGS.filter(b => b.photo);
    POOL = withPhoto.length >= ROUNDS ? withPhoto : BUILDINGS;
    deck = pickRound(setNo);
    const credits = [...new Set(BUILDINGS.filter(b=>b.credit).map(b=>b.credit))];
    document.getElementById('attrib').textContent = credits.length
      ? 'Photographs: ' + credits.join('; ') : '';
    initMap();
    newRound();
  })
  .catch(err => {
    fatal('Could not load data/buildings.json. Run <code>python3 build.py</code> first, '
        + 'and serve the folder with <code>python3 serve.py</code> rather than opening '
        + 'the file directly.');
    console.error(err);
  });
