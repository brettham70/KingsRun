// Headless harness for The Run. It loads the REAL game code straight out of index.html (same technique as tests/lib.js)
// and exposes it without rendering anything. Nothing in index.html is modified.
//
// Slices taken from the page, verbatim:
//   ENGINE block        solver, deck, seeded RNG
//   state + helpers     G, wildRank, N, cur, isRun ...
//   newGame..endRound   deal, turn, round lifecycle
//   The Run block       ECON, TIERS, BOSSES, REGALIA, DECREES, rulesFor, runStartRound, runEndRound, Court, useDecree
//   recordRun           (writes to a stubbed localStorage)
//   aiDraw / aiDiscard  the page's computer-player AI
// The only code duplicated here is what lives inside click handlers in the page (reroll, start-next-round); each copy is
// marked below and has the line number of the original.
const fs = require('fs'), path = require('path');
const PAGE = process.env.KR_PAGE || path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(PAGE, 'utf8');

function slice(from, to, label) {
  const i = html.indexOf(from); if (i < 0) throw new Error('marker missing: ' + from);
  const j = html.indexOf(to, i + from.length); if (j < 0) throw new Error('end marker missing: ' + to);
  return html.slice(i, j);
}
const SRC = [
  slice('/*ENGINE-START*/', '/*ENGINE-END*/'),
  slice("const KEY='kingsrun-v1';", 'const PALETTES'),
  slice('const LEVELS=', '\nconst LEVEL_KEY'),
  slice('let G=null, sel=null', '/*SAVE-START*/'),
  slice('function newGame(cfg)', 'const REC_KEY'),
  slice('/* ---------- The Run ----------', '// First-run walkthrough'),
  slice("const RUNREC_KEY", 'function runRecordsHTML'),
  slice('// Computer players.', 'function pump()'),
].join('\n');

function load() {
  const store = {};
  const localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
  const body = `"use strict";\n${SRC}\n
  return {
    get G(){return G;}, set sel(v){sel=v;},
    newGame, startRound, aiDraw, aiDiscard, useDecree, decreeBlock, openCourt, rollCourt, buyOffer, sellRegalia,
    offerPrice, rulesFor, wildRank, canTakePile, solve, bestDiscard, isWild, seedRng, clearRng, randFloat, randInt,
    ECON, TIERS, BOSSES, REGALIA, DECREES, REG, DEC, EPS, rankLabel,
    // === duplicated from the page's click handler (index.html a==='rreroll'): the reroll is not a standalone function there ===
    reroll(){const r=G.run;if(!(G.phase==='court'&&r.gold>=r.rerollCost))return false;r.gold-=r.rerollCost;r.rerollCost++;rollCourt();return true;},
    // === duplicated from the page's click handler (a==='next'): leave the Court and deal the next round ===
    nextRound(){runMsg='';startRound();},
  };`;
  return new Function('localStorage', body)(localStorage);
}
module.exports = { load, PAGE, SRC };
