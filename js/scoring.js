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

/* Buildings have footprints, streets have width, and nobody should lose marks
   for landing on the wrong side of the churchyard. So place scoring works the
   way date scoring does: full marks anywhere inside a grace radius, and beyond
   it the falloff is measured from the edge of that radius rather than from the
   building itself. Getting inside 500 m still means zooming in, which is the
   whole reason the map goes to street level. */
const GRACE_KM = 0.5;

function placeScore(guess, truth){
  const d = haversine(guess, truth);
  const miss = Math.max(0, d - GRACE_KM);
  return {pts: Math.round(50*Math.exp(-miss/45)),   /* half marks at about 31 km */
          km: d, grace: d <= GRACE_KM};
}

function prettyDistance(km){
  if (km < 0.05) return 'on the building';
  if (km < 1) return Math.round(km*1000) + ' m out';
  if (km < 10) return km.toFixed(1) + ' km out';
  return Math.round(km) + ' km out';
}

if (typeof module !== 'undefined') module.exports = {haversine, dateScore, placeScore, prettyDistance, GRACE_KM};
