# Coffee Blending Principles

A blend combines two or more coffees to achieve a cup profile that is more consistent, complex, or commercially viable than any single origin alone.

## Why Blend?

1. **Consistency**: Single-origin coffees change with each harvest. A blend can be reformulated each season to hit the same target profile.
2. **Complexity**: No single origin covers every dimension. A blend layers a base (body, chocolate), a bridge (balance, sweetness), and a top note (acidity, aroma).
3. **Cost management**: Expensive high-acidity components (Kenyan, Ethiopian Gesha) can be used at 15–25% while the base uses more affordable Brazilian.
4. **Brew-method optimization**: An espresso blend is designed differently from a filter blend.

---

## The Three-Component Framework

Most functional espresso blends follow a three-role structure:

| Role      | % range | What it contributes             | Typical origins         |
|-----------|---------|----------------------------------|-------------------------|
| Base      | 40–65%  | Body, crema, chocolate, sweetness| Brazil, Sulawesi, Sumatra |
| Bridge    | 20–35%  | Balance, clean sweetness, mid notes | Colombia, Guatemala, Peru |
| Top note  | 10–25%  | Acidity, aroma, complexity        | Ethiopia, Kenya, Rwanda  |

This is a guideline, not a rule. Two-component blends (Base + Top) work well for simpler profiles. Some blends use two top-note components for extra complexity.

---

## Percentage Rules

- Percentages must sum to exactly 100.
- Minimum component: 5% (below this, the bean contributes almost nothing to the cup).
- Maximum component: 80% (above this, it is effectively a single origin with a minor addition).
- For 2-component blends: 55–70% base, 30–45% second.
- For 3-component blends: 40–60% base, 20–35% bridge, 10–25% top note.
- For 4-component blends: 35–50% base, 20–30% bridge, 10–20% second bridge or top note, 5–15% accent.
- Blends with more than 5 components are unusual in specialty coffee — complexity tends to become muddled.

---

## Flavor Interactions

**Acidity layering**: Combining a high-acidity Ethiopian (washed) with a low-acidity Brazilian naturally creates medium acidity. The weighted average predicts it well. Example: 60% Brazil (acidity 3.0) + 40% Ethiopia Yirgacheffe (acidity 8.5) = 60% × 3.0 + 40% × 8.5 = 5.2 acidity.

**Body stacking**: A heavy-bodied Sumatra at 20% significantly increases the blend's perceived body, more than a simple weighted average suggests. Heavy Indonesian coffees "pull up" the body of lighter components disproportionately.

**Sweetness**: Natural-processed and honey-processed components increase sweetness. Washed components at light roast also contribute high sweetness. Combining natural Brazil with medium-roast Colombia creates a reliably sweet espresso.

**Conflict points**: Ethiopian floral/citrus notes can clash with heavy Indonesian earth. Keep Indonesian components under 30% if using an Ethiopian brightener above 20%.

---

## Targeted Profile Calculation

The computed profile (acidity, body, sweetness) is calculated as:

```
computed_acidity   = Σ (percentage_i / 100) × bean_acidity_i
computed_body      = Σ (percentage_i / 100) × bean_body_i
computed_sweetness = Σ (percentage_i / 100) × bean_sweetness_i
```

This gives an objective starting point. Actual cup performance may differ due to roast interactions and brew variables, but this calculation is reliable for blend design and comparison.

---

## Adjusting for Brewing Method

**Espresso**: Prioritize body (target ≥ 6.5) and sweetness (target ≥ 6.0). Acidity can be moderate (4.0–6.5). High acidity (>7.0) becomes harsh under pressure.

**Espresso with milk (flat white, latte, cortado)**: Lower acidity target (3.5–5.5) — milk amplifies sour notes. Higher body and sweetness to cut through the dairy.

**Filter / pour-over**: Higher acidity is desirable (6.0–8.5). Body can be lower (4.0–6.0). Sweetness target 5.5–7.5.

**Cold brew**: Target low-medium acidity (3.5–5.5), very high body (7.0+). Use natural process and medium-dark roast components.

---

## Roast Matching

All components in a blend are typically roasted together. When beans have significantly different densities (e.g., dense high-grown Ethiopian vs. low-grown Brazilian), consider whether the target roast level suits all components. The denser bean will be under-developed at the same color as the less dense bean. For high-precision blending, roasting components separately and blending post-roast gives more control.
