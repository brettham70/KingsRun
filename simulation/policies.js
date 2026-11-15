// Court policies and the Decree-use policy. These choose; the production code (via harness.js) executes and validates.
// Item groups are derived ONLY from the real item text in index.html (REGALIA / DECREES). Information-only items
// (Spyglass, Eavesdropper, Scout) change what a human can see, but the page's AI never uses that information, so
// they have no mechanical effect on the simulated player and are left out of every policy list (Random can still buy them).
const GROUPS = {
  economic:   { regalia: ['patron', 'herald', 'tax', 'interest', 'mint', 'earlybird'],              decrees: [] },
  aggressive: { regalia: ['fool', 'jewels', 'commoner', 'seventh', 'twin', 'herald', 'earlybird', 'gambler'], decrees: ['redeal', 'pickpocket'] },
  defensive:  { regalia: ['secondwind', 'vault', 'lowtide', 'starlight', 'purse'],                    decrees: ['insurance', 'pardon'] },
};
const RESERVE = 5;           // listed-item policies never pay if it would leave less than this (a free pick ignores it)
const INFO_ONLY = ['spyglass', 'eaves', 'scout'];
const GROUP_NAMES = ['baseline', 'random', 'economic', 'aggressive', 'defensive'];

// Small separate PRNG so policy randomness never touches the game's stream.
function pRng(seed) { let a = (seed ^ 0x9E3779B9) >>> 0 || 1; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

// view = { gold, free, shop:[{kind,id,sold,price}], regalia:[id], decrees:[id], rerollCost, maxR, maxD, REG, DEC, rerolls, steps }
// returns one of {t:'buy',k} {t:'reroll'} {t:'sell',id} {t:'done'}
function makePolicy(group, seed, reserve = RESERVE) {
  const rnd = pRng(seed);
  const price = o => o.price;
  const full = (v, kind) => kind === 'R' ? v.regalia.length >= v.maxR : v.decrees.length >= v.maxD;
  const legalBuy = (v, o) => !o.sold && price(o) <= v.gold && !full(v, o.kind);

  if (group === 'baseline') {
    // Never buys. Only exception: the Boss bounty free pick (price 0), taken from the first offer in shop order. See report.
    return { name: group, act(v) { const k = v.shop.findIndex(o => v.free && legalBuy(v, o)); return k >= 0 ? { t: 'buy', k } : { t: 'done' }; } };
  }
  if (group === 'random') {
    return { name: group, act(v) {
      if (v.steps >= 6) return { t: 'done' };
      const acts = [{ t: 'done' }];
      v.shop.forEach((o, k) => { if (legalBuy(v, o)) acts.push({ t: 'buy', k }); });
      if (v.gold >= v.rerollCost) acts.push({ t: 'reroll' });
      if (v.shop.some(o => !o.sold && o.kind === 'R' && price(o) <= v.gold && full(v, 'R'))) v.regalia.forEach(id => acts.push({ t: 'sell', id }));
      return acts[Math.floor(rnd() * acts.length)];
    } };
  }
  const G = GROUPS[group];
  const rank = o => { const l = o.kind === 'R' ? G.regalia : G.decrees; return l.indexOf(o.id); };
  return { name: group, act(v) {
    // best listed offer we could pay for (ignoring the capacity limit for now)
    // A free pick (Boss bounty) goes to the listed offer that would cost most; otherwise the best-ranked affordable one.
    let best = -1, bestRank = 1e9, bestCost = -1;
    v.shop.forEach((o, k) => {
      if (o.sold) return; const r = rank(o); if (r < 0) return;
      const afford = price(o) <= v.gold && (v.free || v.gold - price(o) >= reserve);
      if (!afford) return;
      if (v.free) { const real = o.kind === 'R' ? v.REG(o.id).price : v.DEC(o.id).price; if (real > bestCost || (real === bestCost && r < bestRank)) { best = k; bestRank = r; bestCost = real; } }
      else if (r < bestRank) { best = k; bestRank = r; }
    });
    if (best >= 0) {
      const o = v.shop[best];
      if (!full(v, o.kind)) return { t: 'buy', k: best };
      if (o.kind === 'R') {            // Regalia slots full: sell an owned item that this policy doesn't want
        const junk = v.regalia.find(id => G.regalia.indexOf(id) < 0);
        if (junk) return { t: 'sell', id: junk };
      }
      return { t: 'done' };
    }
    // nothing wanted on offer: look again once, if it leaves a healthy reserve
    if (v.rerolls === 0 && v.gold - v.rerollCost >= 12 && !v.shop.some(o => !o.sold && rank(o) >= 0)) return { t: 'reroll' };
    return { t: 'done' };
  } };
}

// Decree use: one documented heuristic per Decree, identical for every group. Called at the start of each of the player's
// turns (draw phase) and again if a Decree moved the phase on. Uses only production checks (decreeBlock) for legality.
function useDecrees(g) {
  const G = g.G, r = G.run, me = G.players[0], used = [];
  if (G.turn !== 0 || !r.decrees.length) return used;
  const cost = () => Math.floor(g.solve(me.hand, g.rulesFor(0)).cost);
  const lastLap = G.outBy !== null && G.outBy !== 0;
  const tryUse = (id, why) => { if (r.decrees.includes(id) && !g.decreeBlock(id)) { const c = cost(); g.useDecree(id); used.push({ id, why, cost_before: c }); return true; } return false; };
  const n = me.hand.length, top = G.discard[G.discard.length - 1];
  if (lastLap) { if (cost() >= 8) tryUse('insurance', 'last lap, hand cost>=8'); if (cost() >= 6) tryUse('pardon', 'last lap, hand cost>=6'); }
  if (G.phase === 'draw') {
    if (r.turns === 0 && cost() / n >= 7) tryUse('redeal', 'first turn, avg leftover>=7/card');
    if (r.decrees.includes('pickpocket') && g.canTakePile(0) && G.discard.length >= 2 && !g.decreeBlock('pickpocket')) {
      const second = G.discard[G.discard.length - 2], now = g.solve(me.hand, g.rulesFor(0)).cost;
      if (g.bestDiscard([...me.hand, second], g.rulesFor(0)).cost < now - 1e-9) tryUse('pickpocket', 'second discard lowers cost');
    }
    if (cost() <= 6 && r.decrees.includes('fog')) tryUse('fog', 'near going out');
    tryUse('scout', 'info only (no effect on this AI)');
  }
  return used;
}
module.exports = { makePolicy, useDecrees, GROUPS, GROUP_NAMES, INFO_ONLY, RESERVE };
