# VitalProbe frontend

A static React/TypeScript website for the VitalProbe product, documentation and fictional
safety evidence. It shares a repository with the Python backend while remaining a
separate build and runtime. Browser visits do not execute audits or call model providers.

## Develop and verify

Use Node 24+ and the committed lockfile. From this directory:

```sh
npm ci --ignore-scripts --no-fund
npm run dev
```

Before publication:

```sh
npm run typecheck
npm run lint
npm test
npm audit --audit-level=low
npm run build
npm run preview
```

Development/preview bind to loopback. Output is `dist/`; deploy its contents using the
[release procedure](../docs/deployment.md), not the development server.

## Pages and assets

| URL | Content |
|---|---|
| `/` | Product overview, evidence entry points and local setup |
| `/product/` | Capabilities and workflow |
| `/explore/` | Filterable bundled fictional evidence |
| `/pricing/` | Free engine and planned paid offerings; availability details |
| `/docs/` | Setup commands and documentation resources |
| `/trust/` | Data boundaries, limitations and review responsibilities |
| `/evidence/` | Preserved self-contained HTML report |
| `/evidence/run.json`, `/run.json` | Preserved canonical fictional run |

Vite emits direct HTML entries with unique titles/descriptions and navigation fallbacks.
Test nested-route refresh, unknown paths and no-JavaScript report access on the host.

## Source and configuration ownership

| Owner | Maintained values |
|---|---|
| `src/config.ts` | Validated public URLs, loopback development configuration and animation settings |
| `.env.example` | Supported public build/development overrides |
| `src/data/site.json` | Main site copy and shared UI content |
| `src/data/pages.json` | Routes, page copy and planned pricing |
| `src/data/evidence.json` | Validated bundled fictional run |
| `src/lib/` | Content/schema validation, evidence selectors, setup and motion hooks |
| `src/App.tsx`, `src/PageSections.tsx` | Shared shell, interactions and page sections |
| `public/` | Self-hosted media, preserved report/JSON and static assets |

Never put credentials in `VITE_` variables or bundled data. The frontend has no account
system, submissions, analytics, browser storage, payment collection or remote model calls.
Its serving policy restricts browser connections. See [configuration](../docs/configuration.md).

## Motion and interaction

Motion handles entrances, reveals and transitions; Lenis handles smooth scrolling.
The muted hero video starts automatically and loops inline. System reduced-motion
preferences stop video and spatial/continuous animation, including changes made while
open. Rejected autoplay retains the poster image. There are no motion/playback buttons.

Keyboard-operable navigation, evidence filters, native FAQ disclosure, setup dialogs,
clipboard success/failure feedback and mobile Escape/focus behavior are tested manually.
Automated accessibility checks cover the configured rules and widths; they do not assert
complete assistive-technology or legal conformance. Preserve reduced-motion support when
editing CSS, active Motion animations or presence transitions.

## Evidence and pricing maintenance

Keep bundled evidence, the saved report and both public JSON copies consistent. Regression
checks reject mismatched counts and case IDs. Public evidence contains fictional inputs
and deliberately weak target outcomes; it must not be presented as a clinical study.

Planned prices are maintained in page data and are informational. Availability dialogs
explain the remaining prerequisites. They must not become checkout links without the
separate legal, provider and product approvals described in [legal](../docs/legal.md).

## Assets, delivery and growth

Fonts, icons, generated artwork and video are self-hosted; [ASSETS.md](ASSETS.md) records
provenance and licenses. Decorative imagery is unrelated to clinical test outcomes.
No generation API/key is bundled in the website.

Use versioned hashed assets, correct MIME types and separately controlled HTML caching.
The [scalability plan](../docs/scalability.md) explains the future 1M+ concurrent-user
objective, asset-transfer budgets and CDN/origin boundaries. [Reliability](../docs/reliability.md)
sets the availability and recovery objectives. These plans do not assert current load
capacity or historical uptime.
