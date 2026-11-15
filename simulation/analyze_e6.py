#!/usr/bin/env python3
"""Tougher-boss experiment: paired analysis, validation, charts, report. Usage: python3 simulation/analyze_e6.py <dir>"""
import sys, os, glob, json
import numpy as np, pandas as pd
from scipy.stats import binomtest
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
D = sys.argv[1]; os.makedirs(f'{D}/tables', exist_ok=True); os.makedirs(f'{D}/charts', exist_ok=True)
rng = np.random.default_rng(7); B = 4000
r = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f'{D}/e6*_runs.csv'))], ignore_index=True)
d = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f'{D}/e6*_rounds.csv'))], ignore_index=True)
r[['skill', 'court', 'rule']] = r.cond.str.split('|', expand=True); d[['skill', 'court', 'rule']] = d.cond.str.split('|', expand=True)
r['completed'] = (r.outcome == 'completed').astype(int); r['gated'] = (r.outcome == 'gated').astype(int)
for c in ('boss_tolls_paid', 'regalia_stolen', 'att_miser', 'att_jester', 'att_usurper'): r[c] = r[c].fillna(0)
r['ended_by'] = r.ended_by.fillna(''); r['ended_at_boss'] = r.ended_at_boss.fillna('')
r.loc[(r.rule.isin(['current', 'current_sym'])) & (r.outcome == 'bankrupt'), 'ended_by'] = 'bill'
last = d.groupby(['cond', 'i']).tail(1)[['cond', 'i', 'boss']].rename(columns={'boss': 'last_boss'})      # where every unfinished run ended (works for current rules too)
r = r.merge(last, on=['cond', 'i']); r['ended_at_boss'] = np.where(r.outcome != 'completed', r.last_boss.fillna(''), '')
N = r.groupby('cond').size().iloc[0]
RULES = ['current', 'tribute', 'steal', 'rematch0', 'rematch5', 'rematch10', 'rematch_esc', 'rematch20', 'rematch_pct25', 'finalgate', 'gate', 'current_sym', 'rematch5_sym', 'finalgate_sym']
NAME = {'current': 'Current rules', 'tribute': 'Tribute on a loss (10 / 15 / 20 gold)', 'steal': 'Boss takes your priciest Regalia', 'rematch0': 'Rematch, no toll', 'rematch5': 'Rematch, 5 gold per loss', 'rematch10': 'Rematch, 10 gold per loss',
    'rematch_esc': 'Rematch, 5 / 10 / 15 … rising', 'rematch20': 'Rematch, 20 gold per loss', 'rematch_pct25': 'Rematch, 25% of treasury per loss (min 5)', 'finalgate': 'Rematch 5 for Miser and Jester; must beat Usurper first try',
    'gate': 'Lose to any boss = run over', 'current_sym': 'Current rules, softer Usurper', 'rematch5_sym': 'Rematch 5, softer Usurper', 'finalgate_sym': 'Final-boss gate, softer Usurper'}
def boot(x): x = np.asarray(x, float); i = rng.integers(0, len(x), (B, len(x))); m = x[i].mean(1); return x.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)
def mcn(a, b): x = int((a & ~b).sum()); y = int((~a & b).sum()); return 1.0 if x + y == 0 else binomtest(x, x + y, .5).pvalue
rows = []
for (sk, ct), g in r.groupby(['skill', 'court']):
    W = g.pivot(index='i', columns='rule', values='completed')
    for rule in RULES:
        x = g[g.rule == rule]; dd = d[(d.skill == sk) & (d.court == ct) & (d.rule == rule)]
        m, lo, hi = boot(W[rule] - W['current']); p = mcn(W[rule].values > 0, W['current'].values > 0)
        at = {b: x[x[f'att_{b}'] > 0][f'att_{b}'] for b in ('miser', 'jester', 'usurper')}
        mx = x[['att_miser', 'att_jester', 'att_usurper']].max(axis=1); fin = x[x.completed == 1].final_treasury
        rows.append(dict(skill=sk, court=ct, rule=rule, name=NAME[rule], runs=len(x), completion=x.completed.mean(), diff_vs_current=m, ci_lo=lo, ci_hi=hi, p=p,
            ended_gate=x.gated.mean(), ended_bill=(x.ended_by == 'bill').mean(), ended_toll=(x.ended_by == 'toll').mean(),
            ended_at_miser=(x.ended_at_boss == 'miser').mean(), ended_at_jester=(x.ended_at_boss == 'jester').mean(), ended_at_usurper=(x.ended_at_boss == 'usurper').mean(),
            attempts_miser=at['miser'].mean(), attempts_jester=at['jester'].mean(), attempts_usurper=at['usurper'].mean(), p90_attempts_usurper=at['usurper'].quantile(.9) if len(at['usurper']) else np.nan,
            pct_runs_3plus_attempts=(mx >= 3).mean(), max_attempts=mx.max(), mean_tolls_paid=x.boss_tolls_paid.mean(), mean_regalia_stolen=x.regalia_stolen.mean(),
            rounds_played=len(dd) / len(x), median_final_treasury=fin.median() if len(fin) else np.nan, mean_round_reached=x.rounds_reached.mean()))
T = pd.DataFrame(rows); T.to_csv(f'{D}/tables/e6_summary.csv', index=False)

# ---- validation ----
V = []; ck = lambda n, ok, det='': (V.append(dict(name=n, ok=bool(ok), detail=det)), print(('  PASS ' if ok else '  FAIL ') + n + (f' — {det}' if det else '')))
seeds = r.groupby('cond').seed.apply(lambda s: tuple(s)); ck(f'{r.cond.nunique()} conditions x {N} runs, identical seed list in every condition (paired)', seeds.nunique() == 1 and (r.groupby('cond').size() == N).all())
nog = r[~r.rule.isin(['gate', 'finalgate', 'finalgate_sym'])]; ck('no run is "gated" outside the gate rules (the 40-attempt safety stop never fired)', nog.gated.sum() == 0, f'max attempts at one boss: {int(r[["att_miser","att_jester","att_usurper"]].max().max())}')
must = r[r.rule.isin(['gate', 'rematch0', 'rematch5', 'rematch10', 'rematch_esc', 'rematch20', 'rematch_pct25', 'finalgate', 'rematch5_sym', 'finalgate_sym'])]
ck('under every "must beat" rule, every completed run beat all three bosses', (must[must.completed == 1].bosses_beaten == 3).all(), f'{int(must.completed.sum())} completed runs')
tol = d.groupby(['cond', 'i']).boss_toll.sum().rename('t').reset_index().merge(r[['cond', 'i', 'boss_tolls_paid']], on=['cond', 'i']); ck('tolls recorded per round add up to the run total', (tol.t == tol.boss_tolls_paid).all())
ck('attempt numbers only on boss rounds, and rematches only under rematch rules', d[d.attempt.notna()].boss.notna().all() and (d[(d.attempt > 1)].rule.str.contains('rematch|finalgate')).all())
ck('no run exceeds round 11', (r.rounds_reached <= 11).all())
cur = r[r.rule == 'current']; ck('the "current rules" condition has no tolls, thefts or gate endings', cur.boss_tolls_paid.sum() == 0 and cur.regalia_stolen.sum() == 0 and cur.gated.sum() == 0)
ck('tribute amounts are 10 / 15 / 20 by boss', d[(d.rule == 'tribute') & d.boss_toll.notna()].groupby('boss').boss_toll.unique().apply(lambda a: list(a)).to_dict() == {'jester': [15.0], 'miser': [10.0], 'usurper': [20.0]})
json.dump(V, open(f'{D}/validation_results.json', 'w'), indent=1); print('all passed' if all(v['ok'] for v in V) else 'FAILURES')

# ---- charts ----
plt.rcParams.update({'figure.dpi': 130, 'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 9, 'axes.grid': True, 'grid.alpha': .25})
show = ['current', 'tribute', 'steal', 'rematch5', 'rematch10', 'rematch20', 'rematch_pct25', 'finalgate', 'finalgate_sym', 'gate']; lab = ['current', 'tribute', 'steal', 'rematch\n5', 'rematch\n10', 'rematch\n20', 'rematch\n25%', 'final\ngate', 'final gate\nsoft Usurper', 'hard\ngate']
fig, axs = plt.subplots(2, 1, figsize=(10, 7), sharex=True); COL = {'none': '#7f8c8d', 'defensive': '#2471a3', 'aggressive': '#8e44ad'}
for ax, sk, ttl in zip(axs, ('best', 'skill80'), ('best play', 'player who slips 20% of the time')):
    for k, ct in enumerate(('none', 'defensive', 'aggressive')):
        t = T[(T.skill == sk) & (T.court == ct)].set_index('rule').loc[show]; x = np.arange(len(show)) + (k - 1) * .27
        ax.bar(x, t.completion * 100, .27, color=COL[ct], label=f'{ct} Court')
        for xi, v in zip(x, t.completion * 100): ax.text(xi, v + 1, f'{v:.0f}', ha='center', fontsize=6.5)
    ax.set_ylim(0, 100); ax.set_ylabel('% of runs completed'); ax.set_title(ttl)
axs[0].legend(fontsize=7, ncol=3); axs[1].set_xticks(range(len(show))); axs[1].set_xticklabels(lab); fig.suptitle(f'Tougher bosses: completion by rule ({N} matched deals per bar)'); plt.tight_layout(); plt.savefig(f'{D}/charts/e6_completion.png'); plt.close()
fig, axs = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
for ax, b in zip(axs, ('miser', 'jester', 'usurper')):
    for ct in ('none', 'defensive', 'aggressive'):
        x = r[(r.skill == 'best') & (r.court == ct) & (r.rule == 'rematch10') & (r[f'att_{b}'] > 0)][f'att_{b}']; vc = x.clip(upper=6).value_counts(normalize=True).reindex(range(1, 7), fill_value=0) * 100
        ax.plot(vc.index, vc.values, marker='o', color=COL[ct], label=f'{ct} Court')
    ax.set_title(f'{b}: attempts needed'); ax.set_xticks(range(1, 7)); ax.set_xticklabels(['1', '2', '3', '4', '5', '6+'])
axs[0].set_ylabel('% of runs that reached the boss'); axs[0].legend(fontsize=7); fig.suptitle('Rematch rule (10 gold per loss), best play: how many attempts each boss takes'); plt.tight_layout(); plt.savefig(f'{D}/charts/e6_attempts.png'); plt.close()
print('written')
