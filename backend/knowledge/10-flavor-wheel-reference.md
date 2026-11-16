# Coffee Flavor Wheel Reference

This document maps common tasting vocabulary to our three primary axes: acidity, body, and sweetness.

## Primary Flavor Axes (1–10 scale)

### Acidity (1 = flat/none, 10 = very high/sharp)

Acidity in coffee is not sourness. At appropriate levels it is perceived as brightness, liveliness, and freshness. At excessive levels it becomes unpleasant sharpness or sourness.

**Descriptors by acidity level**:
- 1–2: Flat, lifeless, no brightness, dull
- 3–4: Soft, mild, warm, low-key brightness (Brazilian natural, dark roast)
- 5–6: Balanced, bright, clean, refreshing (Colombian, medium roast)
- 7–8: Vibrant, sparkling, wine-like, citrus-forward (Kenyan, Ethiopian washed)
- 9–10: Sharp, intense, piercing, requires precise extraction

**Acidity note associations**:
- Citric acid: Lemon, orange, grapefruit (Ethiopian washed, light roast)
- Malic acid: Apple, stone fruit, pear (Kenyan, Colombian)
- Tartaric acid: Wine, blackcurrant, grape (Kenyan, natural fermented)
- Phosphoric acid: Clean brightness, minerality (Kenyan, high-altitude)
- Acetic acid: Vinegary, fermented (over-fermented processing — defect)

---

### Body (1 = very light/thin, 10 = very heavy/full)

Body is the perceived weight or texture of the coffee on the palate.

**Descriptors by body level**:
- 1–2: Watery, thin, tea-like
- 3–4: Light, delicate, clean, silky
- 5–6: Medium, round, smooth, balanced
- 7–8: Full, creamy, heavy, substantial
- 9–10: Syrupy, very heavy, thick, coating

**Body note associations**:
- Light body: Ethiopian washed, light roast, fine grind with low TDS
- Medium body: Colombian, Guatemalan
- Full body: Brazilian natural, Sumatran, dark roast

---

### Sweetness (1 = dry/no sweetness, 10 = very sweet)

Sweetness is the perception of natural sugars in the coffee. It is not added sugar.

**Descriptors by sweetness level**:
- 1–2: Dry, astringent, bitter
- 3–4: Mild sweetness, subtle caramel undertone
- 5–6: Pleasant sweetness, brown sugar, mild caramel
- 7–8: Noticeably sweet, honey, caramel, fruit sweetness
- 9–10: Very sweet, candy-like, dried fruit, molasses

---

## Tasting Note Categories (LLM Estimation)

The following categories are estimated by the AI — they are directional, not measured:

**Chocolate notes**: Dark chocolate, milk chocolate, white chocolate, cacao nib, chocolate brownie.
- Associated with: Brazilian, Guatemalan, medium-dark roast, natural process.

**Caramel / Sugar notes**: Caramel, toffee, butterscotch, brown sugar, honey, molasses.
- Associated with: Colombian, Costa Rican honey, medium roast, sweetness axis 6+.

**Fruity notes (citrus)**: Lemon, orange, bergamot, grapefruit, lime.
- Associated with: Ethiopian washed, Kenyan, light roast, high acidity.

**Fruity notes (berry)**: Blueberry, raspberry, blackcurrant, strawberry, cherry.
- Associated with: Ethiopian natural, Kenyan, Burundian, medium-light roast.

**Fruity notes (stone fruit)**: Peach, apricot, plum, nectarine.
- Associated with: Rwandan, Burundian, Guatemalan, medium roast.

**Nutty notes**: Hazelnut, almond, walnut, peanut.
- Associated with: Brazilian, low-altitude Latin American, medium-dark roast.

**Spice notes**: Cinnamon, clove, cardamom, cedar, tobacco.
- Associated with: Sumatran, Sulawesi, Indian, dark roast.

**Floral notes**: Jasmine, rose, lavender, bergamot, elderflower.
- Associated with: Ethiopian Yirgacheffe, Gesha/Geisha, light roast.

**Earthy notes**: Soil, mushroom, tobacco, wood, leather.
- Associated with: Sumatran (wet-hulled), dark roast, low-altitude beans.

---

## Mapping User Language to Profile Targets

When a user describes a desired blend in natural language, map their words to acidity/body/sweetness targets:

| User phrase                          | Acidity target | Body target | Sweetness target |
|--------------------------------------|---------------|-------------|-----------------|
| "Bold, strong, intense"              | 3.0–5.0       | 8.0–9.5     | 5.0–7.0         |
| "Smooth, easy drinking"              | 4.0–5.5       | 5.5–7.0     | 7.0–8.5         |
| "Bright, fruity, complex"            | 6.5–8.5       | 4.0–6.0     | 6.5–8.0         |
| "Chocolatey, nutty, comfort"         | 3.0–5.0       | 6.5–8.0     | 7.0–8.5         |
| "Floral, delicate, tea-like"         | 7.0–9.0       | 2.5–4.5     | 6.0–8.0         |
| "Good for milk drinks, latte"        | 2.5–4.5       | 7.0–9.0     | 7.0–9.0         |
| "Low acid, stomach-friendly"         | 1.5–3.5       | 6.0–9.0     | 5.0–7.5         |
| "Espresso, dark, rich"               | 2.5–5.0       | 7.5–9.5     | 5.5–7.5         |
| "Single origin style, terroir"       | 6.0–8.5       | 4.0–6.0     | 6.0–8.0         |
| "Sweet, dessert-like"                | 3.0–5.0       | 5.5–7.5     | 8.0–9.5         |
