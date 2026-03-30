# Design System Specification: Clinical TCM Interface

## 1. Overview & Creative North Star
**Creative North Star: "The Modern Scholar’s Ledger"**

Traditional Chinese Medicine (TCM) is rooted in the balance of elements, tactile wisdom, and observational precision. This design system rejects the sterile, "plastic" aesthetic of modern medical software in favor of a "High-End Editorial" experience. We treat the interface not as a grid of buttons, but as a digital extension of a scholar's desk—organized, quiet, and profoundly intentional.

To move beyond "standard" UI, we utilize **Tonal Architecture**. Instead of rigid lines, we define space through paper-like layering, asymmetric "breathing room," and high-contrast editorial typography. The goal is to reduce the cognitive load for clinical nurses by creating a sanctuary of clarity amidst a high-pressure medical environment.

---

## 2. Colors & Surface Philosophy
The palette is derived from natural pigments: rice paper, mineral indigo, crushed cinnabar, and bamboo.

### Surface Hierarchy & The "No-Line" Rule
To achieve a premium, organic feel, **explicitly prohibit 1px solid borders for sectioning.** Boundaries are defined through background shifts or tonal nesting.
*   **Base Layer:** `surface` (#fbf9f4) – The primary "Xuan paper" canvas.
*   **Sectioning:** Use `surface_container_low` (#f5f3ee) for large secondary regions.
*   **Interactive Cards:** Use `surface_container_lowest` (#ffffff) to make high-priority data "lift" off the page naturally.
*   **The Glass Rule:** For floating menus or overlays, use `surface` at 80% opacity with a `backdrop-blur` of 12px. This ensures the TCM motifs (meridians/herbs) bleed through softly, maintaining a sense of depth.

### Signature Textures
*   **Subtle Grain:** Apply a low-opacity noise texture (2-3%) to `surface` layers to mimic the tactile tooth of handmade paper.
*   **Tonal Gradients:** For primary action headers, use a subtle linear gradient from `primary` (#162839) to `primary_container` (#2c3e50). This adds "soul" and weight to the header without looking "web 2.0."

---

## 3. Typography
The system balances the stability of a modern sans-serif with the heritage of "Song" style calligraphic influences.

*   **Display & Headlines (Newsreader):** Used for patient names, diagnostic titles, and high-level summaries. The serif "Newsreader" provides the professional, calligraphic flair requested, signaling authority and calm.
*   **Body & Labels (Manrope):** A clean, geometric sans-serif. It provides the "stable" foundation required for clinical readability. Use `body-md` for patient notes and `label-sm` for vitals.

**Editorial Hierarchy:**
*   **Intentional Asymmetry:** Align headlines to the left with significant leading (`16` spacing token) to create an editorial "white space" that feels expensive and uncluttered.

---

## 4. Elevation & Depth
We eschew traditional "drop shadows" in favor of **Ambient Tonal Layering.**

*   **The Layering Principle:** Depth is achieved by stacking surface tiers. A `surface_container_highest` (#e4e2dd) sidebar sitting on a `surface` background creates a natural structural break without needing a line.
*   **Ambient Shadows:** For critical floating elements (e.g., a medication confirmation modal), use a tinted shadow: `rgba(22, 40, 57, 0.06)` with a 32px blur. The tint of the `primary` indigo makes the shadow feel like natural light in a room, not a digital effect.
*   **Ghost Borders:** If accessibility requires a stroke (e.g., in a high-contrast mode), use `outline_variant` at 15% opacity. Never use 100% opaque borders.

---

## 5. Components

### Buttons & CTAs
*   **Primary:** Solid `primary` (#162839) with `on_primary` text. Use `xl` (0.75rem) roundedness for a soft but professional touch.
*   **Secondary:** `surface_container_high` background with `primary` text. No border.
*   **Tertiary/Quiet:** Transparent background with `secondary` (#496800) text for non-critical actions like "Add Note."

### Input Fields
*   **Style:** Minimalist. No bounding box. Only a 1px `outline_variant` bottom stroke that thickens to 2px in `primary` indigo on focus. 
*   **Error State:** Use `error` (#ba1a1a) for the bottom stroke and hint text.

### Cards & Lists
*   **The No-Divider Rule:** Forbid the use of horizontal divider lines. Use the spacing scale (`3` or `4`) to separate list items. 
*   **Grouping:** Use `surface_container_low` as a background "plate" to group related clinical data points (e.g., a patient's tongue diagnosis and pulse readings).

### Cinnabar Labels (The "Seal" Component)
*   For status badges (e.g., "Critical," "Urgent"), use a small square or rectangular chip with `tertiary_container` (#7f000a) background and `on_tertiary_container` (#ff8277) text. This mimics the look of a traditional Chinese red seal.

### TCM-Specific Motif Integration
*   **Meridian Line Watermarks:** Use lightweight SVG patterns of meridian flows in `outline_variant` at 5% opacity in the background of "Profile" pages.
*   **Herb Line Drawings:** Use as empty-state illustrations, rendered in `primary` indigo with a stroke weight of 0.5px.

---

## 6. Do’s and Don’ts

### Do
*   **Do** use the `16` (5.5rem) spacing token for top-level page margins to create a "gallery" feel.
*   **Do** use `secondary` (Bamboo Green) for "Success" or "Stable" clinical states to subconsciously signal health and vitality.
*   **Do** treat white space as a functional tool. If a screen feels cluttered, increase the background-color-shift areas rather than adding borders.

### Don’t
*   **Don’t** use "Palace Style" (No bright golds, ornate patterns, or heavy reds). We are building a tool for nurses, not a museum app.
*   **Don’t** use standard "Material Blue" or "Success Green." Stick strictly to the Indigo (#2C3E50) and Bamboo (#6B8E23) tokens.
*   **Don’t** use 3D effects, inner shadows, or heavy gradients. The UI should feel as flat and sophisticated as a sheet of expensive stationery.