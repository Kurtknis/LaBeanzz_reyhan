# Feedback Loop and Taste Preferences

## Purpose

The feedback loop allows the AI blend generator to adjust its recommendations based on what a specific owner has tasted and rated. This is not machine learning — it is structured retrieval combined with rule-based constraint derivation.

## How It Works

1. **Feedback storage**: After an owner brews a blend, they submit ratings (1–5 scale) for overall, flavor, body, acidity, and sweetness, along with the brew context (espresso, filter, milk) and an optional comment.

2. **Comment indexing**: The comment is embedded and stored in `knowledge_chunks` with the owner's ID. This makes it retrievable as context for future blend generations.

3. **Preference derivation (rule-based)**:
   - If an owner repeatedly rates acidity low (1–2) for milk drinks, derive the constraint: `milk.acidity_max = 4.0`.
   - If an owner repeatedly rates sweetness high for filter, derive: `filter.sweetness_min = 7.0`.
   - These are stored in `owner_profiles.taste_adjustments` as JSON.

4. **Constraint injection**: When generating a blend, the system reads taste_adjustments and adds hard constraints to the prompt. Example: "For a milk-based espresso, use only beans with acidity below 4.5. This constraint comes from the owner's past feedback."

5. **Applied feedback listing**: The generator must list which constraints were applied in the `applied_feedback` field of its output.

## Brew Context Mapping

| Brew context | Maps to blend style    |
|-------------|------------------------|
| `espresso`  | Espresso (black)       |
| `filter`    | Filter / pour-over     |
| `milk`      | Milk-based espresso    |

## Thresholds for Constraint Derivation

A single low rating does not create a constraint — it might be a bad batch or brewing error. These thresholds are used:

- 3+ ratings of acidity ≤ 2 for the same brew_context → set `acidity_max` for that context
- 3+ ratings of acidity ≥ 4 for the same brew_context → remove any acidity_max constraint
- 3+ ratings of sweetness ≤ 2 for the same brew_context → set `sweetness_min` for that context
- 3+ ratings of body ≤ 2 for the same brew_context → set `body_min` for that context

The constraints are soft ceilings/floors on the selection pool — beans outside the range are filtered out during candidate selection, not just penalized.

## Honesty Constraint

**Never claim machine learning.** The UI copy must say:
- "Adjusted using your previous feedback" ✓
- "Based on your taste history" ✓
- "The AI learned from your data" ✗
- "Our model was retrained on your preferences" ✗

The system is retrieval + SQL aggregation + rule-based thresholds. This is what it is, and the product is better for being honest about it.
