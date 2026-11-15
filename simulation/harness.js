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

function load(opts = {}) {
  // Sim-only rule variants (applied to the in-memory copy of the page code; index.html is never modified).
  let src = SRC;
  if (opts.gambler) {
    const { out, pen } = opts.gambler;
    const a = "if(runHas('gambler'))g*=3;", b = 'Math.ceil(bill*1.5)';
    if (src.split(a).length !== 2 || src.split(b).length !== 2) throw new Error('gambler patch targets not found exactly once');
    src = src.replace(a, `if(runHas('gambler'))g=Math.floor(g*${out});`).replace(b, `Math.ceil(bill*${pen})`);
  }
  if (opts.usurperSym) {      // Usurper's dead Jokers apply to every seat, not only the player
    const a = "const noJ=me&&G.run.boss==='usurper';";
    if (src.split(a).length !== 2) throw new Error('usurper patch target not found exactly once');
    src = src.replace(a, "const noJ=G.run.boss==='usurper';");
  }
  const store = {};
  const localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
  const body = `"use strict";\n${src}\n
  const BOSS0={...BOSSES};
  return {
    get G(){return G;}, set sel(v){sel=v;},
    newGame, startRound, aiDraw, aiDiscard, useDecree, decreeBlock, openCourt, rollCourt, buyOffer, sellRegalia,
    offerPrice, rulesFor, wildRank, canTakePile, solve, bestDiscard, isWild, seedRng, clearRng, randFloat, randInt,
    ECON, TIERS, BOSSES, REGALIA, DECREES, REG, DEC, EPS, rankLabel,
    // === duplicated from the page's click handler (index.html a==='rreroll'): the reroll is not a standalone function there ===
    reroll(){const r=G.run;if(!(G.phase==='court'&&r.gold>=r.rerollCost))return false;r.gold-=r.rerollCost;r.rerollCost++;rollCourt();return true;},
    // === duplicated from the page's click handler (a==='next'): leave the Court and deal the next round ===
    nextRound(){runMsg='';startRound();},
    // === experiment helpers (not in the page) ===
    // Re-deal from a chosen round with chosen Regalia / gold. Same RNG consumption whatever the Regalia, so seeds stay paired across conditions.
    begin(o){const r=G.run;if(o.gold!=null)r.gold=o.gold;r.regalia=[...(o.forced||[])];G.round=(o.startRound||1)-1;G.dealer=(N()-2+N())%N();startRound();},
    setBosses(on){if(on){for(const k in BOSS0)BOSSES[k]=BOSS0[k];}else{for(const k in BOSS0)delete BOSSES[k];}},
    // Draw from the deck only (a cautious player who never takes the discard); mirrors aiDraw's deck branch.
    deckDraw(){const p=cur(),c=drawDeck();p.hand.push(c);G.log=p.name+' drew from the deck.';G.phase='discard';},
    setSkill(s){G.players[0].skill=s;},
    // Deal the same round again (boss rematch experiments). Undoes the end-of-run marks a round-11 settlement sets.
    replayRound(){G.run.over=null;G.recorded=false;G.round--;startRound();},
  };`;
  return new Function('localStorage', body)(localStorage);
}
module.exports = { load, PAGE, SRC };
