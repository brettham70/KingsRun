#!/usr/bin/env python3
"""Aggregates the raw simulation CSVs into summary CSVs and charts. Usage: python3 simulation/analyze.py <outDir>
Every number comes from run_results.csv / round_results.csv / event_log.csv in that directory."""
import sys, json, os, math
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

D = sys.argv[1]
cfg = json.load(open(f'{D}/simulation_config.json'))
runs = pd.read_csv(f'{D}/run_results.csv'); rd = pd.read_csv(f'{D}/round_results.csv'); ev = pd.read_csv(f'{D}/event_log.csv')
GROUPS = cfg['groups']; REG = {x['id']: x for x in cfg['regalia']}; DEC = {x['id']: x for x in cfg['decrees']}
os.makedirs(f'{D}/charts', exist_ok=True)
rd = rd.merge(runs[['run_id', 'outcome', 'rounds_reached']], on='run_id')
rd['settle_net'] = rd.treasury_end_settlement - rd.treasury_start          # includes the bankrupt shortfall (negative end)

def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - a) / d, (c + a) / d)
def pct(x): return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(100 * x, 1)

# ---------------- strategy_results.csv ----------------
def strat_row(name, g):
    n = len(g); comp = g[g.outcome == 'completed']; k = len(comp); lo, hi = wilson(k, n)
    f = comp.final_treasury
    row = dict(group=name, runs=n, completed=k, bankrupt=n - k, completion_rate=round(k / n, 4), completion_ci95_lo=round(lo, 4), completion_ci95_hi=round(hi, 4),
        bankruptcy_rate=round((n - k) / n, 4), mean_round_reached=round(g.rounds_reached.mean(), 3), median_round_reached=g.rounds_reached.median(),
        mean_bust_round=round(g[g.outcome == 'bankrupt'].bust_round.mean(), 3) if n - k else np.nan,
        completed_final_treasury_mean=round(f.mean(), 2) if k else np.nan, completed_final_treasury_median=f.median() if k else np.nan,
        completed_final_treasury_min=f.min() if k else np.nan, completed_final_treasury_max=f.max() if k else np.nan,
        pct_completed_gt25=pct((f > 25).mean()) if k else np.nan,
        pct_completed_0_5=pct(f.between(0, 5).mean()) if k else np.nan, pct_completed_6_15=pct(f.between(6, 15).mean()) if k else np.nan, pct_completed_16_30=pct(f.between(16, 30).mean()) if k else np.nan,
        pct_completed_31_50=pct(f.between(31, 50).mean()) if k else np.nan, pct_completed_51plus=pct((f >= 51).mean()) if k else np.nan,
        mean_gold_spent_purchases=round(g.gold_spent_purchases.mean(), 2), mean_gold_spent_rerolls=round(g.gold_spent_rerolls.mean(), 2), mean_gold_from_sales=round(g.gold_from_sales.mean(), 2),
        mean_items_bought=round(g.items_bought.mean(), 2), mean_gold_generated=round(g.gold_generated.mean(), 1), mean_penalties_paid=round(g.penalties_paid.mean(), 1),
        mean_bosses_beaten=round(g.bosses_beaten.mean(), 2))
    return row
S = pd.DataFrame([strat_row(gn, runs[runs.group == gn]) for gn in GROUPS] + [strat_row('ALL', runs)])
S.to_csv(f'{D}/strategy_results.csv', index=False)

# ---------------- round_summary.csv (round difficulty curve + economy) ----------------
rows = []
for r, g in rd.groupby('round'):
    reach = len(g); bust = int(g.bankrupt.sum()); surv = reach - bust
    inc = g.inc_mint + g.inc_tax + g.inc_patron + g.inc_interest + g.herald_marginal + g.earlybird_marginal
    alive = g[g.bankrupt == 0]
    rows.append(dict(round=r, runs_reaching=reach, runs_surviving=surv, bankrupt=bust, conditional_survival=round(surv / reach, 4), cumulative_survival=round(surv / len(runs), 4),
        penalty_raw_mean=round(g.hand_penalty_raw.mean(), 2), penalty_paid_mean=round(g.penalty_paid.mean(), 2), penalty_paid_median=g.penalty_paid.median(), penalty_paid_p90=g.penalty_paid.quantile(.9),
        treasury_start_mean=round(g.treasury_start.mean(), 2), treasury_start_median=g.treasury_start.median(), treasury_start_p10=g.treasury_start.quantile(.1), treasury_start_p90=g.treasury_start.quantile(.9),
        treasury_end_settlement_mean=round(alive.treasury_end_settlement.mean(), 2), treasury_end_settlement_median=alive.treasury_end_settlement.median(),
        treasury_after_court_mean=round(pd.to_numeric(g.treasury_after_court, errors='coerce').mean(), 2), treasury_after_court_median=pd.to_numeric(g.treasury_after_court, errors='coerce').median(),
        rewards_mean=round(g.rewards_total.mean(), 2), regalia_income_mean=round(inc.mean(), 2), court_spend_mean=round((g.court_spent + g.court_rerolls).mean(), 2),
        net_settlement_change_mean=round(g.settle_net.mean(), 2), net_round_change_incl_court_mean=round((pd.to_numeric(g.treasury_delta, errors='coerce')).mean(), 2),
        player_out_rate=round(g.player_out.mean(), 3), raw_penalty_exceeds_rewards_pct=pct((g.hand_penalty_raw > g.rewards_total).mean())))
RS = pd.DataFrame(rows); RS.to_csv(f'{D}/round_summary.csv', index=False)

# ---------------- economy extras ----------------
per_run_min = rd[rd.bankrupt == 0].groupby('run_id').treasury_end_settlement.min()
eco = {}
for T in (5, 10, 15):
    below = rd[(rd.bankrupt == 0) & (rd.treasury_end_settlement < T)]
    first = below.groupby('run_id')['round'].min()
    # recovered = dipped below T at some settlement and later ended a settlement at >= 25 (the starting treasury)
    rec = 0
    for rid, r0 in first.items():
        later = rd[(rd.run_id == rid) & (rd['round'] > r0) & (rd.bankrupt == 0)]
        if (later.treasury_end_settlement >= 25).any(): rec += 1
    eco[f'runs_below_{T}_at_any_settlement'] = int(len(first)); eco[f'pct_runs_below_{T}'] = pct(len(first) / len(runs))
    eco[f'recovered_to_25plus_after_below_{T}'] = rec; eco[f'pct_recovered_after_below_{T}'] = pct(rec / len(first)) if len(first) else None
    eco[f'pct_settlements_below_{T}'] = pct((rd[rd.bankrupt == 0].treasury_end_settlement < T).mean())
eco['second_wind_activations'] = int(rd.second_wind_used.sum()); eco['second_wind_gold_total'] = int(rd.second_wind_gold.sum())
eco['vault_saving_events'] = int((rd.vault_saving > 0).sum()); eco['vault_saving_gold_total'] = int(rd.vault_saving.sum())
eco['gambler_extra_penalty_events'] = int((rd.gambler_extra > 0).sum()); eco['gambler_extra_penalty_gold_total'] = int(rd.gambler_extra.sum())
eco['gambler_going_out_marginal_total'] = int(rd.gambler_marginal_out.sum())
eco['act1_cap_events'] = int((rd.act1_cap_saving > 0).sum()); eco['act1_cap_gold_saved_total'] = int(rd.act1_cap_saving.sum())
eco['act1_cap_binding_pct_of_act1_rounds'] = pct((rd[rd['round'] <= 3].act1_cap_saving > 0).mean())
eco['rounds_penalty_raw_gt_rewards_pct'] = pct((rd.hand_penalty_raw > rd.rewards_total).mean())
json.dump(eco, open(f'{D}/economy_extras.json', 'w'), indent=1)

# ---------------- regalia_results.csv ----------------
off = ev[ev.type == 'offer']; buys = ev[ev.type == 'buy']
ownrows = rd[['run_id', 'group', 'round', 'regalia_owned', 'inc_mint', 'inc_tax', 'inc_patron', 'inc_interest', 'herald_marginal', 'earlybird_marginal', 'gambler_marginal_out', 'gambler_extra', 'vault_saving', 'second_wind_gold', 'second_wind_used',
    'saved_commoner', 'saved_seventh', 'saved_jewels', 'saved_twin', 'saved_lowtide', 'saved_starlight', 'saved_purse', 'player_out', 'penalty_paid', 'hand_penalty_raw']].copy()
ownrows['own_set'] = ownrows.regalia_owned.fillna('').apply(lambda s: set(s.split('|')) if s else set())
direct = {'patron': 'inc_patron', 'interest': 'inc_interest', 'tax': 'inc_tax', 'mint': 'inc_mint', 'herald': 'herald_marginal', 'earlybird': 'earlybird_marginal', 'gambler': 'gambler_marginal_out', 'secondwind': 'second_wind_gold'}
saved = {'vault': 'vault_saving', 'commoner': 'saved_commoner', 'seventh': 'saved_seventh', 'jewels': 'saved_jewels', 'twin': 'saved_twin', 'lowtide': 'saved_lowtide', 'starlight': 'saved_starlight', 'purse': 'saved_purse'}
runs['owned_final_set'] = runs.regalia_final.fillna('').apply(lambda s: set(s.split('|')) if s else set())
# "ever owned" must include items sold or lost; build from buy events instead
ever = buys[buys.kind == 'R'].groupby('run_id').item.apply(set).to_dict()
runs['ever_set'] = runs.run_id.map(lambda r: ever.get(r, set()))
rrows = []
for rid in REG:
    o = off[(off.kind == 'R') & (off.item == rid)]; b = buys[(buys.kind == 'R') & (buys.item == rid)]
    own = ownrows[ownrows.own_set.apply(lambda s: rid in s)]
    owners = runs[runs.ever_set.apply(lambda s: rid in s)]; non = runs[~runs.ever_set.apply(lambda s: rid in s)]
    row = dict(item=rid, name=REG[rid]['name'], list_price=REG[rid]['price'], times_offered=len(o), times_purchased=len(b), purchase_rate_when_offered=round(len(b) / len(o), 4) if len(o) else np.nan,
        times_bought_free=int((b.free == 1).sum()), avg_price_paid=round(b.price.mean(), 2) if len(b) else np.nan,
        runs_owning=len(owners), owner_completion_rate=round((owners.outcome == 'completed').mean(), 4) if len(owners) else np.nan,
        owner_bankruptcy_rate=round((owners.outcome == 'bankrupt').mean(), 4) if len(owners) else np.nan, owner_mean_round_reached=round(owners.rounds_reached.mean(), 3) if len(owners) else np.nan,
        nonowner_completion_rate=round((non.outcome == 'completed').mean(), 4), owner_rounds_owned_total=len(own))
    for r in range(1, 12): row[f'owned_at_round_{r}'] = int((own['round'] == r).sum())
    if rid in direct and len(own): c = direct[rid]; row['direct_gold_total'] = float(own[c].sum()); row['direct_gold_per_owned_round'] = round(own[c].mean(), 3)
    if rid == 'gambler' and len(own): row['gambler_extra_penalty_total'] = float(own.gambler_extra.sum()); row['gambler_net_total'] = float(own.gambler_marginal_out.sum() - own.gambler_extra.sum())
    if rid in saved and len(own):
        c = saved[rid]; v = pd.to_numeric(own[c], errors='coerce')
        row['saved_total'] = float(v.sum()); row['saved_per_owned_round'] = round(v.mean(), 3); row['saved_basis'] = 'gold (production Vault cap)' if rid == 'vault' else 'points on the final hand, same cards, rule switched off (before caps/modifiers)'
    # selection-controlled view: Random group only, where buying is not strategy-driven
    rg = runs[runs.group == 'random']; ro = rg[rg.ever_set.apply(lambda s: rid in s)]; rn = rg[~rg.ever_set.apply(lambda s: rid in s)]
    row['random_group_owners'] = len(ro); row['random_group_owner_completion'] = round((ro.outcome == 'completed').mean(), 4) if len(ro) else np.nan; row['random_group_nonowner_completion'] = round((rn.outcome == 'completed').mean(), 4) if len(rn) else np.nan
    # landmark comparison (reduces survivor bias): only runs still alive at the start of round 5, split by whether the item was already owned then
    lm = rd[rd['round'] == 5][['run_id', 'group', 'own_set', 'outcome']] if False else None
    rrows.append(row)
# landmark analysis (round 5): runs alive at round-5 start, owner vs non-owner at that moment
r5 = ownrows[ownrows['round'] == 5].merge(runs[['run_id', 'outcome']], on='run_id')
def lm(sub, rid):
    o = sub[sub.own_set.apply(lambda s: rid in s)]; n = sub[~sub.own_set.apply(lambda s: rid in s)]
    return len(o), (o.outcome == 'completed').mean() if len(o) else np.nan, len(n), (n.outcome == 'completed').mean() if len(n) else np.nan
for row in rrows:
    for tag, sub in (('all', r5), ('random', r5[r5.group == 'random'])):
        a_, b_, c_, d_ = lm(sub, row['item']); row[f'r5_{tag}_owners'] = a_; row[f'r5_{tag}_owner_completion'] = round(b_, 4) if a_ else np.nan; row[f'r5_{tag}_nonowners'] = c_; row[f'r5_{tag}_nonowner_completion'] = round(d_, 4) if c_ else np.nan
RG = pd.DataFrame(rrows); RG.to_csv(f'{D}/regalia_results.csv', index=False)

# combos: pairs of Regalia owned together at the end of the run (bought at some point; both in regalia_final)
from itertools import combinations
cb = {}
for _, r in runs.iterrows():
    for a, b in combinations(sorted(r.owned_final_set), 2): cb.setdefault((a, b), []).append(r.outcome == 'completed')
combo = pd.DataFrame([dict(pair=f'{a}+{b}', runs=len(v), completion_rate=round(np.mean(v), 3), small_sample=len(v) < 30) for (a, b), v in cb.items()]).sort_values('runs', ascending=False)
combo.to_csv(f'{D}/regalia_combinations.csv', index=False)

# ---------------- decree_results.csv ----------------
# replay events in order to know inventory size when offers were shown
inv_full_offers = {}; held_rounds = {}
for rid, g in ev.groupby('run_id', sort=False):
    inv = 0
    for _, e in g.iterrows():
        if e.type == 'buy' and e.kind == 'D': inv += 1
        elif e.type == 'decree_use': inv -= 1
        elif e.type == 'offer' and e.kind == 'D' and inv >= 3: inv_full_offers[e['item']] = inv_full_offers.get(e['item'], 0) + 1
use = ev[ev.type == 'decree_use']
drows = []
heldlist = rd.decrees_held.fillna('').apply(lambda s: s.split('|') if s else [])
for did in DEC:
    o = off[(off.kind == 'D') & (off['item'] == did)]; b = buys[(buys.kind == 'D') & (buys['item'] == did)]; u = use[use['item'] == did]
    ur = rd[rd.decrees_used.fillna('').apply(lambda s: did in s.split('|'))]
    end_unused = runs.decrees_final.fillna('').apply(lambda s: s.split('|').count(did)).sum()
    row = dict(item=did, name=DEC[did]['name'], list_price=DEC[did]['price'], times_offered=len(o), times_acquired=len(b), acquired_free=int((b.free == 1).sum()), acquire_rate_when_offered=round(len(b) / len(o), 4) if len(o) else np.nan,
        decree_rounds_held=int(heldlist.apply(lambda l: did in l).sum()), times_used=len(u), runs_using=u.run_id.nunique(), unused_at_end_of_run=int(end_unused),
        use_rate_of_acquired=round(len(u) / len(b), 4) if len(b) else np.nan, offered_while_inventory_full=inv_full_offers.get(did, 0),
        avg_round_used=round(u['round'].mean(), 2) if len(u) else np.nan, avg_hand_cost_when_used=round(u.cost_before.mean(), 2) if len(u) else np.nan,
        rounds_with_use=len(ur), player_out_rate_in_those_rounds=round(ur.player_out.mean(), 3) if len(ur) else np.nan, mean_penalty_paid_in_those_rounds=round(ur.penalty_paid.mean(), 2) if len(ur) else np.nan,
        baseline_out_rate_all_rounds=round(rd.player_out.mean(), 3))
    if did == 'insurance': row['direct_gold_saved_total'] = int(ur.insurance_saving.sum()); row['direct_gold_saved_per_use'] = round(ur.insurance_saving.mean(), 2) if len(ur) else np.nan
    if did == 'pardon': row['direct_gold_saved_total'] = int(ur.pardon_saving.sum()); row['direct_gold_saved_per_use'] = round(ur.pardon_saving.mean(), 2) if len(ur) else np.nan
    drows.append(row)
DR = pd.DataFrame(drows); DR.to_csv(f'{D}/decree_results.csv', index=False)

# ---------------- boss_results.csv ----------------
brows = []
for bk, rn in (('miser', 4), ('jester', 8), ('usurper', 11)):
    g = rd[rd.boss == bk]; reach = len(g); won = int(g.beat_boss.sum()); bust = int(g.bankrupt.sum())
    fr = g.regalia_owned.fillna('').apply(lambda s: s.split('|') if s else []); allr = pd.Series([x for l in fr for x in l]).value_counts()
    fd = g.decrees_held.fillna('').apply(lambda s: s.split('|') if s else []); alld = pd.Series([x for l in fd for x in l]).value_counts()
    cont = g[g.bankrupt == 0]; lo, hi = wilson(won, reach)
    brows.append(dict(boss=bk, round=rn, runs_reaching=reach, pct_of_all_runs_reaching=pct(reach / len(runs)), encounters_won=won, encounters_lost=reach - won, boss_success_rate=round(won / reach, 4), success_ci95_lo=round(lo, 4), success_ci95_hi=round(hi, 4),
        player_went_out_rate=round(g.player_out.mean(), 3), treasury_on_entry_mean=round(g.treasury_start.mean(), 2), treasury_on_entry_median=g.treasury_start.median(),
        hand_penalty_raw_mean=round(g.hand_penalty_raw.mean(), 2), penalty_paid_mean=round(g.penalty_paid.mean(), 2), penalty_paid_median=g.penalty_paid.median(),
        gold_change_in_encounter_mean=round(g.settle_net.mean(), 2), gold_change_in_encounter_median=g.settle_net.median(),
        treasury_after_court_mean=round(pd.to_numeric(cont.treasury_after_court, errors='coerce').mean(), 2) if bk != 'usurper' else np.nan,
        runs_ending_at_boss=bust, pct_of_arrivals_ending_at_boss=pct(bust / reach), pct_of_all_runs_ending_at_boss=pct(bust / len(runs)),
        common_regalia_on_entry='; '.join(f'{k} {pct(v / reach)}%' for k, v in allr.head(5).items()), common_decrees_held_on_entry='; '.join(f'{k} {pct(v / reach)}%' for k, v in alld.head(4).items())))
BR = pd.DataFrame(brows); BR.to_csv(f'{D}/boss_results.csv', index=False)
# boss by group
bg = rd[rd.boss != ''].groupby(['boss', 'group']).agg(reached=('run_id', 'count'), won=('beat_boss', 'sum'), bust=('bankrupt', 'sum'), pen=('penalty_paid', 'mean')).reset_index()
bg['success_rate'] = (bg.won / bg.reached).round(3); bg.to_csv(f'{D}/boss_by_group.csv', index=False)

# ---------------- charts ----------------
plt.rcParams.update({'figure.dpi': 130, 'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 10, 'axes.grid': True, 'grid.alpha': .25})
COL = {'baseline': '#7f8c8d', 'random': '#c0392b', 'economic': '#d4a017', 'aggressive': '#8e44ad', 'defensive': '#2471a3', 'ALL': '#222'}
def save(name, title_note=''): plt.tight_layout(); plt.savefig(f'{D}/charts/{name}.png'); plt.close()
BOSSR = (4, 8, 11)
def bossmarks(ax):
    for b in BOSSR: ax.axvline(b, color='#c0392b', ls=':', alpha=.5)
x = RS['round']
# 1 cumulative survival
fig, ax = plt.subplots(figsize=(7, 4)); ax.plot(x, RS.cumulative_survival * 100, marker='o', color=COL['ALL'], label='all 1,000 runs')
for gn in GROUPS:
    gg = rd[rd.group == gn]; n = (runs.group == gn).sum(); s = gg.groupby('round').survived.sum() / n; ax.plot(s.index, s * 100, color=COL[gn], alpha=.8, label=gn)
bossmarks(ax); ax.set_xlabel('round (dotted = boss rounds 4, 8, 11)'); ax.set_ylabel('% of starting runs alive after the round'); ax.set_title('1. Cumulative survival by round'); ax.legend(fontsize=8); ax.set_ylim(0, 102); ax.set_xticks(x); save('01_cumulative_survival')
# 2 conditional survival
fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(x, RS.conditional_survival * 100, color=['#c0392b' if r in BOSSR else '#34495e' for r in x])
for r, v, n in zip(x, RS.conditional_survival * 100, RS.runs_reaching): ax.text(r, v + .3, f'{v:.0f}%\nn={n}', ha='center', fontsize=7)
ax.set_ylim(70, 106); ax.set_xticks(x); ax.set_xlabel('round (red = boss)'); ax.set_ylabel('% surviving, of runs that reached it'); ax.set_title('2. Conditional survival by round'); save('02_conditional_survival')
# 3 treasury by round with bands
fig, ax = plt.subplots(figsize=(7, 4)); ax.fill_between(x, RS.treasury_start_p10, RS.treasury_start_p90, alpha=.2, color='#2471a3', label='10th–90th percentile'); ax.plot(x, RS.treasury_start_median, marker='o', color='#2471a3', label='median')
ax.plot(x, RS.treasury_start_mean, marker='s', color='#d4a017', label='mean'); ax.set_yscale('symlog', linthresh=25); ax.set_xticks(x); ax.set_xlabel('round'); ax.set_ylabel('treasury at start of round (gold, log-ish)'); ax.set_title('3. Treasury at start of round (runs still alive)'); ax.legend(); bossmarks(ax); save('03_treasury_by_round')
# 4 penalty vs rewards
fig, ax = plt.subplots(figsize=(7, 4)); w = .38; ax.bar(x - w / 2, RS.penalty_paid_mean, w, color='#c0392b', label='mean penalty paid'); ax.bar(x + w / 2, RS.rewards_mean, w, color='#27ae60', label='mean rewards')
ax.set_xticks(x); ax.set_xlabel('round'); ax.set_ylabel('gold per round'); ax.set_title('4. Average penalty paid vs rewards earned'); ax.legend(); save('04_penalty_vs_rewards')
# 5 final treasury distribution
c = runs[runs.outcome == 'completed'].final_treasury; fig, ax = plt.subplots(figsize=(7, 4)); ax.hist(c, bins=np.arange(0, max(c.max(), 400) + 20, 20), color='#34495e'); ax.axvline(25, color='#c0392b', ls='--', label='starting 25'); ax.axvline(c.median(), color='#d4a017', label=f'median {c.median():.0f}')
ax.set_xlim(0, 500); ax.set_xlabel('final treasury (completed runs only)'); ax.set_ylabel('runs'); ax.set_title(f'5. Final treasury, completed runs (n={len(c)}; max {c.max()})'); ax.legend(); save('05_final_treasury_distribution')
# 6 bankruptcy round distribution
b = runs[runs.outcome == 'bankrupt'].groupby(['bust_round', 'group']).size().unstack(fill_value=0).reindex(columns=GROUPS, fill_value=0).reindex(range(1, 12), fill_value=0)
fig, ax = plt.subplots(figsize=(7, 4)); bot = np.zeros(len(b))
for gn in GROUPS: ax.bar(b.index, b[gn], bottom=bot, color=COL[gn], label=gn); bot += b[gn].values
ax.set_xticks(range(1, 12)); ax.set_xlabel('round of bankruptcy'); ax.set_ylabel('runs'); ax.set_title(f'6. Where runs go bankrupt (n={int(b.values.sum())})'); ax.legend(fontsize=8); save('06_bankruptcy_round')
# 7 completion by group
fig, ax = plt.subplots(figsize=(7, 4)); gs = S[S.group.isin(GROUPS)]
ax.bar(gs.group, gs.completion_rate * 100, color=[COL[g] for g in gs.group], yerr=[(gs.completion_rate - gs.completion_ci95_lo) * 100, (gs.completion_ci95_hi - gs.completion_rate) * 100], capsize=4)
for i, v in enumerate(gs.completion_rate * 100): ax.text(i, v + 6, f'{v:.1f}%', ha='center')
ax.set_ylim(0, 100); ax.set_ylabel('% of runs completing all 11 rounds (95% CI)'); ax.set_title('7. Completion rate by Court policy (200 runs each)'); save('07_completion_by_group')
# 8 final treasury by group
fig, ax = plt.subplots(figsize=(7, 4)); data = [runs[(runs.group == g) & (runs.outcome == 'completed')].final_treasury for g in GROUPS]
bp = ax.boxplot(data, tick_labels=[f'{g}\n(n={len(d)})' for g, d in zip(GROUPS, data)], showfliers=False, patch_artist=True)
for p, g in zip(bp['boxes'], GROUPS): p.set_facecolor(COL[g]); p.set_alpha(.6)
ax.set_ylabel('final treasury, completed runs (outliers hidden)'); ax.set_title('8. Final treasury by Court policy'); save('08_final_treasury_by_group')
# 9 regalia purchase frequency
R2 = RG.sort_values('times_purchased'); fig, ax = plt.subplots(figsize=(7, 5.5)); ax.barh(R2.name, R2.times_purchased, color='#34495e')
for i, (p, o) in enumerate(zip(R2.times_purchased, R2.times_offered)): ax.text(p + 2, i, f'{p} of {o} offers ({100 * p / o:.0f}%)', va='center', fontsize=7)
ax.set_xlim(0, R2.times_purchased.max() * 1.45); ax.set_xlabel('times purchased (all 1,000 runs; includes free picks)'); ax.set_title('9. Regalia purchase frequency'); save('09_regalia_purchases')
# 10 direct gold / saved
rows10 = []
for _, r in RG.iterrows():
    v = r.get('direct_gold_total'); sv = r.get('saved_total')
    if r['item'] == 'gambler': v = r.get('gambler_net_total')
    t = v if pd.notna(v) else sv
    if pd.notna(t): rows10.append((r['name'], t, 'income' if pd.notna(v) else ('gold saved' if r['item'] == 'vault' else 'points saved')))
R3 = pd.DataFrame(rows10, columns=['name', 'total', 'kind']).sort_values('total'); fig, ax = plt.subplots(figsize=(7, 4.8))
ax.barh(R3.name, R3.total, color=[{'income': '#27ae60', 'gold saved': '#2471a3', 'points saved': '#8e44ad'}[k] for k in R3.kind])
for i, t in enumerate(R3.total): ax.text(t + (R3.total.max() * .01), i, f'{t:,.0f}', va='center', fontsize=7)
ax.set_xlabel('total over all 1,000 runs'); ax.set_title('10. Direct measurable value by Regalia\ngreen = gold income · blue = gold saved · purple = hand points saved', fontsize=10); save('10_regalia_direct_value')
# 11 boss
fig, axs = plt.subplots(1, 2, figsize=(9, 4)); axs[0].bar(BR.boss, BR.boss_success_rate * 100, color='#c0392b', yerr=[(BR.boss_success_rate - BR.success_ci95_lo) * 100, (BR.success_ci95_hi - BR.boss_success_rate) * 100], capsize=4)
for i, (v, n) in enumerate(zip(BR.boss_success_rate * 100, BR.runs_reaching)): axs[0].text(i, v + 4, f'{v:.0f}%\nn={n}', ha='center', fontsize=8)
axs[0].set_ylim(0, 100); axs[0].set_ylabel('% of encounters where player scored below the boss'); axs[0].set_title('success rate (95% CI)')
axs[1].bar(BR.boss, BR.gold_change_in_encounter_mean, color='#d4a017'); axs[1].axhline(0, color='k', lw=.8); axs[1].set_ylabel('mean treasury change (settlement)'); axs[1].set_title('treasury change in boss round', pad=14); axs[1].set_ylim(-2, BR.gold_change_in_encounter_mean.max() * 1.2)
for i, v in enumerate(BR.gold_change_in_encounter_mean): axs[1].text(i, v + (.3 if v >= 0 else -.9), f'{v:+.1f}', ha='center', fontsize=8)
fig.suptitle('11. Boss encounters'); save('11_boss')
# 12 decrees
fig, ax = plt.subplots(figsize=(7, 4)); xx = np.arange(len(DR)); w = .27
ax.bar(xx - w, DR.times_offered, w, color='#95a5a6', label='offered'); ax.bar(xx, DR.times_acquired, w, color='#34495e', label='acquired'); ax.bar(xx + w, DR.times_used, w, color='#27ae60', label='used')
for i, (a, u) in enumerate(zip(DR.times_acquired, DR.times_used)): ax.text(i + w, u + 25, f'{100 * u / a:.0f}%' if a else '', ha='center', fontsize=8, color='#1e8449')
ax.set_xticks(xx); ax.set_xticklabels(DR.name, rotation=15); ax.set_ylabel('count (all runs)'); ax.set_title('12. Decrees: offered, acquired, used\n(green label = used as % of acquired)', fontsize=10); ax.set_ylim(0, 2400); ax.legend(ncol=3, loc='upper center'); save('12_decrees')
print('analysis written to', D)
