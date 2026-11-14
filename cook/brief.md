# Cook brief: Kingsrun desktop

**Target:** MotionSites "Animated Cards" (cook/reference-animated-cards.png): pure black void, luminous glassy cards with real thickness, soft edge light, no clutter, premium and calm.
**Scope:** desktop game table (1366x768 and 1630x1000) and The Run screens (Court, round results, run end, boss table). Phone layout must stay pixel-identical to main (checked with tests/ and the cmp script).
**Rounds:** 5. User reviews stills after each round.
**Branch:** `cook` (not main). Merge to main only on the user's word.

## Bar (score each 1-10, target 8+ on every row before shipping)
| Dimension | What 8+ looks like |
|---|---|
| Composition | One clear focal point (the piles), hand anchored, nothing floating or cramped, balanced margins at both sizes |
| Light | Cards and piles read as lit objects: edge light, soft glow, depth; no flat grey rectangles |
| Colour | Black void + one accent + suit colours; no muddy greys; contrast AA for text |
| Materials | Cards feel like glass/metal with thickness; table surface has subtle depth, not a flat panel |
| Type | Clear hierarchy: display serif for moments, mono for labels, readable sizes at 1366x768 |
| Motion | Tilt, deal and draw feel smooth; nothing janky; respects reduced-motion |
| Run screens | Court, results and end screens match the table's language (same glass, same light) |

## Rules
- No external assets or libraries. Single index.html, offline-first stays.
- Only desktop styles change (inside the (hover:hover) and (min-width:900px) block) unless a fix is shared and phone is re-verified.
- Banned: generic gradient blobs, neon overload, emoji icons, new fonts.
- Tests must stay green (npm test, npm run test:browser).
