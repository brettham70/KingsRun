#!/usr/bin/env node
// Headless Kingsrun "The Run" simulation. Usage:
//   node simulation/run-sim.js --runs 1000 --out simulation-results/2026-11-16-run-001 [--seed 20261116] [--groups 5]
// Reuses the game's own code (see harness.js). Writes raw run, round and event records as CSV, plus config and manifest.
const fs = require('fs'), path = require('path'), cp = require('child_process');
const { load, PAGE } = require('./harness');
const { makePolicy, useDecrees, GROUPS, GROUP_NAMES, INFO_ONLY, RESERVE } = require('./policies');

const SIM_VERSION = '1.0.0';
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };

function seedFor(base, i) { let x = (base + Math.imul(i + 1, 0x9E3779B1)) >>> 0; x ^= x >>> 16; x = Math.imul(x, 0x85EBCA6B) >>> 0; x ^= x >>> 13; x = Math.imul(x, 0xC2B2AE35) >>> 0; x ^= x >>> 16; return (x >>> 0) || 1; }
const sum = a => a.reduce((s, x) => s + x, 0);

// ---- analysis-only helper: the page's rulesFor(0) with chosen Regalia switched off, to price what each one saved on the final hand ----
function variantRules(g, off) {
  const G = g.G, r = G.run, wr = g.wildRank(), has = k => r.regalia.includes(k) && !off.includes(k);
  const extra = []; if (has('commoner')) extra.push(3); if (has('seventh')) extra.push(7); if (has('jewels')) extra.push(13);
  const noJ = r.boss === 'usurper', EPS = g.EPS;
  const wild = c => c.s < 0 ? !noJ : (c.r === wr || extra.includes(c.r));
  return { wr, wild, bookMin: has('twin') ? (x => x >= 11 ? 2 : 3) : null, pts: c => {
    if (wild(c)) return EPS + (c.s < 0 ? 50 : 20);
    if (c.s < 0) return EPS + 50;
    let v = c.r; if (has('lowtide') && c.r <= 5) v = 0; if (has('purse') && c.r >= 11) v = 5; if (has('starlight') && c.s === 0) v = 0; return v + EPS; } };
}
const HAND_ITEMS = ['commoner', 'seventh', 'jewels', 'twin', 'lowtide', 'starlight', 'purse'];

// Turn the page's own ledger lines into named fields. Unknown labels are kept (other_credit/other_debit) and flagged.
function parseLedger(lines) {
  const f = { hand_penalty_raw: 0, pardon_saving: 0, gambler_extra: 0, insurance_saving: 0, act1_cap_saving: 0, vault_saving: 0, second_wind_gold: 0,
    tribute: 0, out_reward: 0, low_reward: 0, boss_bounty: 0, mint: 0, tax: 0, patron: 0, interest: 0, other: 0, unknown_labels: [] };
  for (const { t, v } of lines) {
    if (/^Caught with/.test(t)) f.hand_penalty_raw = -v;
    else if (t === 'Royal Pardon') f.pardon_saving = v;
    else if (/^Gambler/.test(t)) f.gambler_extra = -v;
    else if (t === 'Insurance halves it') f.insurance_saving = v;
    else if (/^Act 1/.test(t)) f.act1_cap_saving = v;
    else if (t === "Miser's Vault") f.vault_saving = v;
    else if (t === 'Second Wind saves you') f.second_wind_gold = v;
    else if (t === 'Royal tribute') f.tribute = v;
    else if (t === 'You went out first') f.out_reward = v;
    else if (t === 'Lowest score at the table') f.low_reward = v;
    else if (/^Beat /.test(t)) f.boss_bounty = v;
    else if (t === 'Royal Mint') f.mint = v;
    else if (t === 'Tax Collector') f.tax = v;
    else if (t === 'Patron') f.patron = v;
    else if (t === 'Interest') f.interest = v;
    else { f.other += v; f.unknown_labels.push(t); }
  }
  return f;
}

function runOne(g, group, runId, seed, reserve = RESERVE) {
  g.seedRng(seed);
  g.newGame({ mode: 'run', count: 2, names: [] });
  const G = g.G, R = G.run, policy = makePolicy(group, seed, reserve);
  const rounds = [], events = [], ev = (o) => events.push({ run_id: runId, ...o });
  let totalSpent = 0, totalSold = 0, totalReroll = 0, bountyFree = 0, freeUsed = 0, minAfter = 25, order = 0;
  const owned_by_round = [];

  for (;;) {
    const rd = G.round, startGold = R.gold, regStart = [...R.regalia], decStart = [...R.decrees];
    const boss = g.BOSSES[rd] ? g.BOSSES[rd].key : null;
    const uses = [];
    let guard = 0;
    while (G.phase === 'draw' || G.phase === 'discard') {
      if (++guard > 3000) throw new Error(`runaway round ${rd} in ${runId}`);
      if (G.turn === 0 && G.phase === 'draw') for (const u of useDecrees(g)) { uses.push({ ...u, turn: R.turns, hand: G.players[0].hand.length }); ev({ round: rd, type: 'decree_use', item: u.id, detail: u.why, cost_before: u.cost_before }); }
      if (G.phase === 'draw') g.aiDraw(); else g.aiDiscard();
    }
    // ---- settlement has run (production runEndRound). Read it back. ----
    const L = R.ledger, f = parseLedger(L.lines), pts = G.result.map(x => x.pts), out = G.outBy === 0;
    const sumV = sum(L.lines.map(l => l.v)), expected = L.before + sumV;
    const bust = R.over === 'bust';
    const billPaid = out ? 0 : f.hand_penalty_raw - f.pardon_saving + f.gambler_extra - f.insurance_saving - f.act1_cap_saving - f.vault_saving;
    // counterfactual hand-rule savings on the actual final hand (same cards, rule off). Only when not out.
    const me = G.players[0], hs = {};
    if (!out) {
      const base = Math.floor(g.solve(me.hand, variantRules(g, [])).cost);
      if (base !== pts[0]) throw new Error(`rules replica mismatch ${runId} r${rd}: replica ${base} vs game ${pts[0]}`);
      for (const k of HAND_ITEMS) if (regStart.includes(k)) hs[k] = Math.floor(g.solve(me.hand, variantRules(g, [k])).cost) - base;
    }
    // marginal going-out gold per item
    const turns = R.turns, h = regStart.includes('herald'), e = regStart.includes('earlybird'), gm = regStart.includes('gambler');
    const outf = (hh, ee, gg) => ((10 + (hh ? 5 : 0)) * (ee && turns <= 3 ? 2 : 1)) * (gg ? 3 : 1);
    const outAll = out ? outf(h, e, gm) : 0;
    const marg = out ? { herald: h ? outAll - outf(false, e, gm) : 0, earlybird: e ? outAll - outf(h, false, gm) : 0, gambler: gm ? outAll - outf(h, e, false) : 0 } : { herald: 0, earlybird: 0, gambler: 0 };
    const row = {
      run_id: runId, group, seed, round: rd, wild_rank: rd + 2, boss: boss || '', player_cards: rd + 2,
      treasury_start: startGold, regalia_owned: regStart.join('|'), decrees_held: decStart.join('|'),
      out_by: G.outBy === null ? '' : G.outBy, player_out: out ? 1 : 0, player_turns: turns,
      pts_player: pts[0], pts_opp1: pts[1], pts_opp2: pts[2],
      hand_penalty_raw: f.hand_penalty_raw, pardon_saving: f.pardon_saving, insurance_saving: f.insurance_saving, act1_cap_saving: f.act1_cap_saving, vault_saving: f.vault_saving, gambler_extra: f.gambler_extra,
      penalty_paid: billPaid, penalty_reduction_total: f.hand_penalty_raw - billPaid,
      cap_applied: f.act1_cap_saving > 0 ? 'act1' : f.vault_saving > 0 ? 'vault' : '',
      treasury_after_bill: startGold - billPaid, bankrupt: bust ? 1 : 0, second_wind_used: f.second_wind_gold > 0 ? 1 : 0, second_wind_gold: f.second_wind_gold,
      tribute: f.tribute, out_reward: f.out_reward, low_reward: f.low_reward, boss_bounty: f.boss_bounty,
      beat_boss: f.boss_bounty > 0 ? 1 : 0,
      inc_mint: f.mint, inc_tax: f.tax, inc_patron: f.patron, inc_interest: f.interest, other_credit: f.other,
      rewards_total: f.tribute + f.out_reward + f.low_reward + f.boss_bounty + f.mint + f.tax + f.patron + f.interest + f.other,
      herald_marginal: marg.herald, earlybird_marginal: marg.earlybird, gambler_marginal_out: marg.gambler,
      saved_commoner: hs.commoner ?? '', saved_seventh: hs.seventh ?? '', saved_jewels: hs.jewels ?? '', saved_twin: hs.twin ?? '', saved_lowtide: hs.lowtide ?? '', saved_starlight: hs.starlight ?? '', saved_purse: hs.purse ?? '',
      decrees_used: uses.map(u => u.id).join('|'),
      ledger_before: L.before, ledger_after: L.after, ledger_expected: expected, ledger_ok: Math.abs(expected - L.after) < 1e-9 && L.before === startGold ? 1 : 0,
      unknown_labels: f.unknown_labels.join('|'),
      treasury_end_settlement: L.after, survived: bust ? 0 : 1,
      court_spent: 0, court_rerolls: 0, court_sold: 0, court_bought: '', treasury_after_court: '', treasury_delta: '',
    };
    if (!bust) minAfter = Math.min(minAfter, L.after);
    rounds.push(row);
    if (bust || G.phase === 'gameEnd') break;

    // ---- The Court (production openCourt/rollCourt/buyOffer/sellRegalia; reroll replicated in harness) ----
    g.openCourt();
    const bountyBefore = R.free; if (R.free) bountyFree++;
    const logOffers = (gen) => R.shop.forEach(o => ev({ round: rd, type: 'offer', item: o.id, kind: o.kind, price: g.offerPrice(o), free: R.free ? 1 : 0, gen }));
    logOffers(0);
    let steps = 0, rerolls = 0, bought = [];
    for (;;) {
      if (++steps > 40) throw new Error('court loop ' + runId);
      const v = { gold: R.gold, free: R.free, shop: R.shop.map(o => ({ ...o, price: g.offerPrice(o) })), regalia: [...R.regalia], decrees: [...R.decrees], rerollCost: R.rerollCost, maxR: g.ECON.maxR, maxD: g.ECON.maxD, REG: g.REG, DEC: g.DEC, rerolls, steps: steps - 1 };
      const a = policy.act(v);
      if (a.t === 'done') break;
      if (a.t === 'buy') {
        const o = R.shop[a.k], price = g.offerPrice(o), g0 = R.gold, wasFree = R.free;
        g.buyOffer(a.k);
        if (!o.sold || R.gold !== g0 - price) throw new Error(`illegal buy by policy ${group} ${runId}`);
        totalSpent += price; row.court_spent += price; if (wasFree) freeUsed++;
        bought.push(o.id); ev({ round: rd, type: 'buy', item: o.id, kind: o.kind, price, free: wasFree ? 1 : 0, gold_before: g0, gold_after: R.gold });
      } else if (a.t === 'reroll') {
        const c = R.rerollCost, g0 = R.gold;
        if (!g.reroll()) throw new Error('illegal reroll ' + runId);
        rerolls++; totalReroll += c; row.court_rerolls += c; ev({ round: rd, type: 'reroll', price: c, gold_before: g0, gold_after: R.gold }); logOffers(rerolls);
      } else if (a.t === 'sell') {
        const g0 = R.gold; g.sellRegalia(a.id);
        if (R.gold <= g0) throw new Error('illegal sell ' + runId);
        totalSold += R.gold - g0; row.court_sold += R.gold - g0; ev({ round: rd, type: 'sell', item: a.id, price: R.gold - g0, gold_before: g0, gold_after: R.gold });
      }
    }
    row.court_bought = bought.join('|'); row.treasury_after_court = R.gold; row.treasury_delta = R.gold - startGold; minAfter = Math.min(minAfter, R.gold);
    row.bounty_free_pick_available = bountyBefore ? 1 : 0;
    owned_by_round.push(R.regalia.join('|'));
    g.nextRound();
  }
  const last = rounds[rounds.length - 1], bust = R.over === 'bust';
  const run = {
    run_id: runId, group, seed, outcome: bust ? 'bankrupt' : 'completed', rounds_reached: G.round, bust_round: bust ? G.round : '',
    final_treasury: bust ? 0 : R.gold, shortfall_at_bust: bust ? R.gold : '', min_treasury: minAfter,
    regalia_final: R.regalia.join('|'), decrees_final: R.decrees.join('|'), bosses_beaten: R.bossesBeaten,
    gold_spent_purchases: totalSpent, gold_spent_rerolls: totalReroll, gold_from_sales: totalSold, free_picks_available: bountyFree, free_picks_used: freeUsed,
    items_bought: events.filter(e => e.type === 'buy').length, regalia_bought: events.filter(e => e.type === 'buy' && e.kind === 'R').length, decrees_bought: events.filter(e => e.type === 'buy' && e.kind === 'D').length,
    gold_generated: sum(rounds.map(r => r.rewards_total)), penalties_paid: sum(rounds.map(r => r.penalty_paid)),
    ledger_ok: rounds.every(r => r.ledger_ok) ? 1 : 0,
  };
  return { run, rounds, events };
}

function csv(rows, cols) {
  cols = cols || Object.keys(rows[0] || {});
  const q = v => { if (v === undefined || v === null || v === '') return ''; const s = String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  return cols.join(',') + '\n' + rows.map(r => cols.map(c => q(r[c])).join(',')).join('\n') + '\n';
}

function main() {
  const N = +arg('runs', 1000), outDir = arg('out', path.join('simulation-results', new Date().toISOString().slice(0, 10) + '-run-001')), base = +arg('seed', 20261116), reserve = +arg('reserve', RESERVE);
  fs.mkdirSync(outDir, { recursive: true });
  const g = load(), t0 = Date.now();
  const runs = [], rounds = [], events = [];
  const stamp = cp.spawnSync('git', ['rev-parse', 'HEAD'], { cwd: path.dirname(PAGE) }).stdout?.toString().trim();
  const dirty = (cp.spawnSync('git', ['status', '--porcelain', '--', 'index.html', 'sw.js'], { cwd: path.dirname(PAGE) }).stdout?.toString().trim() || '') !== '';
  for (let i = 0; i < N; i++) {
    const group = GROUP_NAMES[i % GROUP_NAMES.length], id = 'R' + String(i + 1).padStart(4, '0'), seed = seedFor(base, i);
    const r = runOne(g, group, id, seed, reserve);
    r.run.run_index = i + 1; runs.push(r.run); rounds.push(...r.rounds); events.push(...r.events);
    if ((i + 1) % 100 === 0) process.stderr.write(`  ${i + 1}/${N} runs (${((Date.now() - t0) / 1000).toFixed(0)}s)\n`);
  }
  const files = { run_results: 'run_results.csv', round_results: 'round_results.csv', event_log: 'event_log.csv' };
  fs.writeFileSync(path.join(outDir, files.run_results), csv(runs));
  fs.writeFileSync(path.join(outDir, files.round_results), csv(rounds));
  const evCols = ['run_id', 'round', 'type', 'item', 'kind', 'price', 'free', 'gen', 'gold_before', 'gold_after', 'cost_before', 'detail'];
  fs.writeFileSync(path.join(outDir, files.event_log), csv(events, evCols));
  const config = {
    sim_version: SIM_VERSION, base_seed: base, seed_scheme: 'seed_i = avalanche_hash(baseSeed + (i+1)*0x9E3779B1), i = run index from 0; every run has its own seed; group = i mod 5 so every group samples the whole seed range',
    runs: N, groups: GROUP_NAMES, group_assignment: 'run index i (0-based) -> GROUP_NAMES[i % 5]', runs_per_group: N / GROUP_NAMES.length,
    card_play_ai: "the page's own aiDraw/aiDiscard (opponent AI) applied to seat 0 with no 'skill' set, i.e. always the best play (same as Hard). Opponents use the Run's own tiers.",
    opponent_tiers: { 'rounds 1-3': g.TIERS(1), 'rounds 4-7': g.TIERS(4), 'rounds 8-11': g.TIERS(8), boss: 'skill 1' },
    court_policy_groups: GROUPS, reserve_gold_after_listed_purchase: reserve, info_only_items_excluded: INFO_ONLY,
    policy_notes: {
      baseline: 'Never buys. Takes the Boss-bounty free pick (price 0) from the first offer in shop order, because the spec says to retain free rewards.',
      random: 'Uniform choice among legal actions {buy any affordable offer, reroll, done}; if Regalia slots are full and a Regalia offer is affordable, selling any owned Regalia is also a legal action. Max 6 actions per Court. No reserve.',
      listed: 'economic/aggressive/defensive: buy the best-ranked affordable listed offer (ranking = list order; a free Boss-bounty pick goes to the listed offer with the highest list price), keep >= 5 gold after paying unless free; sell an unlisted Regalia if slots are full; reroll once if nothing listed is on offer and 12+ gold would remain.',
      decrees: 'insurance: last lap & hand cost>=8; pardon: last lap & cost>=6; redeal: first turn & avg leftover>=7/card; pickpocket: if the 2nd discard lowers best cost; fog: when cost<=6; scout: whenever possible (no effect on this AI).' },
    economy: g.ECON, regalia: g.REGALIA, decrees: g.DECREES, bosses: { 4: g.BOSSES[4], 8: g.BOSSES[8], 11: g.BOSSES[11] },
  };
  fs.writeFileSync(path.join(outDir, 'simulation_config.json'), JSON.stringify(config, null, 1));
  const manifest = { sim_version: SIM_VERSION, git_commit: stamp, game_files_uncommitted_changes: dirty, executed_at: new Date().toISOString(), node: process.version, seconds: (Date.now() - t0) / 1000,
    status: 'simulation complete; analysis pending', runs_started: N, runs_recorded: runs.length, rounds_recorded: rounds.length, events_recorded: events.length, outputs: files };
  fs.writeFileSync(path.join(outDir, 'simulation_manifest.json'), JSON.stringify(manifest, null, 1));
  console.log(`${N} runs, ${rounds.length} rounds, ${events.length} events in ${manifest.seconds.toFixed(1)}s -> ${outDir}`);
}
if (require.main === module) main();
module.exports = { runOne, seedFor, csv };
