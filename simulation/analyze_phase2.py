#!/usr/bin/env python3
"""Paired analysis for Phase 2. Usage: python3 simulation/analyze_phase2.py <dir>. Writes tables/*.csv and charts/*.png into <dir>."""
import sys, os, json
import numpy as np, pandas as pd
from scipy.stats import binomtest
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
D = sys.argv[1]; os.makedirs(f'{D}/tables', exist_ok=True); os.makedirs(f'{D}/charts', exist_ok=True)
rng = np.random.default_rng(20261117); B = 4000
plt.rcParams.update({'figure.dpi': 130, 'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 9, 'axes.grid': True, 'grid.alpha': .25})

def boot(d):
    d = np.asarray(d, float); n = len(d); idx = rng.integers(0, n, (B, n)); m = d[idx].mean(1); return d.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)
def mcnemar(a, b):      # a,b boolean paired arrays: exact two-sided test on discordant pairs
    a = np.asarray(a, bool); b = np.asarray(b, bool); x = int((a & ~b).sum()); y = int((~a & b).sum())
    return 1.0 if x + y == 0 else binomtest(x, x + y, .5).pvalue
def holm(ps):
    o = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0
    for r, k in enumerate(o): run = max(run, (m - r) * ps[k]); adj[k] = min(1, run)
    return adj
def wide(df, col, idx='i', cond='cond'): return df.pivot(index=idx, columns=cond, values=col)
def runs(e): 
    r = pd.read_csv(f'{D}/{e}_runs.csv'); r['completed'] = (r.outcome == 'completed').astype(int); r['early_bust'] = ((r.outcome == 'bankrupt') & (r.bust_round <= 3)).astype(int); r['bust'] = 1 - r.completed; return r
def rounds(e): return pd.read_csv(f'{D}/{e}_rounds.csv')
def summ(r, rd):
    g = r.groupby('cond'); out = pd.DataFrame({'runs': g.size(), 'completion': g.completed.mean(), 'bankrupt': g.bust.mean(), 'early_bust_r2_3': g.early_bust.mean(), 'mean_round_reached': g.rounds_reached.mean(),
        'median_final_treasury_completed': r[r.completed == 1].groupby('cond').final_treasury.median(), 'p90_final_treasury_completed': r[r.completed == 1].groupby('cond').final_treasury.quantile(.9),
        'mean_gold_generated_per_run': g.gold_generated.mean(), 'mean_penalties_paid_per_run': g.penalties_paid.mean(), 'mean_items_bought': g.items_bought.mean()})
    rr = rd.groupby('cond'); out['penalty_paid_per_round'] = rr.penalty_paid.mean(); out['out_rate'] = rr.player_out.mean(); out['turns_per_round'] = rr.player_turns.mean(); out['rewards_per_round'] = rr.rewards_total.mean()
    return out
def paired(r, ref, conds, metric='completed', test=True):
    W = wide(r, metric); rows = []
    for c in conds:
        if c == ref: continue
        d = W[c] - W[ref]; m, lo, hi = boot(d)
        p = mcnemar(W[c] > .5, W[ref] > .5) if (metric in ('completed', 'early_bust', 'bust') and test) else np.nan
        rows.append({'cond': c, 'ref': ref, f'diff_{metric}': m, 'ci_lo': lo, 'ci_hi': hi, 'p_mcnemar': p})
    return pd.DataFrame(rows)
res = {}

# ================= E1 Gambler =================
if os.path.exists(f'{D}/e1_runs.csv'):
    r, rd = runs('e1'), rounds('e1'); S = summ(r, rd)
    own = rd[~rd.cond.str.endswith('control')]; S['gambler_out_gold_per_owned_round'] = own.groupby('cond').gambler_marginal_out.mean(); S['gambler_extra_penalty_per_owned_round'] = own.groupby('cond').gambler_extra.mean()
    S['gambler_net_per_owned_round'] = S.gambler_out_gold_per_owned_round - S.gambler_extra_penalty_per_owned_round
    S['out_reward_per_round'] = rd.groupby('cond').out_reward.mean()
    S.to_csv(f'{D}/tables/e1_summary.csv'); res['e1'] = S
    P = []
    for court in ('none', 'aggressive'):
        cs = [f'{court}|control', f'{court}|g3_15', f'{court}|g2_15', f'{court}|g25_2']
        for ref in (f'{court}|control', f'{court}|g3_15'):
            for metric in ('completed', 'final_treasury', 'penalties_paid', 'rounds_reached'):
                t = paired(r, ref, cs, metric); t['metric'] = metric; P.append(t)
    P = pd.concat(P); P.to_csv(f'{D}/tables/e1_paired.csv', index=False); res['e1p'] = P
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6)); labs = ['control', 'x3 / 1.5\n(current)', 'x2 / 1.5', 'x2.5 / 2']; keys = ['control', 'g3_15', 'g2_15', 'g25_2']
    for ax, court, col in zip(axs[:2], ('none', 'aggressive'), ('#7f8c8d', '#8e44ad')):
        ax.bar(range(4), [S.loc[f'{court}|{k}', 'completion'] * 100 for k in keys], color=col); ax.set_xticks(range(4)); ax.set_xticklabels(labs); ax.set_ylim(0, 100); ax.set_title(f'completion %  ({court} Court)')
        for j, k in enumerate(keys): ax.text(j, S.loc[f'{court}|{k}', 'completion'] * 100 + 1.5, f"{S.loc[f'{court}|{k}','completion']*100:.1f}", ha='center')
    w = .38; x = np.arange(4)
    axs[2].bar(x - w / 2, [S.loc[f'none|{k}', 'median_final_treasury_completed'] for k in keys], w, color='#7f8c8d', label='none Court'); axs[2].bar(x + w / 2, [S.loc[f'aggressive|{k}', 'median_final_treasury_completed'] for k in keys], w, color='#8e44ad', label='aggressive Court')
    axs[2].set_xticks(x); axs[2].set_xticklabels(labs); axs[2].set_title('median final treasury (completed)'); axs[2].legend(fontsize=7)
    fig.suptitle('Experiment 1: Gambler\'s Hand variants (same 1,000 deals each)'); plt.tight_layout(); plt.savefig(f'{D}/charts/e1_gambler.png'); plt.close()

# ================= E2 starting Regalia =================
if os.path.exists(f'{D}/e2_runs.csv'):
    r, rd = runs('e2'), rounds('e2'); S = summ(r, rd); conds = [c for c in S.index if c != 'control']
    rd6 = rd[rd['round'] == 6].groupby('cond').treasury_start.mean(); S['mean_treasury_at_round6_start'] = rd6
    P = paired(r, 'control', conds, 'completed'); P['p_holm'] = holm(P.p_mcnemar.values)
    for m in ('rounds_reached', 'penalties_paid', 'gold_generated', 'final_treasury'):
        t = paired(r, 'control', conds, m); P = P.merge(t[['cond', f'diff_{m}', 'ci_lo', 'ci_hi']].rename(columns={'ci_lo': f'{m}_lo', 'ci_hi': f'{m}_hi'}), on='cond')
    # penalty per round played (paired within run is not defined, so use run-level totals divided by rounds)
    P = P.merge(S[['completion', 'penalty_paid_per_round', 'out_rate', 'mean_treasury_at_round6_start']].reset_index(), on='cond')
    P.to_csv(f'{D}/tables/e2_paired.csv', index=False); S.to_csv(f'{D}/tables/e2_summary.csv'); res['e2'] = (S, P)
    Q = P.sort_values('diff_completed'); fig, ax = plt.subplots(figsize=(7, 5.6))
    ax.errorbar(Q.diff_completed * 100, range(len(Q)), xerr=[(Q.diff_completed - Q.ci_lo) * 100, (Q.ci_hi - Q.diff_completed) * 100], fmt='o', color='#2471a3', capsize=2)
    ax.axvline(0, color='k', lw=.8); ax.set_yticks(range(len(Q))); ax.set_yticklabels(Q.cond); ax.set_xlabel('completion, points vs no-Regalia control (paired, 95% CI)'); ax.set_title(f"Experiment 2: each Regalia forced at round 1 (n={int(S.loc['control','runs'])} matched deals)")
    plt.tight_layout(); plt.savefig(f'{D}/charts/e2_forest.png'); plt.close()

# ================= E3 reserve =================
if os.path.exists(f'{D}/e3_runs.csv'):
    r, rd = runs('e3'), rounds('e3'); S = summ(r, rd); S.to_csv(f'{D}/tables/e3_summary.csv'); res['e3'] = S
    P = []
    for court in ('economic', 'aggressive', 'defensive'):
        cs = [f'{court}|{x}' for x in (5, 10, 15)]
        for m in ('completed', 'early_bust'):
            t = paired(r, cs[0], cs, m); t['metric'] = m; t['court'] = court; P.append(t)
        t = paired(r, 'baseline', cs, 'completed'); t['metric'] = 'completed_vs_baseline'; t['court'] = court; P.append(t)
    P = pd.concat(P); P.to_csv(f'{D}/tables/e3_paired.csv', index=False); res['e3p'] = P
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6))
    for court, col in zip(('economic', 'aggressive', 'defensive'), ('#d4a017', '#8e44ad', '#2471a3')):
        ys = [S.loc[f'{court}|{x}'] for x in (5, 10, 15)]
        axs[0].plot([5, 10, 15], [y.completion * 100 for y in ys], marker='o', color=col, label=court); axs[1].plot([5, 10, 15], [y.early_bust_r2_3 * 100 for y in ys], marker='o', color=col, label=court); axs[2].plot([5, 10, 15], [y.median_final_treasury_completed for y in ys], marker='o', color=col, label=court)
    axs[0].axhline(S.loc['baseline', 'completion'] * 100, color='#7f8c8d', ls='--', label='no-purchase baseline'); axs[0].set_title('completion %'); axs[1].set_title('bankrupt in rounds 2-3 %'); axs[2].set_title('median final treasury (completed)')
    for a in axs: a.set_xticks([5, 10, 15]); a.set_xlabel('reserve (gold kept after buying)')
    axs[0].legend(fontsize=7); fig.suptitle('Experiment 3: Court reserve'); plt.tight_layout(); plt.savefig(f'{D}/charts/e3_reserve.png'); plt.close()

# ================= E4 boss builds =================
if os.path.exists(f'{D}/e4_encounters.csv'):
    e = pd.read_csv(f'{D}/e4_encounters.csv'); e['cond'] = e.build
    S = e.groupby(['boss', 'boss_on', 'build']).agg(n=('i', 'count'), beat=('beat', 'mean'), out=('player_out', 'mean'), pen=('penalty_paid', 'mean'), bust=('bust', 'mean'), turns=('turns', 'mean'), end_gold=('treasury_end', 'mean')).reset_index()
    S.to_csv(f'{D}/tables/e4_summary.csv', index=False); P = []
    for boss in ('miser', 'jester', 'usurper'):
        for on in (1, 0):
            sub = e[(e.boss == boss) & (e.boss_on == on)]
            for m in ('beat', 'penalty_paid', 'player_out', 'bust'):
                t = paired(sub, 'none', sorted(sub.build.unique()), m, test=True); t['boss'] = boss; t['boss_on'] = on; t['metric'] = m; P.append(t)
        # boss effect = on - off, per build, paired by deal
        for b in e.build.unique():
            sub = e[(e.boss == boss) & (e.build == b)]
            for m in ('beat', 'penalty_paid', 'bust'):
                W = sub.pivot(index='i', columns='boss_on', values=m); d = W[1] - W[0]; mm, lo, hi = boot(d); P.append(pd.DataFrame([{'cond': b, 'ref': 'boss_off', f'diff_{m}': mm, 'ci_lo': lo, 'ci_hi': hi, 'p_mcnemar': np.nan, 'boss': boss, 'boss_on': 1, 'metric': m + '_boss_effect'}]))
    P = pd.concat(P); P.to_csv(f'{D}/tables/e4_paired.csv', index=False); res['e4'] = (S, P)
    fig, axs = plt.subplots(1, 3, figsize=(12, 4), sharey=False)
    order = ['none', 'twin', 'fool', 'income', 'defense', 'freeleft', 'wilds', 'wilds_fool', 'wilds_fool_star']
    for ax, boss in zip(axs, ('miser', 'jester', 'usurper')):
        on = S[(S.boss == boss) & (S.boss_on == 1)].set_index('build').loc[order]; off = S[(S.boss == boss) & (S.boss_on == 0)].set_index('build').loc[order]; x = np.arange(len(order))
        ax.bar(x - .2, off.beat * 100, .4, color='#95a5a6', label='same round, boss off'); ax.bar(x + .2, on.beat * 100, .4, color='#c0392b', label='boss on'); ax.set_xticks(x); ax.set_xticklabels(order, rotation=60, ha='right'); ax.set_title(boss + ' round: % rounds player scores below seat-2'); ax.set_ylim(0, 100)
    axs[0].legend(fontsize=7); fig.suptitle('Experiment 4: matched builds vs each boss (same deals, 40 gold in)'); plt.tight_layout(); plt.savefig(f'{D}/charts/e4_bosses.png'); plt.close()

# ================= E5 weaker players =================
if os.path.exists(f'{D}/e5_runs.csv'):
    r, rd = runs('e5'), rounds('e5'); S = summ(r, rd); S.to_csv(f'{D}/tables/e5_summary.csv'); res['e5'] = S; P = []
    for court in ('none', 'defensive', 'aggressive', 'economic'):
        cs = [f'{court}|{p}' for p in ('best', 'skill80', 'skill55', 'skill30', 'deckonly', 'deckonly80')]
        t = paired(r, cs[0], cs, 'completed'); t['court'] = court; P.append(t)
    P = pd.concat(P); P.to_csv(f'{D}/tables/e5_paired.csv', index=False); res['e5p'] = P
    pols = ['best', 'deckonly', 'skill80', 'deckonly80', 'skill55', 'skill30']; fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
    for court, col in zip(('none', 'defensive', 'aggressive', 'economic'), ('#7f8c8d', '#2471a3', '#8e44ad', '#d4a017')):
        axs[0].plot(range(6), [S.loc[f'{court}|{p}', 'completion'] * 100 for p in pols], marker='o', color=col, label=court); axs[1].plot(range(6), [S.loc[f'{court}|{p}', 'turns_per_round'] for p in pols], marker='o', color=col, label=court)
    for a in axs: a.set_xticks(range(6)); a.set_xticklabels(pols, rotation=25)
    axs[0].set_title('completion % by player decision policy'); axs[1].set_title('player turns per round'); axs[0].legend(fontsize=7); fig.suptitle('Experiment 5: weaker card play'); plt.tight_layout(); plt.savefig(f'{D}/charts/e5_players.png'); plt.close()
print('phase 2 analysis written')
