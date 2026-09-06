# Pitch converter reference

Read this only when classifying is ambiguous or a rewrite needs a sharper pattern. Default rewrite still uses **one** of SCR or Pyramid.

## When to reach for which

| Pattern | Reach for it when |
| --- | --- |
| **SCR** | Framing a problem before a recommendation or ask |
| **Pyramid Principle** | Structuring any explanation or recommendation |
| **Cialdini (checklist)** | After drafting: "any social proof? authority? small commitment path?" — apply 0–2, never all six |
| **MEDDIC / Challenger** | Later: qualifying a deal or teaching a customer a new problem frame. Not the default rewrite. |

Pick one framework to practice until it is automatic, then layer the next. Applying all of them in one message reads as scripted.

## SCR

- **Situation:** shared, uncontroversial context (one or two sentences).
- **Complication:** what changed or what is now at risk.
- **Resolution:** the ask or the action.

The first sentence of the user-facing rewrite is still the point (the Resolution), not the Situation. Use Situation and Complication as support after the point.

## Pyramid Principle

- Lead with the answer / recommendation.
- Group supporting arguments under that answer (usually 2–4).
- Evidence lives under the groups, not before the answer.

## Cialdini (post-draft checklist)

Run after the draft. Add at most 1–2 that already fit. Do not mention these names in the rewrite.

1. Reciprocity — a useful fact or concession before the ask
2. Commitment/consistency — a small next step they can say yes to
3. Social proof — peers, teams, or similar cases already doing it
4. Authority — a standard, metric, or named source that warrants the claim
5. Liking — shared goal or constraint, not flattery
6. Scarcity — a real deadline or capacity limit only if true

## MEDDIC / Challenger (later, not default)

- **MEDDIC:** Metrics, Economic buyer, Decision criteria, Decision process, Identify pain, Champion. Use when the draft is a sales/qualification conversation, not a Slack/status rewrite.
- **Challenger:** teach a new insight, tailor to the stakeholder, take control of the next step. Use when the goal is to reframe how the audience sees the problem.

## Before / after

**Before (hedged, build-a-case):**

We've been looking at latency on the checkout path for a while and there are a few things that might be contributing. I think maybe if we moved tracing to a dedicated collector it could possibly help reduce p99 by up to around 40% in some cases, though we'd need to validate. Happy to discuss if people have thoughts.

**After (point first, certain, short):**

We should move checkout tracing to a dedicated collector this quarter. p99 on that path is the customer-visible bottleneck, and isolating collection is how we cut it by ~40%. Reply in thread if you want the rollout sequenced behind the freeze.

**First-sentence check:** someone who only heard the first sentence knows the ask (move tracing this quarter).
