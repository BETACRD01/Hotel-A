# CSS structure

The large public stylesheets are kept as stable entry points because templates already load them directly.
Each entry file now imports smaller files by responsibility, preserving the original cascade order.

- `estilos.css` imports `public/`: base public styles, layout, auth, client panel, reservations, responsive overrides and final unification rules.
- `resort_premium.css` imports `resort/`: premium public UI, catalog, client/reservation, auth and payment styles.
- `gerente.css` imports `manager/`: manager shell, dashboard components, forms, responsive rules and dark overrides.

When adding styles, prefer the matching folder instead of growing the entry files again.
