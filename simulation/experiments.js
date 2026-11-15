#!/usr/bin/env node
// Phase 2: controlled balance experiments. Usage: node simulation/experiments.js <e1|e2|e3|e4|e5|all> [--runs N] [--out dir]
// Every condition inside an experiment replays the SAME seeds (paired design), so differences come from the condition, not the deal.
// Rule variants (e1) are applied to an in-memory copy of the page code; index.html is never modified.
const fs = require('fs'), path = require('path');
const { load } = require('./harness');
const { runOne, seedFor, csv, parseLedger } = require('./run-sim');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const BASE = 20261117;                       // new seed base: Phase 2 uses deals independent of Phase 1
const OUT = arg('out', path.join('simulation-results', '2026-11-16-phase2'));
fs.mkdirSync(OUT, { recursive: true });
const loaders = {}; const G_ = (v) => { const k = JSON.stringify(v); return loaders[k] || (loaders[k] = v === 'cur' ? load() : load({ gambler: v })); };
const ALL_REGALIA = ['commoner', 'seventh', 'jewels', 'fool', 'twin', 'starlight', 'lowtide', 'purse', 'vault', 'spyglass', 'eaves', 'herald', 'earlybird', 'mint', 'tax', 'interest', 'patron', 'secondwind', 'gambler'];
const RUNCOLS = ['exp', 'cond', 'i', 'seed', 'court', 'reserve', 'outcome', 'rounds_reached', 'bust_round', 'final_treasury', 'min_treasury', 'items_bought', 'gold_generated', 'penalties_paid', 'bosses_beaten', 'regalia_final'];
const RNDCOLS = ['exp', 'cond', 'i', 'round', 'boss', 'treasury_start', 'hand_penalty_raw', 'penalty_paid', 'player_out', 'player_turns', 'pts_player', 'pts_opp1', 'rewards_total', 'out_reward', 'beat_boss', 'bankrupt', 'treasury_end_settlement', 'gambler_marginal_out', 'gambler_extra', 'earlybird_marginal', 'herald_marginal'];

function runConditions(exp, conds, N) {
  const runs = [], rounds = []; const t0 = Date.now();
  for (let i = 0; i < N; i++) {
    const seed = seedFor(BASE, i);
    for (const c of conds) {
      const g = G_(c.variant || 'cur');
      const r = runOne(g, c.court, `${exp}-${c.id}-${i}`, seed, c.reserve ?? 5, c.opts || {});
      runs.push({ exp, cond: c.id, i, seed, court: c.court, reserve: c.reserve ?? 5, ...r.run });
      for (const x of r.rounds) rounds.push({ exp, cond: c.id, i, ...x });
    }
    if ((i + 1) % 200 === 0) process.stderr.write(`  ${exp} ${i + 1}/${N} (${((Date.now() - t0) / 1000).toFixed(0)}s)\n`);
  }
  fs.writeFileSync(path.join(OUT, `${exp}_runs.csv`), csv(runs, RUNCOLS));
  fs.writeFileSync(path.join(OUT, `${exp}_rounds.csv`), csv(rounds, RNDCOLS));
  return { runs: runs.length, rounds: rounds.length, seconds: (Date.now() - t0) / 1000 };
}

const EXP = {
  e1(N) {   // Gambler's Hand variants, forced onto every run at round 1; two Court contexts
    const V = { g3_15: { out: 3, pen: 1.5 }, g2_15: { out: 2, pen: 1.5 }, g25_2: { out: 2.5, pen: 2 } }, conds = [];
    for (const court of ['none', 'aggressive']) {
      conds.push({ id: `${court}|control`, court, opts: { forced: [], ban: ['gambler'] } });
      for (const [k, v] of Object.entries(V)) conds.push({ id: `${court}|${k}`, court, variant: v, opts: { forced: ['gambler'], gambler: v } });
    }
    return { conds, meta: { variants: V } };
  },
  e2(N) {   // each Regalia forced at round 1, otherwise no purchases
    const conds = [{ id: 'control', court: 'none', opts: { forced: [] } }, ...ALL_REGALIA.map(r => ({ id: r, court: 'none', opts: { forced: [r] } }))];
    return { conds, meta: {} };
  },
  e3(N) {   // Court reserve 5/10/15
    const conds = [{ id: 'baseline', court: 'baseline' }];
    for (const court of ['economic', 'aggressive', 'defensive']) for (const rs of [5, 10, 15]) conds.push({ id: `${court}|${rs}`, court, reserve: rs });
    return { conds, meta: {} };
  },
  e5(N) {   // weaker, more human-like player decision policies
    const P = { best: {}, skill80: { skill: 0.8 }, skill55: { skill: 0.55 }, skill30: { skill: 0.3 }, deckonly: { deckOnly: true }, deckonly80: { deckOnly: true, skill: 0.8 } }, conds = [];
    for (const court of ['none', 'defensive', 'aggressive', 'economic']) for (const [k, o] of Object.entries(P)) conds.push({ id: `${court}|${k}`, court, opts: { ...o } });
    return { conds, meta: { policies: P } };
  },
};

// ---- Experiment 4: single-round boss encounters with matched builds (starts at the boss round with fixed treasury) ----
const BUILDS = { none: [], wilds: ['commoner', 'seventh', 'jewels'], fool: ['fool'], wilds_fool: ['commoner', 'seventh', 'jewels', 'fool'], wilds_fool_star: ['commoner', 'seventh', 'jewels', 'fool', 'starlight'],
  freeleft: ['starlight', 'lowtide', 'purse'], defense: ['secondwind', 'vault', 'starlight'], income: ['patron', 'interest', 'tax'], twin: ['twin'] };
const BOSSR = { miser: 4, jester: 8, usurper: 11 };
function e4(N, gold = 40) {
  const g = G_('cur'), rows = []; const t0 = Date.now();
  for (let i = 0; i < N; i++) {
    const seed = seedFor(BASE + 1, i);
    for (const [boss, rn] of Object.entries(BOSSR)) for (const [bn, build] of Object.entries(BUILDS)) for (const on of [1, 0]) {
      g.seedRng(seed); g.newGame({ mode: 'run', count: 2, names: [] }); g.setBosses(!!on); g.begin({ forced: build, gold, startRound: rn });
      const G = g.G, R = G.run; let guard = 0;
      while (G.phase === 'draw' || G.phase === 'discard') { if (++guard > 3000) throw new Error('runaway'); if (G.phase === 'draw') g.aiDraw(); else g.aiDiscard(); }
      const f = parseLedger(R.ledger.lines), pts = G.result.map(x => x.pts), out = G.outBy === 0;
      const paid = out ? 0 : f.hand_penalty_raw - f.pardon_saving + f.gambler_extra - f.insurance_saving - f.act1_cap_saving - f.vault_saving;
      rows.push({ boss, round: rn, build: bn, boss_on: on, i, seed, gold_in: gold, pts_player: pts[0], pts_opp1: pts[1], beat: pts[0] < pts[1] ? 1 : 0, player_out: out ? 1 : 0, turns: R.turns, penalty_raw: f.hand_penalty_raw, penalty_paid: paid, bust: R.over === 'bust' ? 1 : 0, second_wind: f.second_wind_gold > 0 ? 1 : 0, treasury_end: R.ledger.after });
    }
    if ((i + 1) % 500 === 0) process.stderr.write(`  e4 ${i + 1}/${N} (${((Date.now() - t0) / 1000).toFixed(0)}s)\n`);
  }
  g.setBosses(true);
  fs.writeFileSync(path.join(OUT, 'e4_encounters.csv'), csv(rows));
  return { runs: rows.length, seconds: (Date.now() - t0) / 1000 };
}

const DEFAULT_N = { e1: 1000, e2: 600, e3: 1000, e4: 2000, e5: 500 };
function main() {
  const which = process.argv[2] || 'all', list = which === 'all' ? ['e1', 'e2', 'e3', 'e4', 'e5'] : [which];
  const cfgPath = path.join(OUT, `config_${which}.json`); const cfg = { base_seed_e1_e2_e3_e5: BASE, base_seed_e4: BASE + 1, experiments: {} };
  for (const e of list) {
    const N = +arg('runs', DEFAULT_N[e]);
    const res = e === 'e4' ? e4(N) : (() => { const d = EXP[e](N); const r = runConditions(e, d.conds, N); return { ...r, paired_seeds_per_condition: N, conditions: d.conds.map(c => ({ id: c.id, court: c.court, reserve: c.reserve ?? 5, opts: c.opts || {}, variant: c.variant || 'current' })), ...d.meta }; })();
    cfg.experiments[e] = { N, ...res }; console.log(e, JSON.stringify({ N, ...(res.runs ? { runs: res.runs } : {}), seconds: res.seconds }));
    fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 1));
  }
}
if (require.main === module) main();
