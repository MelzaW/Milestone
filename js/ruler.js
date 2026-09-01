/* ============================================================
   The date ruler: one even scale from 1000 to 2025.
   Every century occupies the same width and the grain is a decade
   throughout, so a year is worth the same distance wherever you are.
   ============================================================ */

const SEGMENTS = [
  {from:1000, to:2025, frac:1.0, step:10, tickEvery:100, labelEvery:100, name:'decades'}
];
const R_W = 1000, R_PAD = 26, R_TRACK = R_W - R_PAD*2, R_Y = 78;
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
function grainFor(y){ return 10; }
function snapYear(y){ const g = grainFor(y); return Math.round(y/g)*g; }
function ordinal(n){ const s = ['th','st','nd','rd'], v = n % 100; return n + (s[(v-20)%10] || s[v] || s[0]); }
function labelForYear(y){ return y + 's'; }
function grainName(y){ return 'decade'; }

/* Draws the ruler into an <svg>. `truth` is the principal build range, or null
   while the player is still guessing. */
function drawRuler(el, year, truth, lit){
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
  /* The cursor is the Elizabeth Tower, which is both a building and a clock,
     and so is the whole game in one mark. Loose rather than accurate: a shaft,
     a clock stage, a belfry and a spire. The hands are live, the long one
     sweeping once a century and the short one once a millennium, so they turn
     as you drag and read the year you are standing on. */
  const hx = yearToX(year);
  const cy = R_Y - 43, R = 5.6;
  const p = (...pts) => pts.map(([x,y],i)=>`${i?'L':'M'}${(hx+x).toFixed(1)},${(R_Y+y).toFixed(1)}`).join(' ')+' Z';

  s += `<line x1="${hx.toFixed(1)}" y1="${R_Y-14}" x2="${hx.toFixed(1)}" y2="${R_Y+14}" class="handle-line"/>`;
  s += `<path class="bb-body" d="${p([-4.8,-2],[4.8,-2],[4.5,-36],[-4.5,-36])}"/>`;      // shaft: slender
  s += `<path class="bb-body" d="${p([-7.4,-36],[7.4,-36],[7.4,-50],[-7.4,-50])}"/>`;    // clock stage
  s += `<path class="bb-body" d="${p([-8.2,-50],[8.2,-50],[8.2,-52.5],[-8.2,-52.5])}"/>`;// cornice
  s += `<path class="bb-body" d="${p([-6.4,-52.5],[6.4,-52.5],[6.4,-59],[-6.4,-59])}"/>`;// belfry
  s += `<path class="bb-body" d="${p([-6.4,-59],[6.4,-59],[0,-69])}"/>`;                 // spire
  s += `<circle cx="${hx.toFixed(1)}" cy="${(R_Y-70.5).toFixed(1)}" r="1.1" class="bb-body"/>`;
  s += `<circle cx="${hx.toFixed(1)}" cy="${cy}" r="${R}" class="bb-face${lit ? ' lit' : ''}"/>`;

  const hand = (turns, len, w) => {
    const a = turns*2*Math.PI - Math.PI/2;
    return `<line x1="${hx.toFixed(1)}" y1="${cy}" x2="${(hx+Math.cos(a)*len).toFixed(1)}"`
         + ` y2="${(cy+Math.sin(a)*len).toFixed(1)}" class="bb-hand" stroke-width="${w}"/>`;
  };
  s += hand((year % 1000)/1000, R-3.0, 1.5);   // once a millennium
  s += hand((year % 100)/100,  R-1.4, 1.0);    // once a century

  el.innerHTML = s;
  el.setAttribute('aria-valuenow', year);
  el.setAttribute('aria-valuetext', labelForYear(year));
}
