/* ============================================================
   Scoring. Fifty for the date, fifty for the place, so a round is
   out of a hundred and the day's score is the average of five.
   ============================================================ */

const DEG = Math.PI/180;

/* Great circle distance in kilometres. */
function haversine(a, b){
  const R = 6371, dLat = (b[0]-a[0])*DEG, dLon = (b[1]-a[1])*DEG;
  const h = Math.sin(dLat/2)**2
          + Math.cos(a[0]*DEG)*Math.cos(b[0]*DEG)*Math.sin(dLon/2)**2;
  return 2*R*Math.asin(Math.sqrt(h));
}

/* Buildings take years to build, so the answer is a span. Anywhere inside the
   principal build range scores full marks; outside, the falloff is measured
   from the nearer end of the range rather than from a notional midpoint.
   The tolerance is wider before 1300, where the ruler only asks for a century. */
function dateScore(guess, range){
  const [from, to] = range;
  const err = guess < from ? from - guess : (guess > to ? guess - to : 0);
  const sigma = from < 1300 ? 110 : 28;
  return {pts: Math.round(50*Math.exp(-(err*err)/(2*sigma*sigma))), err, from, to};
}

/* Place scoring is a hand-drawn curve rather than a formula, because what a
   near miss is worth is a judgement about the game and not something an
   exponential happens to get right. Full marks anywhere inside the grace
   radius; between the control points below the score interpolates linearly.
   Buildings have footprints and streets have width, so nobody should lose
   marks for landing on the wrong side of the churchyard. */
const PLACE_CURVE = [
  [0.5,   50],   /* the grace radius: anywhere inside it is full marks */
  [5,     49],
  [10,    45],
  [15,    40],
  [25,    35],
  [50,    25],
  [100,   15],
  [200,    8],
  [500,    2],
  [1500,   0],   /* further than the length of the country */
];
const GRACE_KM = PLACE_CURVE[0][0];

function placeScore(guess, truth){
  const d = haversine(guess, truth);
  let pts = 0;
  if (d <= GRACE_KM) {
    pts = PLACE_CURVE[0][1];
  } else {
    for (let i = 1; i < PLACE_CURVE.length; i++){
      const [d0, p0] = PLACE_CURVE[i-1], [d1, p1] = PLACE_CURVE[i];
      if (d <= d1){ pts = p0 + (p1 - p0)*(d - d0)/(d1 - d0); break; }
    }
  }
  return {pts: Math.round(pts), km: d, grace: d <= GRACE_KM};
}

function prettyDistance(km){
  if (km < 0.05) return 'on the building';
  if (km < 1) return Math.round(km*1000) + ' m out';
  if (km < 10) return km.toFixed(1) + ' km out';
  return Math.round(km) + ' km out';
}

if (typeof module !== 'undefined') module.exports = {haversine, dateScore, placeScore, prettyDistance, GRACE_KM};
