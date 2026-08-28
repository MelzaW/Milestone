/* ============================================================
   The date ruler: non-linear, denser where the building stock is.
   Centuries before 1300, decades to 1945, half-decades after.
   ============================================================ */

const SEGMENTS = [
  {from:1000, to:1300, frac:0.14, step:100, tickEvery:100, labelEvery:100, name:'centuries'},
  {from:1300, to:1700, frac:0.24, step:10,  tickEvery:50,  labelEvery:100, name:'decades'},
  {from:1700, to:1900, frac:0.30, step:10,  tickEvery:25,  labelEvery:50,  name:'decades'},
  {from:1900, to:2025, frac:0.32, step:5,   tickEvery:25,  labelEvery:25,  name:'half-decades'}
];
const R_W = 1000, R_PAD = 26, R_TRACK = R_W - R_PAD*2, R_Y = 52;
(function(){
  let acc = 0;
  for (const s of SEGMENTS){ s.x0 = R_PAD + acc*R_TRACK; acc += s.frac; s.x1 = R_PAD + acc*R_TRACK; }
})();

function yearToX(y){
  y = Math.max(1000, Math.min(2025, y));
  for (const s of SEGMENTS){
    if (y <= s.to || s === SEGMENTS[SEGMENTS.length-1])
      return s.x0 + (y - s.from)/(s.to - s.from)*(s.x1 - s.x0);
  }
}
function xToYear(x){
  x = Math.max(R_PAD, Math.min(R_W - R_PAD, x));
  for (const s of SEGMENTS){
    if (x <= s.x1 || s === SEGMENTS[SEGMENTS.length-1])
      return s.from + (x - s.x0)/(s.x1 - s.x0)*(s.to - s.from);
  }
}
function grainFor(y){ return y < 1300 ? 100 : (y < 1945 ? 10 : 5); }
function snapYear(y){ const g = grainFor(y); return Math.round(y/g)*g; }
function ordinal(n){ const s = ['th','st','nd','rd'], v = n % 100; return n + (s[(v-20)%10] || s[v] || s[0]); }
function labelForYear(y){
  if (y < 1300) return ordinal(Math.floor(y/100)+1) + ' century';
  if (y < 1945) return y + 's';
  return y + '–' + (y+4);
}
function grainName(y){ return y < 1300 ? 'century' : (y < 1945 ? 'decade' : 'half-decade'); }

/* Draws the ruler into an <svg>. `truth` is the principal build range, or null
   while the player is still guessing. */
function drawRuler(el, year, truth){
  let s = `<line x1="${R_PAD}" y1="${R_Y}" x2="${R_W-R_PAD}" y2="${R_Y}" class="tick major" stroke-width="1.2"/>`;
  for (const seg of SEGMENTS){
    s += `<line x1="${seg.x0}" y1="${R_Y-16}" x2="${seg.x0}" y2="${R_Y+16}" class="tick major" stroke-width="1.2"/>`;
    for (let y = seg.from; y < seg.to; y += seg.step){
      const x = yearToX(y), major = y % seg.tickEvery === 0;
      s += `<line x1="${x.toFixed(1)}" y1="${R_Y}" x2="${x.toFixed(1)}" y2="${R_Y + (major?11:6)}"`
         + ` class="tick${major?' major':''}" stroke-width="${major?1:.7}"/>`;
      if (y % seg.labelEvery === 0)
        s += `<text class="ticklab" x="${x.toFixed(1)}" y="${R_Y+25}">${y}</text>`;
    }
    s += `<text class="seglab" x="${((seg.x0+seg.x1)/2).toFixed(1)}" y="${R_Y-32}">${seg.name}</text>`;
  }
  s += `<line x1="${R_W-R_PAD}" y1="${R_Y-16}" x2="${R_W-R_PAD}" y2="${R_Y+16}" class="tick major" stroke-width="1.2"/>`;
  s += `<text class="ticklab" x="${R_W-R_PAD}" y="${R_Y+25}">2025</text>`;

  if (truth){
    const a = yearToX(truth[0]), b = yearToX(truth[1]), gx = yearToX(year);
    s += `<rect x="${Math.min(a,b).toFixed(1)}" y="${R_Y-8}" width="${Math.max(2,Math.abs(b-a)).toFixed(1)}"`
       + ` height="16" fill="var(--accent)" opacity=".28"/>`;
    const near = year < truth[0] ? a : (year > truth[1] ? b : gx);
    s += `<line x1="${gx.toFixed(1)}" y1="${R_Y-14}" x2="${near.toFixed(1)}" y2="${R_Y-14}" class="gap-line"/>`;
    s += `<line x1="${a.toFixed(1)}" y1="${R_Y-24}" x2="${a.toFixed(1)}" y2="${R_Y+14}" class="truth-line"/>`;
    s += `<circle cx="${a.toFixed(1)}" cy="${R_Y-24}" r="4" fill="var(--accent)"/>`;
  }
  const hx = yearToX(year);
  s += `<line x1="${hx.toFixed(1)}" y1="${R_Y-14}" x2="${hx.toFixed(1)}" y2="${R_Y+14}" class="handle-line"/>`;
  s += `<path class="handle" d="M${(hx-6).toFixed(1)},${R_Y-14} L${(hx+6).toFixed(1)},${R_Y-14} L${hx.toFixed(1)},${R_Y-4} Z"/>`;
  el.innerHTML = s;
  el.setAttribute('aria-valuenow', year);
  el.setAttribute('aria-valuetext', labelForYear(year));
}
