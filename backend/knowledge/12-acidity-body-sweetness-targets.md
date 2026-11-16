# Acidity, Body, and Sweetness Targets by Use Case

This is a quick-reference guide for the AI blend generator. When given a prompt describing a coffee use case, these tables map it to numeric profile targets.

## By Coffee Style

| Style                    | Acidity | Body  | Sweetness | Notes                                    |
|--------------------------|---------|-------|-----------|------------------------------------------|
| Espresso (specialty)     | 4.5–6.5 | 7.0–8.5 | 7.0–8.5 | Balanced, works as shot and in milk      |
| Espresso (traditional)   | 2.5–4.5 | 8.0–9.5 | 6.0–8.0 | Bold, low acid, designed for milk drinks |
| Filter / Pour-over       | 6.0–8.5 | 3.5–6.0 | 6.0–8.5 | Bright, clean, terroir-expressive        |
| Cold brew                | 2.0–4.5 | 7.5–9.5 | 5.5–7.5 | Very low acid, full body                 |
| AeroPress (concentrate)  | 4.0–6.5 | 6.0–8.0 | 6.5–8.5 | Flexible; adjust for preference          |
| Moka pot                 | 3.5–5.5 | 7.0–8.5 | 6.0–8.0 | Bold, low-medium acid                    |

---

## By Drinker Preference

| Preference                        | Acidity | Body  | Sweetness |
|-----------------------------------|---------|-------|-----------|
| "I like bold, dark coffee"        | 2.0–4.0 | 8.0–9.5 | 5.5–7.5 |
| "I like fruity, bright coffee"    | 7.0–9.0 | 3.0–5.5 | 7.0–8.5 |
| "I want something chocolatey"     | 3.0–5.5 | 6.5–8.5 | 7.5–9.0 |
| "I prefer balanced, easy to drink"| 5.0–6.5 | 5.5–7.5 | 6.5–8.0 |
| "I have sensitive stomach (acid)" | 1.5–3.5 | 6.0–9.0 | 5.5–7.5 |
| "Sweet, dessert-like"             | 2.5–4.5 | 5.5–7.5 | 8.5–10.0|
| "Floral, delicate, tea-like"      | 7.5–9.5 | 2.5–4.5 | 6.5–8.5 |
| "Nutty, smooth, comforting"       | 3.0–5.0 | 6.0–8.0 | 7.0–9.0 |

---

## By Milk Pairing

When the user specifies a milk-based drink, adjust targets:

| Milk drink               | Acidity target | Body target | Why                                              |
|--------------------------|---------------|-------------|--------------------------------------------------|
| Espresso (black)         | 4.0–7.0       | 6.5–8.5     | Baseline                                         |
| Latte (200ml milk)       | 2.0–4.5       | 7.5–9.0     | Milk amplifies acid; needs high body to show     |
| Flat white (100ml milk)  | 3.0–5.5       | 7.5–9.0     | Less milk than latte but same principle          |
| Cappuccino               | 3.5–5.5       | 7.0–8.5     | Foam texture changes perception                  |
| Cortado (50ml milk)      | 4.5–6.5       | 7.0–8.5     | Small milk ratio, can tolerate more acidity      |
| Oat milk latte           | 2.0–4.0       | 8.0–9.5     | Oat milk's sweetness needs a bold, low-acid base |
| Cold milk / iced latte   | 2.5–4.5       | 7.5–9.5     | Cold dulls sweetness, needs strong base          |

---

## Computed vs. Estimated Profile

### Computed (deterministic)
- Acidity = Σ(percentage_i × bean_acidity_i) / 100
- Body = Σ(percentage_i × bean_body_i) / 100
- Sweetness = Σ(percentage_i × bean_sweetness_i) / 100

These values are mathematically derived from the bean data. They are objective.

### Estimated (AI-inferred)
- Chocolate intensity: estimated based on origin, roast, and processing
- Caramel intensity: estimated based on sweetness, processing, and roast
- Fruitiness: estimated based on acidity, origin, and processing
- Nuttiness: estimated based on body, origin, and roast
- Florality: estimated based on acidity, varietals, and origin

The estimated notes are directional guidance. Display them with a label that makes the AI provenance clear — e.g. "AI estimate" — to maintain honesty with the user.
