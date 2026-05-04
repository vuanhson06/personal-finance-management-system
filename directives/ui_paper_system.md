# UI Paper System (Neumorphism) Directive
**Layer 1: Standard Operating Procedures**

## 1. Core Philosophy
The Personal Finance Web App utilizes a "Neumorphism" (soft UI) design system. Elements should appear extruded from the background or pressed into it. The light source is positioned at the top-left, casting bright highlights on the top/left edges and soft dark shadows on the bottom/right edges.

## 2. Design Tokens
- **Surface (Background):** `#E7E5E4` (Warm gray, crucial for shadows to work).
- **Text (Primary):** `#1E2938` (Deep navy/slate for high contrast).
- **Text (Secondary):** `#64748B` (Muted gray for labels).
- **Primary Accent:** `#006666` (Teal - used for active states, buttons, main charts).
- **Success:** `#00A63D` (Green - for positive trends, income sparklines).
- **Danger:** `#FF2157` (Red - for negative trends, expense sparklines).

## 3. Typography
- **Display & Headers:** `Space Mono` (Weights 600, 700). Used for card values (e.g., ₹125,400) and main titles.
- **Data & Body:** `JetBrains Mono` (Weights 400, 500). Used for labels, dates, and secondary text.

## 4. Shadow Physics & CSS Classes
Do not use standard Bootstrap shadows (`shadow-sm`, `shadow`). You must write custom CSS utility classes in `style.css` to achieve the neumorphic effect. The light source is Top-Left.

### Extruded (Outset) Shadow
Used for cards, panels, and inactive buttons.
```css
.neu-outset {
    background: #E7E5E4;
    box-shadow: 8px 8px 16px #c4c3c2, -8px -8px 16px #ffffff;
    border-radius: 20px; /* Standard card radius */
    border: none;
}
```

### Pressed (Inset) Shadow
Used for input fields, search bars, and active/pressed states.
```css
.neu-inset {
    background: #E7E5E4;
    box-shadow: inset 6px 6px 12px #c4c3c2, inset -6px -6px 12px #ffffff;
    border-radius: 50px; /* Pill shape for inputs */
    border: none;
}
```

### Interactive States
For buttons and clickable elements, we transition between outset and inset.
```css
.neu-btn {
    background: #E7E5E4;
    box-shadow: 6px 6px 12px #c4c3c2, -6px -6px 12px #ffffff;
    border-radius: 12px;
    border: none;
    color: #1E2938;
    transition: all 0.2s ease-in-out;
}

.neu-btn:hover {
    box-shadow: 8px 8px 16px #c4c3c2, -8px -8px 16px #ffffff;
    transform: translateY(-1px);
}

.neu-btn:active, .neu-btn.active {
    box-shadow: inset 4px 4px 8px #c4c3c2, inset -4px -4px 8px #ffffff;
    transform: translateY(0);
}
```

### Primary Action Button (Solid)
For primary actions (like "+ Create Project" in the reference), use the Primary Accent color with a subtle drop shadow, maintaining the pill shape.
```css
.neu-btn-primary {
    background-color: #006666;
    color: #ffffff;
    border-radius: 50px;
    box-shadow: 4px 4px 10px rgba(0, 102, 102, 0.3);
    border: none;
    transition: all 0.2s ease-in-out;
}
.neu-btn-primary:hover {
    background-color: #005555;
    box-shadow: 6px 6px 12px rgba(0, 102, 102, 0.4);
    transform: translateY(-1px);
}
```

## 5. Component Anatomy
### Financial Cards
- **Padding:** Minimum `24px` internal padding.
- **Structure:** 
  - **Top Left:** Small icon enclosed in a `.neu-outset` or `.neu-inset` box (approx `40x40px`, `10px` radius).
  - **Top Right:** Sparkline chart (Chart.js `line` with disabled axes, tension 0.4).
  - **Bottom Left:** Main value in `Space Mono` (e.g., `fs-3 fw-bold`), followed by percentage indicator colored in Success (`#00A63D`) or Danger (`#FF2157`).

### Charts Panel
- **Wrapper:** Large `.neu-outset` container.
- **Header:** Flexbox with Title on the left, Date filter (`.neu-inset`) and View toggles on the right.
- **Chart.js Config:** 
  - Primary Line Color: `#006666`
  - Secondary Line Color: `#A0AEC0`
  - Tension (Bezier curve): `0.4` for smooth flowing lines.
  - Fill: Gradient from `rgba(0,102,102,0.2)` to transparent.

## 6. Constraints
- **Web Environment:** All classes must complement and override Bootstrap 5 correctly (e.g., overriding `.card`, `.form-control`). Do not use Bootstrap borders.
- **Accessibility:** Ensure high contrast for text `#1E2938` on `#E7E5E4`. Inputs must show a visible focus ring (e.g., `outline: 2px solid #006666; outline-offset: 2px;`) to meet WCAG AA standards.
