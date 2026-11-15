#!/usr/bin/env python3
"""Writes phase2_report.md from the tables in <dir>/tables. All numbers computed; interpretation is mine. Usage: python3 simulation/make_report_phase2.py <dir>"""
import sys, json
import numpy as np, pandas as pd
D = sys.argv[1]; T = f'{D}/tables/'
e1 = pd.read_csv(T + 'e1_summary.csv', index_col=0); e1p = pd.read_csv(T + 'e1_paired.csv'); e2s = pd.read_csv(T + 'e2_summary.csv', index_col=0); e2 = pd.read_csv(T + 'e2_paired.csv')
e3 = pd.read_csv(T + 'e3_summary.csv', index_col=0); e3p = pd.read_csv(T + 'e3_paired.csv'); e4 = pd.read_csv(T + 'e4_summary.csv'); e4p = pd.read_csv(T + 'e4_paired.csv')
e5 = pd.read_csv(T + 'e5_summary.csv', index_col=0); e5p = pd.read_csv(T + 'e5_paired.csv'); val = json.load(open(f'{D}/validation_results.json'))
cfgs = {e: json.load(open(f'{D}/config_{e}.json'))['experiments'][e] for e in ('e1', 'e2', 'e3', 'e4', 'e5')}
pct = lambda x, d=1: f'{100 * x:.{d}f}%'; pts = lambda x, d=1: f'{100 * x:+.{d}f}'
md = lambda df, f='g': df.to_markdown(index=False, floatfmt=f)
def pr(df, cond, ref, metric): r = df[(df.cond == cond) & (df.ref == ref) & (df.metric == metric)].iloc[0]; return r
def ci(r, col, scale=100, d=1, unit=''): return f"{scale * r[col]:+.{d}f}{unit} ({scale * r['ci_lo']:+.{d}f} to {scale * r['ci_hi']:+.{d}f})"

# ---------- E1 ----------
rows = []
for court, label in (('none', 'No Court purchases'), ('aggressive', 'Aggressive Court')):
    for k, nm in (('control', 'No Gambler (control)'), ('g3_15', 'x3 out / x1.5 penalty (current)'), ('g2_15', 'x2 / x1.5'), ('g25_2', 'x2.5 / x2')):
        s = e1.loc[f'{court}|{k}']
        d = '' if k == 'control' else ci(pr(e1p, f'{court}|{k}', f'{court}|control', 'completed'), 'diff_completed')
        rows.append({'Court': label, 'Variant': nm, 'Completion': pct(s.completion), 'vs control, points (95% CI)': d, 'Bankrupt in rounds 2-3': pct(s.early_bust_r2_3),
            'Median final treasury (completed)': f'{s.median_final_treasury_completed:.0f}', '90th pct': f'{s.p90_final_treasury_completed:.0f}',
            'Gambler net gold per owned round': '' if k == 'control' else f'{s.gambler_net_per_owned_round:+.1f}', 'Player goes out': pct(s.out_rate)})
t_e1 = pd.DataFrame(rows)
g3n = e1.loc['none|g3_15']; g3a = e1.loc['aggressive|g3_15']; g2a = e1.loc['aggressive|g2_15']; g25a = e1.loc['aggressive|g25_2']; g2n = e1.loc['none|g2_15']; g25n = e1.loc['none|g25_2']
# ---------- E2 ----------
price = {'commoner': 22, 'seventh': 24, 'jewels': 24, 'fool': 15, 'twin': 16, 'starlight': 13, 'lowtide': 13, 'purse': 9, 'vault': 12, 'spyglass': 10, 'eaves': 5, 'herald': 9, 'earlybird': 6, 'mint': 6, 'tax': 9, 'interest': 10, 'patron': 10, 'secondwind': 9, 'gambler': 4}
q = e2.sort_values('diff_completed', ascending=False).copy(); q['price'] = q.cond.map(price)
t_e2 = pd.DataFrame({'Regalia (forced at round 1)': q.cond, 'Price': q.price, 'Completion': (q.completion * 100).round(1).astype(str) + '%', 'vs control, points (95% CI)': [f"{100*a:+.1f} ({100*b:+.1f} to {100*c:+.1f})" for a, b, c in zip(q.diff_completed, q.ci_lo, q.ci_hi)],
    'p (Holm-adj.)': q.p_holm.map(lambda x: '<0.001' if x < .001 else f'{x:.3f}'), 'Rounds reached': q.diff_rounds_reached.map(lambda x: f'{x:+.2f}'), 'Penalties paid per run': q.diff_penalties_paid.map(lambda x: f'{x:+.1f}'),
    'Gold generated per run': q.diff_gold_generated.map(lambda x: f'{x:+.0f}'), 'Points per gold': (q.diff_completed * 100 / q.price).round(2)})
ctl = e2s.loc['control']; null = e2.set_index('cond').loc[['spyglass', 'eaves']]
top4 = q.head(4); noise = max(abs(null.ci_lo.min()), abs(null.ci_hi.max())) * 100
# ---------- E3 ----------
rows = []
for court in ('economic', 'aggressive', 'defensive'):
    for rs in (5, 10, 15):
        s = e3.loc[f'{court}|{rs}']; pe = e3p[(e3p.cond == f'{court}|{rs}') & (e3p.ref == f'{court}|5') & (e3p.metric == 'completed')]; pb = e3p[(e3p.cond == f'{court}|{rs}') & (e3p.metric == 'completed_vs_baseline')].iloc[0]
        rows.append({'Court policy': court, 'Reserve': rs, 'Bankrupt in rounds 2-3': pct(s.early_bust_r2_3), 'Completion': pct(s.completion), 'vs reserve 5 (points, 95% CI)': '' if rs == 5 else f"{100*pe.iloc[0].diff_completed:+.1f} ({100*pe.iloc[0].ci_lo:+.1f} to {100*pe.iloc[0].ci_hi:+.1f})",
            'vs no-purchase baseline (points)': f"{100*pb.diff_completed:+.1f}", 'Mean round reached': f'{s.mean_round_reached:.2f}', 'Median final treasury': f'{s.median_final_treasury_completed:.0f}'})
t_e3 = pd.DataFrame(rows)
# ---------- E4 ----------
order = ['none', 'twin', 'fool', 'income', 'defense', 'freeleft', 'wilds', 'wilds_fool', 'wilds_fool_star']
bdesc = {'none': 'no Regalia', 'twin': 'Twin Crowns', 'fool': 'Court Fool', 'income': 'Patron + Interest + Tax', 'defense': 'Second Wind + Vault + Starlight', 'freeleft': 'Starlight + Low Tide + Heavy Purse', 'wilds': 'Commoner + Seventh + Crown Jewels', 'wilds_fool': 'the three wilds + Court Fool', 'wilds_fool_star': 'three wilds + Fool + Starlight'}
def e4tab(boss):
    on = e4[(e4.boss == boss) & (e4.boss_on == 1)].set_index('build'); off = e4[(e4.boss == boss) & (e4.boss_on == 0)].set_index('build'); rows = []
    for b in order:
        eff = e4p[(e4p.boss == boss) & (e4p.cond == b) & (e4p.metric == 'beat_boss_effect')].iloc[0]; peff = e4p[(e4p.boss == boss) & (e4p.cond == b) & (e4p.metric == 'penalty_paid_boss_effect')].iloc[0]
        vs = '' if b == 'none' else (lambda r: f"{100*r.diff_beat:+.1f} ({100*r.ci_lo:+.1f} to {100*r.ci_hi:+.1f})")(e4p[(e4p.boss == boss) & (e4p.boss_on == 1) & (e4p.cond == b) & (e4p.metric == 'beat')].iloc[0])
        rows.append({'Build': bdesc[b], 'Success with boss': pct(on.loc[b, 'beat']), 'vs no-Regalia build (points, 95% CI)': vs, 'Same round, boss off': pct(off.loc[b, 'beat']), 'Boss effect on success (points)': f"{100*eff.diff_beat:+.1f}",
            'Penalty paid with boss': f"{on.loc[b,'pen']:.1f}", 'Boss effect on penalty (gold)': f"{peff.diff_penalty_paid:+.1f}", 'Bankrupt (40 gold in)': pct(on.loc[b, 'bust'])})
    return pd.DataFrame(rows)
tj, tm, tu = e4tab('jester'), e4tab('miser'), e4tab('usurper')
jw = e4[(e4.boss == 'jester') & (e4.boss_on == 1)].set_index('build')
# ---------- E5 ----------
pols = ['best', 'deckonly', 'skill80', 'deckonly80', 'skill55', 'skill30']; pn = {'best': 'Best play (Phase 1)', 'deckonly': 'Never takes the discard pile', 'skill80': 'Slips 20% of the time', 'deckonly80': 'No discard pile + slips 20%', 'skill55': 'Slips 45% of the time', 'skill30': 'Slips 70% of the time'}
rows = []
for p in pols:
    r = {'Player': pn[p]}
    for c in ('none', 'defensive', 'aggressive', 'economic'): r[{'none': 'No purchases', 'defensive': 'Defensive', 'aggressive': 'Aggressive', 'economic': 'Economic'}[c]] = pct(e5.loc[f'{c}|{p}', 'completion'])
    r['Goes out'] = pct(e5.loc[f'none|{p}', 'out_rate']); r['Turns per round'] = f"{e5.loc[f'none|{p}','turns_per_round']:.1f}"; rows.append(r)
t_e5 = pd.DataFrame(rows)
g = lambda c, p: e5.loc[f'{c}|{p}', 'completion']
vs_rows = []
for c in ('defensive', 'aggressive', 'economic'):
    for p in ('best', 'skill80', 'skill55', 'skill30'):
        vs_rows.append({'Player': pn[p], 'Court': c, 'Completion': pct(g(c, p)), 'No purchases': pct(g('none', p)), 'Gain from buying (points)': f"{100*(g(c,p)-g('none',p)):+.1f}"})
t_e5b = pd.DataFrame(vs_rows)
ev = {e: cfgs[e]['N'] for e in cfgs}
R = []; w = R.append
w(f"""# The Run — Phase 2: Controlled Balance Experiments

*Built on the Phase 1 baseline (`../2026-11-16-run-001/balance_report.md`). Same unmodified game code; rule variants live only inside the simulator. Every number is computed from the CSVs in this folder.*

## 1. Summary

| # | Question | Answer |
|---|---|---|
| 1 | Gambler's Hand ×3/×1.5 vs ×2/×1.5 vs ×2.5/×2 | Its value depends on how often the player goes out. Alone (player goes out {pct(g3n.out_rate,0)}), the current version adds {pts(pr(e1p,'none|g3_15','none|control','completed').diff_completed)} points of completion (not significant); both weaker versions *hurt* ({pts(pr(e1p,'none|g2_15','none|control','completed').diff_completed)} and {pts(pr(e1p,'none|g25_2','none|control','completed').diff_completed)}). With the Aggressive Court (goes out {pct(g3a.out_rate,0)}) it is strong: +{100*pr(e1p,'aggressive|g3_15','aggressive|control','completed').diff_completed:.1f} points and a median final treasury of {g3a.median_final_treasury_completed:.0f}, against {g2a.median_final_treasury_completed:.0f} for ×2/×1.5 and {g25a.median_final_treasury_completed:.0f} for ×2.5/×2. |
| 2 | Each Regalia forced at round 1 | The three wild-rank Regalia and Court Fool are by far the strongest ({', '.join(f"{r.cond} {100*r.diff_completed:+.0f}" for r in top4.itertuples())} points over a {pct(ctl.completion,0)} control). Income Regalia help much more when owned from round 1 (Interest {pts(e2.set_index('cond').loc['interest','diff_completed'],0)}, Patron {pts(e2.set_index('cond').loc['patron','diff_completed'],0)}) than Phase 1's after-the-fact comparison suggested. Gambler's Hand, Royal Mint, Spyglass and Eavesdropper show no detectable effect. |
| 3 | Court reserve 5 / 10 / 15 | A reserve of 10 cuts bankruptcies in rounds 2–3 from {pct(e3.loc['aggressive|5','early_bust_r2_3'],0)}/{pct(e3.loc['defensive|5','early_bust_r2_3'],0)}/{pct(e3.loc['economic|5','early_bust_r2_3'],0)} (Aggressive/Defensive/Economic) to {pct(e3.loc['aggressive|10','early_bust_r2_3'],0)}/{pct(e3.loc['defensive|10','early_bust_r2_3'],0)}/{pct(e3.loc['economic|10','early_bust_r2_3'],0)} and lifts completion modestly; 15 removes nearly all early bankruptcies but adds little more completion. |
| 4 | Bosses with matched builds | Against the Jester, the three wild-rank Regalia make the boss almost irrelevant ({pct(jw.loc['wilds','beat'],0)} success vs {pct(jw.loc['none','beat'],0)} with no Regalia). The Usurper is the one boss that really bites ({100*e4p[(e4p.boss=='usurper')&(e4p.cond=='none')&(e4p.metric=='beat_boss_effect')].iloc[0].diff_beat:+.0f} points of success, {e4p[(e4p.boss=='usurper')&(e4p.cond=='none')&(e4p.metric=='penalty_paid_boss_effect')].iloc[0].diff_penalty_paid:+.1f} gold) and it switches Court Fool off completely. |
| 5 | Weaker card play | Everything gets much harder, and **buying matters far more for weaker players**. A player who slips 45% of the time completes {pct(g('none','skill55'),0)} with no purchases, {pct(g('defensive','skill55'),0)} with the Defensive Court and {pct(g('aggressive','skill55'),0)} with the Aggressive Court. Phase 1's "doing nothing is strong" holds only for best play. |

**How to read the rest.** Differences between conditions are *paired*: every condition replays the same {ev['e1']:,} (Exp. 1, 3), {ev['e2']:,} (Exp. 2), {ev['e5']:,} (Exp. 5) or {ev['e4']:,} (Exp. 4) deals, so intervals are much tighter than the Phase 1 group comparisons. Nothing here has been applied to the game.

## 2. Method and caveats common to all experiments

- **Paired seeds.** Within an experiment every condition uses the same seed list, so the opening deal is identical. After the first Court the random streams can drift apart (a purchase changes how many random numbers the Court uses), so pairing is exact only for the first deal. To measure how much this alone matters I included two Regalia that do nothing in this simulation (Spyglass and Eavesdropper, which only change what a human can see). They differ from the control by {pts(null.diff_completed.iloc[0])} points (95% CI {pts(null.ci_lo.iloc[0])} to {pts(null.ci_hi.iloc[0])}). **Treat Experiment 2 differences smaller than about ±{noise:.0f} points as noise.**
- **Same game rules, same AI.** Experiments 1–4 use the Phase 1 best-play AI. Experiment 5 relaxes that.
- **Variants.** Gambler variants patch two numbers in an in-memory copy of the page code (×3 → ×N on going-out gold, ×1.5 → ×M on the penalty); fractional going-out gold is rounded down. `index.html` is unchanged.
- **Final treasury** in paired comparisons counts bankrupt runs as 0, so it mixes survival and gold. Median final treasury in the tables is over completed runs only.
- **Single-item tests are marginal effects at round 1 with nothing else bought.** They don't tell you how items combine.

## 3. Experiment 1 — Gambler's Hand variants

Gambler's Hand forced onto every run at round 1 ({ev['e1']:,} paired deals per row), in two contexts: no other purchases at all, and the Aggressive Court policy (which can also buy wild-rank Regalia, Court Fool and Early Bird).

{md(t_e1)}

![](charts/e1_gambler.png)

- **Why the result flips with context.** Gambler's Hand pays on the rounds where you go out and costs on the rounds where you don't. With no other items the player goes out about {pct(g3n.out_rate,0)} of rounds, so the {g3n.gambler_extra_penalty_per_owned_round:.1f} gold of extra penalty per round nearly cancels the {g3n.gambler_out_gold_per_owned_round:.1f} gold of bonus (net {g3n.gambler_net_per_owned_round:+.1f}). With Aggressive purchases the player goes out {pct(g3a.out_rate,0)} of rounds and the same item nets {g3a.gambler_net_per_owned_round:+.1f}.
- **Weaker multipliers.** ×2/×1.5 nets {g2n.gambler_net_per_owned_round:+.1f} alone and {g2a.gambler_net_per_owned_round:+.1f} with Aggressive purchases; ×2.5/×2 nets {g25n.gambler_net_per_owned_round:+.1f} and {g25a.gambler_net_per_owned_round:+.1f}. Doubling the penalty multiplier is more damaging than trimming the bonus: ×2.5/×2 is worse than ×2/×1.5 in both contexts.
- **Inflation.** In the Aggressive context ×2/×1.5 lowers the median final treasury from {g3a.median_final_treasury_completed:.0f} to {g2a.median_final_treasury_completed:.0f} (still above the {e1.loc['aggressive|control','median_final_treasury_completed']:.0f} with no Gambler) while keeping completion above the control ({pts(pr(e1p,'aggressive|g2_15','aggressive|control','completed').diff_completed)} points, not significant).
- **Early busts.** With the Aggressive Court the item raises bankruptcies in rounds 2–3 slightly ({pct(e1.loc['aggressive|control','early_bust_r2_3'])} → {pct(g3a.early_bust_r2_3)} / {pct(g2a.early_bust_r2_3)} / {pct(g25a.early_bust_r2_3)}), because heavier penalties arrive before the bonus does.

## 4. Experiment 2 — each Regalia forced at round 1

Each Regalia given free at round 1 to {ev['e2']} matched deals, no other purchases, compared with the same deals and no Regalia. Control completion {pct(ctl.completion)}, penalty {ctl.penalty_paid_per_round:.1f} gold per round, median final treasury {ctl.median_final_treasury_completed:.0f}.

{md(t_e2)}

![](charts/e2_forest.png)

*Points per gold = completion gain per gold of list price. Holm adjustment covers the 19 comparisons.*

- **Strongest, in absolute terms:** the wild-rank Regalia (Crown Jewels, Seventh Heaven, Commoner's Crown) and Court Fool, each worth about {100*q.head(4).diff_completed.min():.0f}–{100*q.head(4).diff_completed.max():.0f} points. Starlight and Low Tide follow (about {100*e2.set_index('cond').loc['lowtide','diff_completed']:.0f}–{100*e2.set_index('cond').loc['starlight','diff_completed']:.0f}).
- **Best per gold spent:** {', '.join(f"{r['Regalia (forced at round 1)']} ({r['Points per gold']})" for _, r in t_e2.sort_values('Points per gold', ascending=False).head(4).iterrows())} points per gold. **Worst per gold among items that work:** Herald ({t_e2[t_e2['Regalia (forced at round 1)']=='herald']['Points per gold'].iloc[0]}) and Royal Mint (not distinguishable from zero).
- **Income Regalia work when owned early** (Interest, Patron, Tax: +11 to +16 points). Phase 1 saw them as weak because they're bought later by runs that already have the gold; this experiment removes that selection.
- **Gambler's Hand alone** is {pts(e2.set_index('cond').loc['gambler','diff_completed'])} points with an interval spanning zero: consistent with Experiment 1.
- **Second Wind** adds {pts(e2.set_index('cond').loc['secondwind','diff_completed'],0)} points although it saves no penalty gold on average: it simply converts one bankruptcy into a continuation.

## 5. Experiment 3 — Court reserve

Same deals, three listed-item Court policies, reserve (gold the policy must keep after paying) 5, 10 or 15; {ev['e3']:,} paired runs per row. A free boss-bounty pick ignores the reserve.

{md(t_e3)}

![](charts/e3_reserve.png)

- **Early bankruptcies fall steadily** as the reserve rises (reserve 10: about a 6–10 point drop; reserve 15: about a 7–11 point drop), for all three policies.
- **Completion improves less**, and not always significantly: Economic gains {pts(pr(e3p.rename(columns={'court':'c'}),'economic|15','economic|5','completed').diff_completed)} points at 15; Aggressive peaks at 10 ({pts(pr(e3p,'aggressive|10','aggressive|5','completed').diff_completed)}); Defensive gains {pts(pr(e3p,'defensive|10','defensive|5','completed').diff_completed)} / {pts(pr(e3p,'defensive|15','defensive|5','completed').diff_completed)} at 10 / 15 (neither significant).
- **A bigger reserve also means buying fewer or later items**, which shows up as a lower final treasury for Aggressive ({e3.loc['aggressive|5','median_final_treasury_completed']:.0f} → {e3.loc['aggressive|15','median_final_treasury_completed']:.0f}).
- **With 1,000 paired deals, Aggressive and Defensive beat the no-purchase baseline at every reserve** (+6 to +10 points), where Phase 1's 200-run comparison was inconclusive. Economic stays well below it at every reserve.

## 6. Experiment 4 — bosses with matched builds

Single-round encounters: each deal is played at the boss round with a fixed 40 gold, with each build, **boss on and boss off** (the same round number with the boss rule removed; seat 1 then plays at the normal tier rather than boss skill, so "boss off" isn't a perfect control). {ev['e4']:,} deals per cell. "Success" is the player scoring strictly less than seat 1, the game's own boss test.

### The Jester (round 8)

{md(tj)}

![](charts/e4_bosses.png)

- **The Jester itself is mild:** with no Regalia it lowers success by {abs(100*e4p[(e4p.boss=='jester')&(e4p.cond=='none')&(e4p.metric=='beat_boss_effect')].iloc[0].diff_beat):.1f} points and adds {e4p[(e4p.boss=='jester')&(e4p.cond=='none')&(e4p.metric=='penalty_paid_boss_effect')].iloc[0].diff_penalty_paid:.1f} gold to the bill.
- **Extra wild ranks neutralise it** (success {pct(jw.loc['wilds','beat'],0)}; boss effect about zero; bill under 1 gold). The Jester changes the wild rank each turn but cannot take away a fixed wild rank.
- **Free-leftover and defensive builds do not help the Jester fight** (Starlight/Low Tide/Purse and Second Wind/Vault/Starlight are {pts(e4p[(e4p.boss=='jester')&(e4p.boss_on==1)&(e4p.cond=='freeleft')&(e4p.metric=='beat')].iloc[0].diff_beat)} and {pts(e4p[(e4p.boss=='jester')&(e4p.boss_on==1)&(e4p.cond=='defense')&(e4p.metric=='beat')].iloc[0].diff_beat)} points on success), because they make leftovers cheaper rather than helping you go out; they do cut the bill.

### The Miser (round 4)

{md(tm)}

### The Usurper (round 11)

{md(tu)}

- **The Usurper is the only boss with a large effect** ({abs(100*e4p[(e4p.boss=='usurper')&(e4p.cond=='none')&(e4p.metric=='beat_boss_effect')].iloc[0].diff_beat):.0f} points of success even for builds that dominate the others).
- **Court Fool is dead against the Usurper** (identical results to no Regalia): the code doesn't deal the extra Joker that round.
- **The income build is identical to no Regalia in a single round**, as it must be; its value is gold between rounds, not card play.

## 7. Experiment 5 — weaker card play

The player's decisions are degraded using the game's own computer-level mechanism ("slips" = with that probability the move is replaced by a random one) and one extra policy, never taking the discard pile. {ev['e5']} paired runs per cell. These are **illustrative stand-ins, not measured human behaviour**: I have no data on how people actually play.

{md(t_e5)}

Gain from buying, by player quality:

{md(t_e5b)}

![](charts/e5_players.png)

- **Completion falls quickly** as play weakens: with no purchases from {pct(g('none','best'),0)} (best) to {pct(g('none','skill80'),0)} (slips 20%), {pct(g('none','skill55'),0)} (45%), {pct(g('none','skill30'),0)} (70%). Even a 20% slip rate costs {100*(g('none','best')-g('none','skill80')):.0f} points with no purchases and about {100*(g('defensive','best')-g('defensive','skill80')):.0f}–{100*(g('aggressive','best')-g('aggressive','skill80')):.0f} with the Defensive or Aggressive Court.
- **Never taking the discard pile costs relatively little** ({pts(g('none','deckonly')-g('none','best'),0)} points with no purchases) but makes rounds longer ({e5.loc['none|deckonly','turns_per_round']:.1f} vs {e5.loc['none|best','turns_per_round']:.1f} turns).
- **Purchases protect weaker players.** At 45% slips, Aggressive purchases are worth {pts(g('aggressive','skill55')-g('none','skill55'),0)} points and Defensive {pts(g('defensive','skill55')-g('none','skill55'),0)}, against {pts(g('aggressive','best')-g('none','best'),0)} and {pts(g('defensive','best')-g('none','best'),0)} for best play. Economic remains the weakest policy at every skill level.
- **Early bankruptcies increase with weaker play** under the same reserve of 5 (Defensive {pct(e5.loc['defensive|best','early_bust_r2_3'],0)} → {pct(e5.loc['defensive|skill55','early_bust_r2_3'],0)} at 45% slips), which strengthens the case for Experiment 3's larger reserve for human players.
- **Turn-based items** shift with play quality: the player goes out in fewer rounds ({pct(e5.loc['aggressive|best','out_rate'],0)} → {pct(e5.loc['aggressive|skill55','out_rate'],0)} with the Aggressive Court), which weakens going-out income (Gambler's Hand, Herald, Early Bird).

## 8. What changes from Phase 1

| Phase 1 said | Phase 2 shows |
|---|---|
| Income Regalia add little survival (Potential) | They help clearly when owned from round 1 (Interest, Patron, Tax +11 to +16 points). Phase 1's comparison was confounded by timing. |
| Doing nothing is as good as buying (Potential) | True only for best play. At 45% slips, Aggressive purchases are worth {pts(g('aggressive','skill55')-g('none','skill55'),0)} points and Defensive {pts(g('defensive','skill55')-g('none','skill55'),0)}; Economic still adds nothing. |
| Gambler's Hand is underpriced (Evidence-backed) | Narrowed: very strong with out-rate boosters, roughly neutral alone, and negative at weaker multipliers. The problem is its synergy and the gold surplus it produces, not its stand-alone strength. |
| Jester interacts with wild builds (Potential) | Confirmed and sharpened: three wild-rank Regalia remove the Jester's effect. |
| Early deaths come from low reserves (Evidence-backed) | Confirmed with a dose-response (5 → 10 → 15). |

## 9. Findings and options (nothing applied)

| # | Finding | Class | Evidence | Option to consider | Follow-up |
|---|---|---|---|---|---|
| 1 | Wild-rank Regalia and Court Fool dominate everything else | Evidence-backed | +{100*q.head(4).diff_completed.min():.0f} to +{100*q.head(4).diff_completed.max():.0f} points each at round 1; boss rounds, success ~{pct(jw.loc['wilds','beat'],0)} vs {pct(jw.loc['none','beat'],0)} at the Jester | Reprice, limit stacking, or accept as the "power" tier | Test stacked wilds with a mid-run purchase rather than round 1 |
| 2 | Herald, Royal Mint and Gambler's Hand (alone) give little survival per gold | Evidence-backed (single-item, round 1) | below ~1 point per gold, Mint indistinguishable from zero | Consider re-pricing or strengthening | Re-test after changes |
| 3 | Gambler's Hand ×2/×1.5 would cut the gold surplus by about a third in Aggressive runs but make it a trap when bought alone | Evidence-backed (effects), design judgement (whether it matters) | Experiment 1 | Keep ×3 if the surplus is acceptable; otherwise soften the bonus but leave the penalty at ×1.5 or lower (doubling the penalty hurt most) | Try ×2/×1.25 and ×2.5/×1.5 |
| 4 | A reserve of about 10 is the sweet spot for buying policies | Evidence-backed | Experiment 3 | Show a warning below 10 after a purchase in rounds 1–3 | Human Court spending data |
| 5 | The Usurper turns Court Fool off and has by far the largest boss effect | Evidence-backed | Experiment 4 | Confirm it is intended | — |
| 6 | The Jester is trivial for wild-rank builds and mild for others | Evidence-backed | Experiment 4 | Optional: let the Jester also affect fixed wild ranks | Test the change at the Jester |
| 7 | Buying matters much more for weaker players, so all balance numbers depend on assumed skill | Evidence-backed (that it depends); **Not enough evidence** for what real players are like | Experiment 5 | Collect real play data (turn decisions, out rates) to calibrate | Log anonymised decisions in the app |
| 8 | Information-only items still cannot be evaluated | Not enough evidence | no effect in these runs | — | Human study |

## 10. Limits

- Weak-play policies are stand-ins; real people differ in *which* mistakes they make, not just how often.
- Pairing is exact only for the first deal (see §2); intervals are conservative for that reason but not exact.
- Marginal single-item effects do not predict combinations.
- Boss tests start at the boss round with 40 gold, so they say nothing about arrival state; Phase 1 covers that.
- Court policies are still my heuristics (reserve aside).
- p-values are exact McNemar tests on paired completions; Experiment 2 is Holm-adjusted, the others are not adjusted for multiple comparisons.

## 11. Validation

{chr(10).join(f"- {'PASS' if v['ok'] else 'FAIL'}: {v['name']}" + (f" ({v['detail']})" if v['detail'] else '') for v in val)}

## 12. Files

`e1_runs.csv`/`e1_rounds.csv` … `e5_*` (raw per-run and per-round records for each experiment), `e4_encounters.csv`, `tables/*.csv` (summaries and paired comparisons with confidence intervals), `charts/*.png`, `config_e*.json`, `validation_results.json`.

Reproduce: `node simulation/experiments.js all --out <dir>` → `python3 simulation/analyze_phase2.py <dir>` → `node simulation/validate_phase2.js <dir>` → `python3 simulation/make_report_phase2.py <dir>`.
""")
open(f'{D}/phase2_report.md', 'w').write(''.join(R)); print('written', len(''.join(R)))
