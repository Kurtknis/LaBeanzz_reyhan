# Blend Validation Rules

This document defines the hard rules that every AI-generated blend must pass before it is returned to the user.

## Structural Rules (enforced in code, never waived)

1. **Percentage sum = 100 exactly.** Integer percentages only. Even rounding errors are rejected.
2. **Component count: 2–5 beans.** Fewer than 2 is a single origin, not a blend. More than 5 creates unmanageable complexity.
3. **Minimum percentage per bean: 5%.** A bean below 5% contributes too little to the cup to justify its presence.
4. **Maximum percentage per bean: 85%.** Above 85% it is effectively a single origin.
5. **No duplicate beans.** Each coffee_bean_id must appear exactly once.
6. **All bean IDs must exist in the candidate set** that was sent to the model in the prompt. The model cannot invent beans.
7. **All beans must have status AVAILABLE or LOW_STOCK** at the time of generation. OUT_OF_STOCK and RESERVED beans cannot be used.

## Quality Rules (checked in code)

8. **Blend name: 3–60 characters.** No HTML, no markdown, plain text only.
9. **Description: 10–300 characters.** No HTML, no markdown.
10. **Reasoning: max 1000 characters.** Plain text only.
11. **Applied feedback list: 0–5 items**, each max 200 characters. If no feedback was applied, return an empty array.

## Profile Consistency (advisory, logged on failure but not blocking)

12. **Computed acidity within ±1.5 of target.** If the blend was designed for a low-acidity profile but the weighted average gives acidity 7.5, log a warning.
13. **Computed body within ±1.5 of target.** Same principle.
14. **Computed sweetness within ±1.5 of target.**

## Retry Logic

- On first validation failure: append the specific validation errors to the conversation and call the LLM again once.
- On second validation failure: return 422 with the validation errors. Log status = INVALID in ai_generations.
- On network or API error: log status = ERROR, return 503.

## What the Model Must Not Do

- Invent bean names or IDs not in the candidate list.
- Use a bean that is OUT_OF_STOCK.
- Output HTML or markdown in text fields.
- Return percentages that do not sum to 100.
- Output fewer than 2 or more than 5 recipe items.
- Include the same bean twice.

## JSON Schema (enforced at API level)

The model is called with the following JSON schema to constrain its output:

```json
{
  "type": "object",
  "required": ["blend_name", "description", "recipe", "reasoning", "applied_feedback"],
  "additionalProperties": false,
  "properties": {
    "blend_name": { "type": "string" },
    "description": { "type": "string" },
    "recipe": {
      "type": "array",
      "minItems": 2,
      "maxItems": 5,
      "items": {
        "type": "object",
        "required": ["coffee_bean_id", "percentage"],
        "additionalProperties": false,
        "properties": {
          "coffee_bean_id": { "type": "string" },
          "percentage": { "type": "integer", "minimum": 5, "maximum": 85 }
        }
      }
    },
    "reasoning": { "type": "string" },
    "applied_feedback": {
      "type": "array",
      "maxItems": 5,
      "items": { "type": "string" }
    }
  }
}
```
