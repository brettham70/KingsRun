#!/usr/bin/env node
// Validation of a finished simulation directory + determinism tests. Usage: node simulation/validate.js <outDir> [expectedRuns]
const fs = require('fs'), path = require('path');
const { load } = require('./harness');
const { runOne, seedFor } = require('./run-sim');
function readCsv(f) {
  const t = fs.readFileSync(f, 'utf8').trim().split('\n'), cols = t[0].split(',');
  return t.slice(1).map(line => { const out = []; let cur = '', q = false;
    for (let i = 0; i < line.length; i++) { const ch = line[i]; if (q) { if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') q = false; else cur += ch; } else if (ch === '"') q = true; else if (ch === ',') { out.push(cur); cur = ''; } else cur += ch; }
    out.push(cur); const o = {}; cols.forEach((c, i) => o[c] = out[i]); return o; });
}
const dir = process.argv[2], expected = +(process.argv[3] || 1000);
const cfg = JSON.parse(fs.readFileSync(path.join(dir, 'simulation_config.json')));
const runs = readCsv(path.join(dir, 'run_results.csv')), rounds = readCsv(path.join(dir, 'round_results.csv')), events = readCsv(path.join(dir, 'event_log.csv'));
const g = load(); const res = [];
const check = (name, ok, detail) => { res.push({ name, ok: !!ok, detail: detail || '' }); console.log((ok ? '  PASS ' : '  FAIL ') + name + (detail ? '  — ' + detail : '')); };
const N = x => +x;
check(`exactly ${expected} runs recorded`, runs.length === expected, runs.length + ' rows');
check('every run id unique', new Set(runs.map(r => r.run_id)).size === runs.length);
check('every run has a recorded seed, and seeds are unique', runs.every(r => N(r.seed) > 0) && new Set(runs.map(r => r.seed)).size === runs.length);
const gs = {}; runs.forEach(r => gs[r.group] = (gs[r.group] || 0) + 1);
check('five groups, 200 each (sums to 1000)', Object.keys(gs).length === 5 && Object.values(gs).every(n => n === expected / 5) && Object.values(gs).reduce((a, b) => a + b) === expected, JSON.stringify(gs));
check('no run exceeds 11 rounds', runs.every(r => N(r.rounds_reached) <= 11) && rounds.every(r => N(r.round) <= 11));
const byRun = {}; rounds.forEach(r => (byRun[r.run_id] = byRun[r.run_id] || []).push(r));
check('every run has one round record per round reached', runs.every(r => byRun[r.run_id].length === N(r.rounds_reached) && byRun[r.run_id].every((x, i) => N(x.round) === i + 1)));
check('bankrupt runs stop at the bankrupt round (last record bankrupt, none after)', runs.filter(r => r.outcome === 'bankrupt').every(r => { const l = byRun[r.run_id]; return N(l[l.length - 1].bankrupt) === 1 && l.slice(0, -1).every(x => N(x.bankrupt) === 0) && N(r.bust_round) === l.length; }));
check('completed runs reached round 11 and survived it', runs.filter(r => r.outcome === 'completed').every(r => N(r.rounds_reached) === 11 && N(byRun[r.run_id][10].survived) === 1));
check('every round ledger reconciles (before + credits - debits = after)', rounds.every(r => N(r.ledger_ok) === 1), rounds.filter(r => N(r.ledger_ok) !== 1).length + ' mismatches');
check('ledger opening balance equals recorded start-of-round treasury', rounds.every(r => N(r.ledger_before) === N(r.treasury_start)));
check('no unrecognised ledger lines', rounds.every(r => !r.unknown_labels));
check('treasury never negative except the bankruptcy settlement', rounds.every(r => N(r.bankrupt) === 1 || (N(r.treasury_end_settlement) >= 0 && (r.treasury_after_court === '' || N(r.treasury_after_court) >= 0))));
check('every completed run ends with treasury >= 0', runs.filter(r => r.outcome === 'completed').every(r => N(r.final_treasury) >= 0));
check('Regalia capacity (<=5) and Decree capacity (<=3) respected', rounds.every(r => (r.regalia_owned ? r.regalia_owned.split('|').length : 0) <= 5 && (r.decrees_held ? r.decrees_held.split('|').length : 0) <= 3) && runs.every(r => (r.regalia_final ? r.regalia_final.split('|').length : 0) <= 5 && (r.decrees_final ? r.decrees_final.split('|').length : 0) <= 3));
check('bosses appear only on rounds 4 (miser), 8 (jester), 11 (usurper)', rounds.every(r => (r.boss === '') === ![4, 8, 11].includes(N(r.round)) && (r.boss === '' || r.boss === { 4: 'miser', 8: 'jester', 11: 'usurper' }[N(r.round)])));
check('Act 1 cap respected (rounds 1-3 penalty paid <= 10)', rounds.filter(r => N(r.round) <= 3).every(r => N(r.penalty_paid) <= 10));
check('Miser\'s Vault respected (penalty paid <= 25 whenever owned)', rounds.filter(r => (r.regalia_owned || '').includes('vault')).every(r => N(r.penalty_paid) <= 25));
check('boss bounty paid exactly when the player scored below the boss (and only on boss rounds)', rounds.every(r => (N(r.boss_bounty) === 12) === (r.boss !== '' && N(r.pts_player) < N(r.pts_opp1) && N(r.bankrupt) !== 1) || N(r.bankrupt) === 1));
const bountyRounds = rounds.filter(r => N(r.boss_bounty) > 0).length, freeUsed = events.filter(e => e.type === 'buy' && e.free === '1').length;
const freeByRun = {}; events.filter(e => e.type === 'buy' && e.free === '1').forEach(e => freeByRun[e.run_id] = (freeByRun[e.run_id] || 0) + 1);
check('free picks never exceed bounties earned (no double counting)', runs.every(r => (freeByRun[r.run_id] || 0) <= N(r.bosses_beaten)), `${freeUsed} free picks used / ${bountyRounds} bounties`);
check('every purchase was paid for (price 0 only when a free pick)', events.filter(e => e.type === 'buy').every(e => e.free === '1' ? N(e.price) === 0 : N(e.price) > 0 && N(e.gold_after) === N(e.gold_before) - N(e.price)));
const baseBuys = events.filter(e => e.type === 'buy' && runs.find(r => r.run_id === e.run_id).group === 'baseline');
check('baseline never paid for anything (only free bounty picks)', baseBuys.every(e => e.free === '1') && events.filter(e => e.type === 'reroll' && runs.find(r => r.run_id === e.run_id).group === 'baseline').length === 0, baseBuys.length + ' free picks taken');
check('no placeholder / NaN values in numeric fields', rounds.every(r => ['treasury_start', 'penalty_paid', 'rewards_total'].every(k => Number.isFinite(N(r[k])))));
// determinism: re-run a sample of runs from their recorded seeds and compare
const sample = [0, 1, 2, 3, 4, 17, 250, 501, 777, 999].filter(i => i < runs.length);
const base = cfg.base_seed; let same = true;
for (const i of sample) { const row = runs[i], again = runOne(g, row.group, row.run_id, N(row.seed), cfg.reserve_gold_after_listed_purchase).run;
  for (const k of ['outcome', 'rounds_reached', 'final_treasury', 'min_treasury', 'regalia_final', 'decrees_final', 'gold_generated', 'penalties_paid', 'gold_spent_purchases']) if (String(again[k]) !== String(row[k])) { same = false; console.log('   mismatch', row.run_id, k, again[k], row[k]); } }
check('same seed + group reproduces the same run (' + sample.length + ' re-runs)', same);
check('recorded seeds follow the documented scheme', runs.every((r, i) => N(r.seed) === seedFor(base, i)));
const failed = res.filter(r => !r.ok).length;
fs.writeFileSync(path.join(dir, 'validation_results.json'), JSON.stringify(res, null, 1));
console.log(failed ? `\n${failed} FAILED` : `\nall ${res.length} checks passed`);
process.exit(failed ? 1 : 0);
