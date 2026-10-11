# VitalProbe public frontend

Static React/TypeScript website with Motion, Lenis, self-hosted fonts and generated
hero artwork. The evidence explorer reads a bundled, validated fictional run. No
accounts, submissions, analytics, model calls or browser secrets are involved.
The previous self-contained HTML report remains at `/evidence/`; JSON is available
there and at `/run.json` for existing links.

Use Node 24 or newer:

```sh
npm ci --ignore-scripts --no-fund
npm run dev
npm run typecheck
npm run lint
npm test
npm run build
npm run preview
```

Development and preview bind to loopback. Public link overrides and the development
host/port are documented in `.env.example` and validated in `src/config.ts`.
Never add provider secrets to a `VITE_` variable: Vite exposes those values publicly.
Maintained copy lives in `src/data/site.json`, evidence in `src/data/evidence.json`,
and animation settings in `src/config.ts`. Update the saved report and both JSON
copies together; tests reject inconsistent counts and case IDs.

The hero is decorative generated artwork, not a clinical device or scientific result.
The still was made using the built-in image generation tool, then optimized with
FFmpeg. Video authoring uses an explicitly approved, separate OpenRouter request;
no key or generation API is bundled in the website. See [asset provenance](ASSETS.md).

The site respects reduced motion, keeps decorative video paused until requested, provides
a pause/play control, and uses keyboard-operable filters, native FAQ disclosure and a
native setup dialog. Human clinical, counsel and calibration gates remain OPEN.
