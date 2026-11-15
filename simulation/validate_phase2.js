#!/usr/bin/env node
// Integrity checks for Phase 2. Usage: node simulation/validate_phase2.js <dir>
const fs = require('fs'), path = require('path');
const { load } = require('./harness'); const { runOne, seedFor } = require('./run-sim');
const D = process.argv[2], BASE = 20261117;
const rd = f => { const t = fs.readFileSync(path.join(D, f), 'utf8').trim().split('\n'), c = t[0].split(','); return t.slice(1).map(l => { const v = l.split(','); const o = {}; c.forEach((k, i) => o[k] = v[i]); return o; }); };
const res = []; const check = (n, ok, d) => { res.push({ name: n, ok: !!ok, detail: d || '' }); console.log((ok ? '  PASS ' : '  FAIL ') + n + (d ? ' — ' + d : '')); };
const cfg = e => JSON.parse(fs.readFileSync(path.join(D, `config_${e}.json`))).experiments[e];
// paired structure
for (const e of ['e1', 'e2', 'e3', 'e5']) {
  const runs = rd(`${e}_runs.csv`), N = cfg(e).N, by = {}; runs.forEach(r => (by[r.cond] = by[r.cond] || []).push(+r.seed));
  const conds = Object.keys(by), ref = by[conds[0]].join();
  check(`${e}: ${conds.length} conditions x ${N} runs, identical seed list in every condition (paired)`, conds.every(c => by[c].length === N && by[c].join() === ref) && by[conds[0]].every((s, i) => s === seedFor(BASE, i)));
  check(`${e}: no run exceeds 11 rounds`, runs.every(r => +r.rounds_reached <= 11));
}
// E1 arithmetic
{
  const r = rd('e1_rounds.csv'), mult = { g3_15: [30, 1.5], g2_15: [20, 1.5], g25_2: [25, 2], control: [0, 0] };
  const none = r.filter(x => x.cond.startsWith('none|'));
  check('e1 (no-Court): going-out reward equals 10 x the variant multiplier (30 / 20 / 25) and 0 for control, in every round the player went out', none.filter(x => +x.player_out === 1).every(x => { const m = mult[x.cond.split('|')[1]][0]; return +x.out_reward === (m || 10); }));
  check('e1 (no-Court, rounds 4-11): penalty paid = ceil(raw x variant penalty multiplier)', none.filter(x => +x.round >= 4 && +x.player_out === 0 && +x.hand_penalty_raw > 0 && +x.bankrupt === 0).every(x => { const p = mult[x.cond.split('|')[1]][1] || 1; return +x.penalty_paid === Math.ceil(+x.hand_penalty_raw * p); }));
  const runs = rd('e1_runs.csv');
  check('e1: Gambler\'s Hand owned at the end in every variant run, never in control', runs.every(x => x.cond.endsWith('control') ? !x.regalia_final.includes('gambler') : x.regalia_final.includes('gambler')));
}
// E2 forced items present
{
  const runs = rd('e2_runs.csv');
  check('e2: forced Regalia owned at the end of every run (no-Court never sells; Second Wind may be used up)', runs.every(x => x.cond === 'control' ? x.regalia_final === '' : x.cond === 'secondwind' ? ['secondwind', ''].includes(x.regalia_final) : x.regalia_final === x.cond), runs.length + ' runs');
  check('e2: control runs bought nothing', runs.filter(x => x.cond === 'control').every(x => +x.items_bought === 0));
}
// E4
{
  const e = rd('e4_encounters.csv'), key = (b, bd, on) => e.filter(x => x.boss === b && x.build === bd && x.boss_on === on).map(x => `${x.i}:${x.beat}:${x.penalty_paid}`).join();
  const n = {}; e.forEach(x => { const k = `${x.boss}|${x.build}|${x.boss_on}`; n[k] = (n[k] || 0) + 1; });
  check('e4: every boss x build x on/off cell has the same encounter count', new Set(Object.values(n)).size === 1 && Object.keys(n).length === 54, Object.values(n)[0] + ' per cell');
  check('e4: boss rounds are 4 / 8 / 11', e.every(x => +x.round === { miser: 4, jester: 8, usurper: 11 }[x.boss]));
  check('e4: income-only build plays identically to no build (it cannot change card play) in all 6 boss/on-off cells', ['miser', 'jester', 'usurper'].every(b => ['0', '1'].every(on => key(b, 'income', on) === key(b, 'none', on))));
  check('e4: Court Fool changes nothing against the Usurper (code disables it) but does elsewhere', key('usurper', 'fool', '1') === key('usurper', 'none', '1') && key('usurper', 'fool', '0') !== key('usurper', 'none', '0') && key('jester', 'fool', '1') !== key('jester', 'none', '1'));
  check('e4: nobody enters with other than 40 gold', e.every(x => +x.gold_in === 40));
}
// determinism + ledger on re-run samples
{
  let ok = true, led = true, n = 0;
  const loaders = {}; const gfor = v => { const k = JSON.stringify(v); return loaders[k] || (loaders[k] = v ? load({ gambler: v }) : load()); };
  for (const e of ['e1', 'e2', 'e3', 'e5']) {
    const runs = rd(`${e}_runs.csv`), conf = cfg(e).conditions, byId = Object.fromEntries(conf.map(c => [c.id, c]));
    for (let k = 0; k < runs.length; k += Math.floor(runs.length / 60)) {
      const row = runs[k], c = byId[row.cond], v = c.variant === 'current' ? null : c.variant;
      const again = runOne(gfor(v), c.court, 'x', +row.seed, c.reserve, c.opts).run; n++;
      for (const f of ['outcome', 'rounds_reached', 'final_treasury', 'gold_generated', 'penalties_paid', 'regalia_final']) if (String(again[f]) !== String(row[f])) { ok = false; console.log('   mismatch', e, row.cond, row.i, f, again[f], row[f]); }
      if (again.ledger_ok !== 1) led = false;
    }
  }
  check(`re-running ${n} sampled runs from their seeds and conditions reproduces them exactly`, ok);
  check(`all ${n} sampled runs' round ledgers reconcile`, led);
}
fs.writeFileSync(path.join(D, 'validation_results.json'), JSON.stringify(res, null, 1));
const f = res.filter(x => !x.ok).length; console.log(f ? `\n${f} FAILED` : `\nall ${res.length} checks passed`); process.exit(f ? 1 : 0);
