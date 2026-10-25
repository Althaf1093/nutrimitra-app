# Wellstride design mock (reference only)

These are the owner-approved visual references, one HTML file per screen. Open any `.dc.html` as plain markup to read the
exact colours, spacing, copy and structure (they use inline styles and `theme.css` tokens). They are NOT app code:
rebuild them with the app's real components (React Native + expo-router), do not copy the HTML.

| File | Screen |
|---|---|
| Welcome.dc.html | Welcome with a Telugu / English picker (Telugu first) |
| Main.dc.html | Today (phone): calorie ring, macros, meal slots, water, movement, tab bar |
| AddFood.dc.html | Add food sheet: search with variants, camera, category chips |
| Coach.dc.html | Coach chat with a loggable meal card and quick-prompt cards |
| Plan.dc.html | Plan with food pictures, "from your kitchen" badges, swap, WhatsApp shopping list |
| Progress.dc.html | Insights dashboard (the tab is called Insights): habit score, KPI grid, weekly heatmap, best and worst day, patterns, macro split, nutrient check, eat more / cut back |
| ShareCard.dc.html | Shareable weekly card in Telugu (9:16) |
| Desktop.dc.html | Today on PC: sidebar and two-column dashboard |

Notes
- Numbers, names and Telugu text are illustrative. All Telugu needs a native reader before launch.
- Food "pictures" in the mock are original illustrated stand-ins. See docs/DESIGN_PROMPT.md for the image plan.
- Tab names: Today, Plan, Coach, Insights (Progress is renamed Insights).
