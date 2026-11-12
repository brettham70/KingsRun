// Shared helpers: load the game's engine and save logic straight out of index.html, so tests always run the real code.
const fs = require('fs'), path = require('path');
const PAGE = process.env.KR_PAGE || path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(PAGE, 'utf8');
const between = (a, b) => { const i = html.indexOf(a), j = html.indexOf(b); if (i < 0 || j < 0) throw new Error('marker missing: ' + a); return html.slice(i, j); };

function loadEngine() {
  const code = between('/*ENGINE-START*/', '/*ENGINE-END*/') + between('/*SAVE-START*/', '/*SAVE-END*/');
  return new Function(code + `; return {solve,bestDiscard,makeDeck,shuffle,isWild,pts,randInt,randFloat,seedRng,clearRng,
    validGame,migrateSave,SAVE_VERSION,DECK_SIZE};`)();
}

// Run-mode rules for one player, built from plain options (the page builds the same thing from Regalia).
const EPS = 1 / 1024;
function rulesFrom(wr, o = {}) {
  const extra = o.extra || [];
  const wild = c => c.s < 0 ? !o.noJoker : (c.r === wr || extra.includes(c.r));
  return {
    wr, wild, bookMin: o.faceBooks ? (r => r >= 11 ? 2 : 3) : null,
    pts: c => {
      if (wild(c)) return EPS + (c.s < 0 ? 50 : 20);
      if (c.s < 0) return EPS + 50;
      let v = c.r;
      if (o.low && c.r <= 5) v = 0;
      if (o.heavy && c.r >= 11) v = 5;
      if (o.star && c.s === 0) v = 0;
      return v + EPS;
    }
  };
}

// Independent reference solver: tries every way of splitting the hand into groups. Slow, so only for small hands.
// `R` is a rules object, or a plain wild rank (standard rules).
function brute(hand, R) {
  if (typeof R === 'number') R = rulesFrom(R, {}), R.pts = c => c.s < 0 ? 50 : c.r === R.wr ? 20 : c.r;
  const BM = r => R.bookMin ? R.bookMin(r) : 3;
  const valid = blk => {
    const N = blk.filter(c => !R.wild(c));
    if (N.some(c => c.s < 0)) return false;
    if (!N.length) return blk.length >= 3;
    if (N.every(c => c.r === N[0].r) && blk.length >= BM(N[0].r)) return true;
    if (blk.length < 3 || blk.length > 11) return false;
    if (!N.every(c => c.s === N[0].s)) return false;
    const rs = N.map(c => c.r); if (new Set(rs).size !== rs.length) return false;
    return Math.max(...rs) - Math.min(...rs) + 1 <= blk.length;
  };
  let best = Infinity; const blocks = [];
  (function rec(i) {
    if (i === hand.length) {
      let cost = 0; for (const b of blocks) if (!valid(b)) cost += b.reduce((s, c) => s + R.pts(c), 0);
      best = Math.min(best, cost); return;
    }
    for (const b of blocks) { b.push(hand[i]); rec(i + 1); b.pop(); }
    blocks.push([hand[i]]); rec(i + 1); blocks.pop();
  })(0);
  return best;
}
module.exports = { loadEngine, rulesFrom, brute, html, PAGE, EPS };
