#!/usr/bin/env python3
"""Writes balance_report.md for a finished simulation directory. All figures are read from that directory's CSVs (nothing typed in by hand);
the interpretation text is mine. Usage: python3 simulation/make_report.py <runDir> <sensitivityDir>"""
import sys, json, math
import numpy as np, pandas as pd
from scipy.stats import norm
D, D2 = sys.argv[1], sys.argv[2]
cfg = json.load(open(f'{D}/simulation_config.json')); man = json.load(open(f'{D}/simulation_manifest.json'))
runs = pd.read_csv(f'{D}/run_results.csv'); rd = pd.read_csv(f'{D}/round_results.csv'); S = pd.read_csv(f'{D}/strategy_results.csv').set_index('group')
S2 = pd.read_csv(f'{D2}/strategy_results.csv').set_index('group'); RS = pd.read_csv(f'{D}/round_summary.csv').set_index('round')
RG = pd.read_csv(f'{D}/regalia_results.csv').set_index('item'); DR = pd.read_csv(f'{D}/decree_results.csv').set_index('item'); BR = pd.read_csv(f'{D}/boss_results.csv').set_index('boss')
BG = pd.read_csv(f'{D}/boss_by_group.csv'); CB = pd.read_csv(f'{D}/regalia_combinations.csv'); eco = json.load(open(f'{D}/economy_extras.json')); val = json.load(open(f'{D}/validation_results.json'))
rd2 = pd.read_csv(f'{D2}/round_results.csv'); val2 = json.load(open(f'{D2}/validation_results.json'))
G = cfg['groups']; N = len(runs)
def md(df, floatfmt='g'): return df.to_markdown(index=False, floatfmt=floatfmt)
def pc(x, d=1): return f'{100 * x:.{d}f}%'
def ztest(k1, n1, k2, n2):
    p = (k1 + k2) / (n1 + n2); se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)); z = (k1 / n1 - k2 / n2) / se; return 2 * (1 - norm.cdf(abs(z)))
comp = lambda df, g: int(df.loc[g, 'completed'])
n_per = int(S.loc['baseline', 'runs'])

# ---- tables ----
t_strat = pd.DataFrame({'Group': G + ['ALL'], 'Runs': [int(S.loc[g, 'runs']) for g in G + ['ALL']], 'Completed': [int(S.loc[g, 'completed']) for g in G + ['ALL']],
    'Completion (95% CI)': [f"{pc(S.loc[g,'completion_rate'])} ({pc(S.loc[g,'completion_ci95_lo'],0)}–{pc(S.loc[g,'completion_ci95_hi'],0)})" for g in G + ['ALL']],
    'Mean round reached': [S.loc[g, 'mean_round_reached'] for g in G + ['ALL']], 'Median final treasury (completed)': [S.loc[g, 'completed_final_treasury_median'] for g in G + ['ALL']],
    'Mean gold spent (purchases / rerolls)': [f"{S.loc[g,'mean_gold_spent_purchases']:.1f} / {S.loc[g,'mean_gold_spent_rerolls']:.1f}" for g in G + ['ALL']],
    'Items bought / run': [S.loc[g, 'mean_items_bought'] for g in G + ['ALL']]})
t_vs = []
for g in G[1:]:
    t_vs.append({'Group': g, 'Completion': pc(S.loc[g, 'completion_rate']), 'vs baseline (pts)': f"{100*(S.loc[g,'completion_rate']-S.loc['baseline','completion_rate']):+.1f}", 'p (two-proportion z)': f"{ztest(comp(S,g), n_per, comp(S,'baseline'), n_per):.3f}",
        'Sensitivity (reserve 10)': pc(S2.loc[g, 'completion_rate']), 'sens. vs baseline (pts)': f"{100*(S2.loc[g,'completion_rate']-S2.loc['baseline','completion_rate']):+.1f}", 'sens. p': f"{ztest(comp(S2,g), n_per, comp(S2,'baseline'), n_per):.3f}"})
t_vs = pd.DataFrame(t_vs)
fin = runs[runs.outcome == 'completed'].final_treasury
buckets = pd.DataFrame({'Final treasury': ['0–5', '6–15', '16–30', '31–50', '51+'], 'Completed runs': [int(fin.between(0, 5).sum()), int(fin.between(6, 15).sum()), int(fin.between(16, 30).sum()), int(fin.between(31, 50).sum()), int((fin >= 51).sum())]})
buckets['Share'] = (buckets['Completed runs'] / len(fin) * 100).round(1).astype(str) + '%'
t_round = RS.reset_index()[['round', 'runs_reaching', 'bankrupt', 'conditional_survival', 'cumulative_survival', 'penalty_raw_mean', 'penalty_paid_mean', 'penalty_paid_median', 'rewards_mean', 'regalia_income_mean', 'court_spend_mean', 'net_settlement_change_mean', 'treasury_start_median', 'treasury_end_settlement_median']]
t_round.columns = ['Round', 'Reached', 'Bankrupt', 'Cond. survival', 'Cum. survival', 'Raw penalty (mean)', 'Penalty paid (mean)', 'Penalty paid (median)', 'Rewards (mean)', 'Regalia income (mean)', 'Court spend (mean)', 'Net at settlement (mean)', 'Treasury start (median)', 'Treasury after settlement (median)']
t_round['Cond. survival'] = (t_round['Cond. survival'] * 100).round(1).astype(str) + '%'; t_round['Cum. survival'] = (t_round['Cum. survival'] * 100).round(1).astype(str) + '%'
t_boss = BR.reset_index()[['boss', 'round', 'runs_reaching', 'encounters_won', 'boss_success_rate', 'player_went_out_rate', 'treasury_on_entry_median', 'hand_penalty_raw_mean', 'penalty_paid_mean', 'gold_change_in_encounter_mean', 'runs_ending_at_boss', 'pct_of_arrivals_ending_at_boss']]
t_boss.columns = ['Boss', 'Round', 'Reached', 'Beaten', 'Success', 'Player out rate', 'Treasury on entry (median)', 'Raw penalty (mean)', 'Penalty paid (mean)', 'Net gold in round (mean)', 'Runs ended here', '% of arrivals ended']
t_boss['Success'] = (t_boss['Success'] * 100).round(1).astype(str) + '%'; t_boss['% of arrivals ended'] = t_boss['% of arrivals ended'].astype(str) + '%'
bgp = BG.pivot(index='boss', columns='group', values='success_rate')[G].reset_index(); bgp = bgp.set_index('boss').loc[['miser', 'jester', 'usurper']].reset_index()
# regalia table
rg = RG.reset_index()
def direct_text(r):
    if pd.notna(r.get('direct_gold_per_owned_round')): return f"{r['direct_gold_per_owned_round']:.2f} gold/round"
    if pd.notna(r.get('saved_per_owned_round')): return f"{r['saved_per_owned_round']:.2f} {'gold' if r['item']=='vault' else 'pts'}/round"
    return 'n/a (no direct gold effect)'
t_reg = pd.DataFrame({'Regalia': rg.name, 'Price': rg.list_price, 'Offered': rg.times_offered, 'Bought': rg.times_purchased, 'Buy rate': (rg.purchase_rate_when_offered * 100).round(1).astype(str) + '%', 'Runs owning': rg.runs_owning,
    'Direct value per owned round': rg.apply(direct_text, axis=1),
    'Completion, owners at round 5 (n)': rg.apply(lambda r: f"{r.r5_all_owner_completion*100:.0f}% ({int(r.r5_all_owners)})", axis=1), 'Completion, non-owners at round 5': (rg.r5_all_nonowner_completion * 100).round(0).astype(int).astype(str) + '%'})
t_reg = t_reg.sort_values('Price', ascending=False)
t_dec = DR.reset_index()[['name', 'list_price', 'times_offered', 'times_acquired', 'acquire_rate_when_offered', 'times_used', 'use_rate_of_acquired', 'unused_at_end_of_run', 'offered_while_inventory_full', 'avg_round_used', 'direct_gold_saved_per_use']]
t_dec.columns = ['Decree', 'Price', 'Offered', 'Acquired', 'Acquire rate', 'Used', 'Used / acquired', 'Unused at run end', 'Offered while 3 held', 'Avg round used', 'Gold saved per use']
t_dec = t_dec.astype(object).where(t_dec.notna(), '—')
t_dec['Acquire rate'] = (t_dec['Acquire rate'] * 100).round(1).astype(str) + '%'; t_dec['Used / acquired'] = (t_dec['Used / acquired'] * 100).round(0).astype(int).astype(str) + '%'
big = CB[CB.runs >= 90].head(8)[['pair', 'runs', 'completion_rate']]; big['completion_rate'] = (big.completion_rate * 100).round(0).astype(int).astype(str) + '%'; big.columns = ['Pair held at end of run', 'Runs', 'Completion']

# ---- computed facts used in prose ----
boss_rows = rd[rd.boss.notna()]; nb_rows = rd[rd.boss.isna()]
boss_bust = boss_rows.bankrupt.mean(); nb_bust = nb_rows.bankrupt.mean(); busts = int(rd.bankrupt.sum()); busts_on_boss = int(boss_rows.bankrupt.sum())
a1 = rd[(rd['round'] <= 3) & (rd.bankrupt == 1)]; a1_2 = rd2[(rd2['round'] <= 3) & (rd2.bankrupt == 1)]
a1g = a1.group.value_counts().to_dict(); a1g2 = a1_2.group.value_counts().to_dict()
eb = rd[rd.regalia_owned.fillna('').str.contains('earlybird')]; eb_trig = ((eb.player_out == 1) & (eb.player_turns <= 3)).mean()
gm = RG.loc['gambler']; net_g = gm.gambler_net_total / gm.owner_rounds_owned_total
mean_turns = rd.player_turns.mean(); med_turns = rd.player_turns.median()
outrate = rd.player_out.mean()
pos_net = (RS.loc[1:10, 'net_settlement_change_mean'] > 0).all()
low = RS.loc[RS.conditional_survival.nsmallest(4).index.sort_values()]
inc = ['mint', 'tax', 'interest', 'patron', 'herald']; hand = ['commoner', 'seventh', 'jewels', 'fool', 'starlight', 'secondwind']
inc_own = RG.loc[inc, 'r5_all_owner_completion']; hand_own = RG.loc[hand, 'r5_all_owner_completion']
base_comp = S.loc['baseline', 'completion_rate']; ok_all = all(v['ok'] for v in val); ok2 = all(v['ok'] for v in val2)
ev = pd.read_csv(f'{D}/event_log.csv'); fp = int(((ev.type == 'buy') & (ev.free == 1)).sum()); bounties = int((rd.boss_bounty > 0).sum())
pv = {g: ztest(comp(S, g), n_per, comp(S, 'baseline'), n_per) for g in G[1:]}; pv2 = {g: ztest(comp(S2, g), n_per, comp(S2, 'baseline'), n_per) for g in G[1:]}
dd = lambda a, b: 100 * (a - b)
sens_gain = {g: dd(S2.loc[g, 'completion_rate'], S.loc[g, 'completion_rate']) for g in ('economic', 'aggressive', 'defensive')}
eco_early = runs[(runs.group == 'economic') & (runs.outcome == 'bankrupt')].bust_round.between(2, 5).mean()
r5 = rd[rd['round'] == 5]; r5b = r5[r5.bankrupt == 1]; r5g = r5.groupby('group').bankrupt.mean()
nmin = int(min(RG.r5_all_owners.min(), RG.r5_all_nonowners.min())); nmax = int(RG.r5_all_owners.max())
fmtd = lambda d: ', '.join(f'{k} {v}' for k, v in d.items())
ref = rd.groupby('round').player_out.mean()

R = []
w = R.append
w(f"""# The Run — 1,000-Run Baseline Balance Report

*Simulation version {man['sim_version']} · game code commit `{(man['git_commit'] or '')[:10]}` · executed {man['executed_at'][:16].replace('T',' ')} UTC · base seed {cfg['base_seed']} · {N:,} runs, {len(rd):,} round settlements, {man['events_recorded']:,} logged events.*

**What this is.** A measurement of The Run as it is *today*, using the game's own rules code (loaded straight from `index.html`, unmodified), not a proposal to change it. Nothing in the game was changed. Every figure below is computed from the raw CSVs in this folder; where something is an interpretation, an assumption or a heuristic, it is labelled.

## 1. Executive summary

- **Completion:** {int(S.loc['ALL','completed'])} of {N:,} runs ({pc(S.loc['ALL','completion_rate'])}, 95% CI {pc(S.loc['ALL','completion_ci95_lo'],0)}–{pc(S.loc['ALL','completion_ci95_hi'],0)}) survived all 11 rounds; {int(S.loc['ALL','bankrupt'])} ({pc(S.loc['ALL','bankruptcy_rate'])}) went bankrupt. Median round reached: {S.loc['ALL','median_round_reached']:.0f}; mean {S.loc['ALL','mean_round_reached']:.2f}.
- **Typical bankrupt run** ends around round {S.loc['ALL','mean_bust_round']:.1f} on average, but the failures cluster: round 4 (The Miser) alone ends {int(RS.loc[4,'bankrupt'])} runs.
- **Final treasury is high and wide** for completed runs: median {fin.median():.0f}, mean {fin.mean():.0f}, max {fin.max():.0f}; {buckets.iloc[4,2]} of completed runs finish with 51+ gold and only {int(fin.between(0,5).sum())+int(fin.between(6,15).sum())} of {len(fin)} finish with 15 or less. Winning runs are rarely close calls.
- **Doing nothing is a strong strategy.** The no-purchase baseline completed {pc(base_comp)}. In the headline run no buying policy beat it significantly (Defensive {dd(S.loc['defensive','completion_rate'],base_comp):+.1f} points, p={pv['defensive']:.2f}; Aggressive {dd(S.loc['aggressive','completion_rate'],base_comp):+.1f}, p={pv['aggressive']:.2f}). Only Defensive with a 10-gold reserve did ({dd(S2.loc['defensive','completion_rate'],base_comp):+.1f} points, p={pv2['defensive']:.3f}). Economic ({pc(S.loc['economic','completion_rate'])}) and Random ({pc(S.loc['random','completion_rate'])}) were significantly *worse* than doing nothing.
- **Strongest single finding:** Gambler's Hand (price {int(gm.list_price)}) produced about {net_g:.1f} net gold per round owned (gold ×3 on going out, minus the 1.5× penalty), several times any other income Regalia.
- **Where difficulty comes from:** boss rounds (3 of 11 rounds) account for {busts_on_boss} of {busts} bankruptcies ({pc(busts_on_boss/busts,0)}). A run arriving at a boss round goes bankrupt {pc(boss_bust)} of the time versus {pc(nb_bust)} on other rounds.
- **Gold inflates:** median treasury at the start of a round climbs from {RS.loc[1,'treasury_start_median']:.0f} (round 1) to {RS.loc[11,'treasury_start_median']:.0f} (round 11); the average round nets +gold in every round 1–10.

*Important framing:* the "player" here is the game's own computer-player AI playing at full strength (see §9). Real human survival rates will differ, most likely lower. Treat every rate as a comparison between rules and policies, not a prediction of human win rate.

## 2. How the simulation was done

- **Real rules reused.** The harness slices the production code out of `index.html` (engine, round lifecycle, `rulesFor`, `runEndRound`, Court, Decrees, bosses, the computer-player AI) and runs it headless. Two tiny click-handler snippets that are not functions in the page (reroll, "deal next round") are replicated and marked in `harness.js`. A hand-rule replica (used only to price what Regalia saved) is asserted equal to the game's own scoring on every round.
- **Card play.** The page has no AI for the player's own seat, so the opponent AI (`aiDraw`/`aiDiscard`, best play every time) plays seat 0. It is the same for every group. Opponents follow the Run's own tiers (Squire/Knight/Baron, skill 0.55/0.8/0.95; bosses skill 1).
- **Court policies** (what varies between groups). Documented in `simulation_config.json`. In short: **Baseline** never buys (takes a Boss-bounty free pick if one exists); **Random** picks uniformly among legal actions; **Economic / Aggressive / Defensive** buy the best-ranked affordable item from a list derived from the real item text, keeping a reserve of {cfg['reserve_gold_after_listed_purchase']} gold. Decree use is one fixed heuristic for all groups.
- **Seeds.** Each run has its own seed (recorded); group = run index mod 5, so every group samples the whole seed range. {man['runs_recorded']:,} runs were started, 200 per group. Re-running any recorded seed with its group reproduces the identical run (checked in validation).
- **Sensitivity run.** After seeing that some early bankruptcies were caused by the policies keeping too little gold in reserve, I ran a second full 1,000 with a reserve of 10 (the game's own Act-1 warning level). It is labelled separately in §6; the headline numbers are the pre-planned reserve-5 run.

## 3. Differences between the design summary and the code

I treated the code as the source of truth. These differ from the summary supplied:

1. **There are 19 Regalia, not 9.** All nine listed Regalia exist exactly as described. Ten more exist: Commoner's Crown (3s wild), Seventh Heaven (7s wild), Crown Jewels (Kings wild), Court Fool (extra Joker each round), Twin Crowns (royal pairs are books), Starlight (★ leftovers free), Low Tide (3–5 leftovers free), Heavy Purse (J/Q/K leftovers cost 5), Spyglass and Eavesdropper (information only).
2. **Decrees (not supplied) are six:** Pickpocket, Scout, Redeal, Fog, Royal Pardon, Insurance.
3. **Reroll cost is not flat 2.** It starts at 2 each Court visit and goes up by 1 with every reroll in that visit (2, 3, 4 …).
4. **Boss bounty / free pick.** The bounty sets a flag that makes *every* offer free until the first purchase. It carries over to later Courts if unused. There is no Court after round 11, so the Usurper's bounty is +12 gold only. In this data {bounties} boss bounties were earned and {fp} free picks were used (checked in validation: never more than bounties earned).
5. **Order of bill modifiers** (matters for Regalia interplay): Royal Pardon → Gambler ×1.5 (rounded up) → Insurance halving (rounded up) → Act 1 cap (10) → Miser's Vault cap (25). Hand-rule Regalia (Low Tide, Starlight, Purse, extra wilds) act earlier by changing the cost of leftovers.
6. **Bankruptcy timing.** The bill is paid first; bankrupt means treasury **below 0** (0 is alive). Second Wind then resets the treasury to 10. Income is only collected *after* the bankruptcy check, so income cannot save a round in which you are bankrupted.
7. **"Lowest score" reward counts ties** (player's points ≤ both opponents). Going out always scores 0, so it always qualifies.
8. **Bosses.** Boss is seat 1. "Beat the boss" is strictly fewer points than the boss. The Miser stops *everyone* (not only the player) taking discards; the Jester's wild change applies to all hands; the Usurper's dead Jokers apply to the player only.
9. **Early Bird** counts the player's own turns including the turn they go out.
10. **Information-only items** (Spyglass, Eavesdropper, Scout) can't be evaluated with this AI because it never uses that information (§9).

## 4. Survival analysis

![](charts/01_cumulative_survival.png)
![](charts/02_conditional_survival.png)

Conditional survival uses only runs that reached the round; cumulative uses all {N:,} starting runs.

{md(t_round, '.2f')}

**Reading it.** Difficulty is **not smooth**. The four weakest rounds are {', '.join(f"round {i} ({pc(low.loc[i,'conditional_survival'])})" for i in low.index)} — three of them boss rounds. **Round 2's dip is Court overspending:** no baseline run goes bankrupt in rounds 1–3 (the Act 1 cap means anyone holding 10+ gold is safe), so every early bankruptcy follows a purchase. **Round 5** follows The Miser with no Act 1 cap in place: the runs that go bankrupt there arrive with a median of {r5b.treasury_start.median():.0f} gold and face a median bill of {r5b.penalty_paid.median():.0f}; spenders suffer most (bankruptcy rate at round 5: {', '.join(f'{k} {v*100:.0f}%' for k,v in r5g.sort_values().items())}).

![](charts/06_bankruptcy_round.png)

### Bosses

{md(t_boss, '.2f')}

Boss success by Court policy:

{md(bgp, '.3f')}

- **The Miser (round 4) is the single deadliest point:** {int(BR.loc['miser','runs_ending_at_boss'])} runs end there ({BR.loc['miser','pct_of_all_runs_ending_at_boss']}% of all runs), and runs arrive with a median of only {BR.loc['miser','treasury_on_entry_median']:.0f} gold because early Court spending has drained them.
- **The Usurper (round 11) is the hardest to *beat*** ({pc(BR.loc['usurper','boss_success_rate'])} success; the player goes out only {pc(BR.loc['usurper','player_went_out_rate'],0)} of the time versus {pc(outrate,0)} overall) **but rarely lethal** ({BR.loc['usurper','pct_of_arrivals_ending_at_boss']}% of arrivals), since arriving treasuries are large (median {BR.loc['usurper','treasury_on_entry_median']:.0f}). It costs points, not runs.
- **The Jester (round 8)** is the one where builds matter most: Aggressive runs beat it {pc(BG[(BG.boss=='jester')&(BG.group=='aggressive')].success_rate.iloc[0],0)} of the time versus {pc(BG[(BG.boss=='jester')&(BG.group=='defensive')].success_rate.iloc[0],0)} for Defensive and Economic, {pc(BG[(BG.boss=='jester')&(BG.group=='baseline')].success_rate.iloc[0],0)} for the baseline and {pc(BG[(BG.boss=='jester')&(BG.group=='random')].success_rate.iloc[0],0)} for Random. Extra wild ranks and the extra Joker blunt a wild that changes every turn. This is a build interaction worth watching, not proof of an unfair boss.

![](charts/11_boss.png)

## 5. Gold economy

![](charts/03_treasury_by_round.png)
![](charts/04_penalty_vs_rewards.png)

- **Gaining or losing?** Players gain gold on average in every round from 1 to 10 (net at settlement +{RS.loc[1:10,'net_settlement_change_mean'].min():.1f} to +{RS.loc[1:10,'net_settlement_change_mean'].max():.1f}); round 11 is roughly break-even ({RS.loc[11,'net_settlement_change_mean']:+.1f}).
- **Inflation:** yes. Median start-of-round treasury {RS.loc[1,'treasury_start_median']:.0f} → {RS.loc[11,'treasury_start_median']:.0f}; the 90th percentile at round 11 is {RS.loc[11,'treasury_start_p90']:.0f}. After the Regalia and Decree slots are full, gold has nothing to buy.
- **Penalty vs rewards.** The raw hand penalty exceeds that round's rewards in {eco['rounds_penalty_raw_gt_rewards_pct']}% of settlements overall and in {RS.loc[11,'raw_penalty_exceeds_rewards_pct']}% of round 11 settlements. Averaged per round, rewards exceed penalties paid in rounds 1–10; in round 11 they are about equal ({RS.loc[11,'penalty_paid_mean']:.1f} paid vs {RS.loc[11,'rewards_mean']:.1f} rewards).
- **Approaching bankruptcy.** {eco['pct_runs_below_15']}% of runs dipped below 15 gold at some settlement, {eco['pct_runs_below_10']}% below 10, {eco['pct_runs_below_5']}% below 5. Of those, {eco['pct_recovered_after_below_15']}% / {eco['pct_recovered_after_below_10']}% / {eco['pct_recovered_after_below_5']}% later reached 25+ gold again (*recovery here = ended a later round at ≥ the starting 25 gold*).
- **Act 1 cap.** It bound in {eco['act1_cap_binding_pct_of_act1_rounds']}% of Act 1 rounds, saving {eco['act1_cap_gold_saved_total']:,} gold in total. For the no-purchase baseline it works perfectly: **0 baseline runs went bankrupt in rounds 1–3**. It does not protect runs that spend the treasury down: {len(a1)} runs went bankrupt in rounds 2–3, all in buying groups ({fmtd(a1g)}).
- **Second Wind** fired {eco['second_wind_activations']} times (restoring {eco['second_wind_gold_total']:,} gold in total). **Miser's Vault** cap applied {eco['vault_saving_events']} times (saving {eco['vault_saving_gold_total']:,} gold). **Gambler's Hand** extra penalty hit {eco['gambler_extra_penalty_events']} times costing {eco['gambler_extra_penalty_gold_total']:,} gold, against {eco['gambler_going_out_marginal_total']:,} gold of extra going-out reward.

![](charts/05_final_treasury_distribution.png)

Final treasury, completed runs only (bankrupt runs are reported separately and not mixed in):

{md(buckets)}

## 6. Strategy comparison

{md(t_strat, '.2f')}

![](charts/07_completion_by_group.png)
![](charts/08_final_treasury_by_group.png)

Difference from the no-purchase baseline (200 runs each, so each rate carries roughly ±7 points):

{md(t_vs)}

- **Strongest:** Defensive, then Aggressive. Defensive ({pc(S.loc['defensive','completion_rate'])}, sensitivity {pc(S2.loc['defensive','completion_rate'])}) is the only policy to beat the baseline convincingly, and only once it keeps 10 gold in reserve.
- **Weakest:** Random and Economic, both significantly below the baseline. Economic buys gold generators that pay off late, but {pc(eco_early,0)} of its bankruptcies happen in rounds 2–5, before they pay off. Among the survivors it finishes richer than the baseline (median {S.loc['economic','completed_final_treasury_median']:.0f} vs {S.loc['baseline','completed_final_treasury_median']:.0f}). Defensive finishes with far less gold (median {S.loc['defensive','completed_final_treasury_median']:.0f}) because it spends on its set and its Regalia mostly save rather than earn.
- **Aggressive** survives about as often as the baseline but finishes with enormous treasuries (median {S.loc['aggressive','completed_final_treasury_median']:.0f}, max {S.loc['aggressive','completed_final_treasury_max']:.0f}), driven by Gambler's Hand and Early Bird.
- **Caveats.** The policies are my heuristics, not optimal play. Differences of under ~10 points between groups are within sampling noise at 200 runs each. The reserve sensitivity ({min(sens_gain.values()):+.1f} to {max(sens_gain.values()):+.1f} points for the listed policies) shows how much an arbitrary policy parameter can move a result. The Baseline is not a pure "no items" control: it takes the free pick after a boss win ({fp} free picks across all groups, {int(((ev.type=='buy')&(ev.free==1)&ev.run_id.isin(runs[runs.group=='baseline'].run_id)).sum())} of them in the baseline).

## 7. Regalia and Decrees

![](charts/09_regalia_purchases.png)
![](charts/10_regalia_direct_value.png)

{md(t_reg)}

*Direct value:* income and Vault figures are gold. Hand-rule Regalia (wilds, Low Tide, Starlight, Purse, Twin) are shown as **points saved on the final hand with that rule switched off** (same cards; before caps, and ignoring that these Regalia also help a player *go out*, which is not captured). Court Fool, Spyglass and Eavesdropper have no direct gold effect that can be measured.

*Owner vs non-owner:* to reduce survivor bias (an expensive Regalia can only be bought by a run that stayed alive long enough) the last two columns look only at runs still alive at the start of round 5. Raw owner/non-owner completion across all runs is in `regalia_results.csv` but flatters expensive items. This is still an **association, not a cause**: owners differ from non-owners in strategy, gold and luck. Owner group sizes at round 5 range from {int(RG.r5_all_owners.min())} to {nmax} runs, so the smaller ones are shaky.

- **Most frequently bought:** {', '.join(RG.sort_values('times_purchased', ascending=False).name.head(3))} (cheap, and favoured by several policies). **Rarest:** Spyglass and Eavesdropper (bought only by the Random policy or as free picks).
- **Most impactful (direct gold):** Gambler's Hand, then Early Bird and Herald.
- **Strongest survival association (round-5 landmark):** the wild-making and hand Regalia — {', '.join(f"{RG.loc[i,'name']} {pc(RG.loc[i,'r5_all_owner_completion'],0)}" for i in hand_own.sort_values(ascending=False).index[:4])} — against {pc(RG.r5_all_nonowner_completion.mean(),0)} for non-owners.
- **Income Regalia do not show that association** ({', '.join(f"{RG.loc[i,'name']} {pc(inc_own[i],0)}" for i in inc)}), and several sit at or below the non-owner rate.

**Pairs** (held together at the end of a run; ≥90 runs only):

{md(big)}

These pairs mostly reflect what a single policy buys together (e.g. the Defensive set), so they are not evidence of synergy. Of {len(CB)} observed pairs, {int((~CB.small_sample).sum())} have 30+ runs; the rest are too rare to say anything about (full list in `regalia_combinations.csv`).

### Decrees

![](charts/12_decrees.png)

{md(t_dec, '.2f')}

Insurance and Royal Pardon pay back roughly their price in gold saved when used by this heuristic ({DR.loc['insurance','direct_gold_saved_per_use']:.1f} gold per use for a price of {int(DR.loc['insurance','list_price'])}; {DR.loc['pardon','direct_gold_saved_per_use']:.1f} for {int(DR.loc['pardon','list_price'])}). Redeal is acquired often but used only {pc(DR.loc['redeal','use_rate_of_acquired'],0)} of the time under my heuristic, and {int(DR.loc['redeal','unused_at_end_of_run'])} were still unused when runs ended. That reflects my use-rule at least as much as the Decree itself. Scout and Fog were bought almost only by the Random policy (the listed policies leave them out).

## 8. Findings and recommendations

*Classification:* **Evidence-backed** = adequate data from this simulation. **Potential** = plausible, needs more samples or controlled testing. **Not enough evidence** = missing data or implementation detail. No change below has been made to the game.

| # | Finding | Class | Evidence | Possible response | What to measure next |
|---|---|---|---|---|---|
| 1 | Gambler's Hand is far cheaper than the gold it produces | Evidence-backed | price {int(gm.list_price)}; ≈{net_g:.1f} net gold per owned round vs {RG.loc['earlybird','direct_gold_per_owned_round']:.1f} Early Bird (price {int(RG.loc['earlybird','list_price'])}), {RG.loc['herald','direct_gold_per_owned_round']:.1f} Herald ({int(RG.loc['herald','list_price'])}), {RG.loc['patron','direct_gold_per_owned_round']:.1f} Patron ({int(RG.loc['patron','list_price'])}); heavily drives Aggressive treasuries up to {S.loc['aggressive','completed_final_treasury_max']:.0f} | Raise its price or lower the ×3; expected effect is a smaller gold surplus, not necessarily lower survival | Re-run with the change; compare Aggressive final treasury and completion |
| 2 | Early deaths come from spending, not from the cards | Evidence-backed | 0 baseline busts in rounds 1–3; {len(a1)} busts in rounds 2–3 among buyers; sensitivity (reserve 10) cuts listed-policy early busts to {sum(v for k,v in a1g2.items() if k!='random')} (from {sum(v for k,v in a1g.items() if k!='random')}) | Optional: stronger on-screen warning when the treasury would fall below the Act 1 cap; no rule change needed | Observe real players' Court spending |
| 3 | The Miser (round 4) is the deadliest single round | Evidence-backed | {int(RS.loc[4,'bankrupt'])} of {int(RS.loc[4,'runs_reaching'])} arrivals ({pc(1-RS.loc[4,'conditional_survival'])}); median entry treasury {BR.loc['miser','treasury_on_entry_median']:.0f} | Mostly a result of low treasury on arrival; consider whether a cushion before round 4 is intended | Re-test after any Act 1 income change |
| 4 | Gold inflates and has no late sink | Evidence-backed (observation); whether it is a *problem* is a design call | median {RS.loc[1,'treasury_start_median']:.0f}→{RS.loc[11,'treasury_start_median']:.0f}; {buckets.iloc[4,2]} of completed runs finish with 51+ | If final gold is meant to matter, add a sink or a score; otherwise leave | Check against how final gold is shown to players |
| 5 | Income Regalia (Mint, Tax, Interest, Patron, Herald) add little survival | Potential | direct gold {RG.loc['mint','direct_gold_per_owned_round']:.1f}–{RG.loc['interest','direct_gold_per_owned_round']:.1f} per round (Herald {RG.loc['herald','direct_gold_per_owned_round']:.1f}); owner completion at round 5 {pc(inc_own.min(),0)}–{pc(inc_own.max(),0)} vs ≈{pc(RG.r5_all_nonowner_completion[inc].mean(),0)} non-owners; Economic group {pc(S.loc['economic','completion_rate'])} vs baseline {pc(base_comp)} | Consider moving their value earlier (Act 1) rather than later | Controlled test: force each Regalia on at round 1 |
| 6 | Wild-making and free-leftover Regalia (and Second Wind) look strongest for survival | Potential | owners at round 5: {pc(hand_own.min(),0)}–{pc(hand_own.max(),0)} completion; Starlight saves ≈{RG.loc['starlight','saved_per_owned_round']:.1f} points per owned round | None yet; selection effects possible | Randomised assignment of each item at round 1 (cleanest test) |
| 7 | Purchasing is not clearly better than not purchasing | Potential | baseline {pc(base_comp)} vs Aggressive {pc(S.loc['aggressive','completion_rate'])}, Defensive {pc(S.loc['defensive','completion_rate'])} (sens. {pc(S2.loc['defensive','completion_rate'])}) | Policy-dependent; a better policy might do much better | Try a stronger (search-based) Court policy |
| 8 | Usurper is hard to beat but rarely kills; Jester interacts with wild-making builds | Evidence-backed (rates); Potential (interaction) | Usurper success {pc(BR.loc['usurper','boss_success_rate'])}, ends {BR.loc['usurper','pct_of_arrivals_ending_at_boss']}% of arrivals; Jester success Aggressive {pc(BG[(BG.boss=='jester')&(BG.group=='aggressive')].success_rate.iloc[0],0)} vs {pc(BG[(BG.boss=='jester')&(BG.group=='defensive')].success_rate.iloc[0],0)} Defensive | None | Test builds head-to-head at the Jester |
| 9 | Early Bird's 3-turn window is met often by the AI | Potential (depends on human speed) | met in {pc(eb_trig,0)} of owned rounds; median player turns per round {med_turns:.0f} | Check on human play before changing | Human turn counts per round |
| 10 | Miser's Vault rarely does anything | Potential | applied {eco['vault_saving_events']} times for {eco['vault_saving_gold_total']} gold in total; price {int(RG.loc['vault','list_price'])} | Possibly the wrong size for AI-sized penalties; humans may be caught with more | Human penalty distribution |
| 11 | Spyglass, Eavesdropper, Scout cannot be evaluated | Not enough evidence | The AI never uses the information | — | Human play study |
| 12 | Redeal, Pickpocket, Fog effects | Not enough evidence | use rules are my heuristics; no direct gold link | — | Better Decree-use policy, or A/B on a fixed hand |

## 9. Limits of this study

- **One player AI.** The player is the opponent AI at full strength every turn, so results are an upper bound on skill. The AI doesn't use hints, peeks or reading of opponents.
- **Rounds are short for the AI** (median {med_turns:.0f} player turns, mean {mean_turns:.1f}; the player goes out in {pc(outrate,0)} of rounds), which matters for turn-based items (Early Bird, Scout, Fog).
- **Court policies are hand-written** and only three of five are "strategies"; each has a parameter (reserve) that visibly moves the result.
- **Association is not causation** for every Regalia comparison (owner selection, survivor bias). The round-5 landmark reduces but does not remove this.
- **Direct-value numbers are counterfactual accounting on the same state** (e.g. Gambler: marginal going-out gold with the item vs. without it for that round), not re-simulations.
- **200 runs per group** gives about ±7 points of uncertainty on any completion rate; the pairwise tests are uncorrected for multiple comparisons.
- Opponent skill tiers and boss skill are as coded; I did not vary them.

## 10. Validation

Headline run: {'all ' + str(len(val)) + ' checks passed' if ok_all else 'FAILURES: ' + ', '.join(v['name'] for v in val if not v['ok'])}. Sensitivity run: {'all ' + str(len(val2)) + ' checks passed' if ok2 else 'FAILURES'}.

{chr(10).join(f"- {'PASS' if v['ok'] else 'FAIL'}: {v['name']}" + (f" ({v['detail']})" if v['detail'] else '') for v in val)}

Not placeholders: every figure above is read from the CSVs next to this file. Charts are drawn from those CSVs by `simulation/analyze.py`.

## 11. Files

`run_results.csv` (one row per run) · `round_results.csv` (one row per round reached, full ledger) · `event_log.csv` (offers, buys, rerolls, sales, Decree uses) · `regalia_results.csv` · `decree_results.csv` · `boss_results.csv` · `boss_by_group.csv` · `strategy_results.csv` · `round_summary.csv` · `regalia_combinations.csv` · `economy_extras.json` · `validation_results.json` · `simulation_config.json` · `simulation_manifest.json` · `charts/`. Sensitivity run: `../2026-11-16-run-002-reserve10/`.

Reproduce: `node simulation/run-sim.js --runs 1000 --out <dir>` then `node simulation/validate.js <dir>`, `python3 simulation/analyze.py <dir>`, `python3 simulation/make_report.py <dir> <sensitivityDir>`.
""")
open(f'{D}/balance_report.md', 'w').write(''.join(R))
man['status'] = 'complete: simulation, validation, analysis and report generated'; man['analysis_files'] = ['strategy_results.csv', 'round_summary.csv', 'regalia_results.csv', 'decree_results.csv', 'boss_results.csv', 'boss_by_group.csv', 'regalia_combinations.csv', 'economy_extras.json', 'validation_results.json', 'balance_report.md', 'charts/*.png']
man['sensitivity_run'] = '../2026-11-16-run-002-reserve10'; json.dump(man, open(f'{D}/simulation_manifest.json', 'w'), indent=1)
print('report written', len(''.join(R)), 'chars')
