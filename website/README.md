# VPS Linux website

Static Vue 3 website. Requires Bun 1.4.4 or newer. No backend, account credentials or environment variables are needed to build it.

## Local development

```sh
cd website
bun install --frozen-lockfile
bun run dev
bun run build
bun run preview
```

The terminal is a scripted demo, never a live shell. The site uses native anchor navigation and expandable documentation; no client-side router or SPA fallback is required. Motion respects the operating system's reduced-motion setting. No remote fonts or stock images are downloaded by the website.

## Browser validation

```sh
cd website
bunx playwright install chromium
bun run build
bun run test
```

Alternatively, use an installed Chromium: `CHROMIUM_PATH=/usr/bin/chromium bun run test`. Tests cover desktop, mobile and reduced motion, release destinations, navigation, documentation, keyboard focus, browser errors and overflow at representative widths. Screenshots and test results are local ignored artifacts.

## Vercel deployment

The production target is **https://vps-linux.vercel.app/**, assuming the project is named `vps-linux`. The canonical link, `og:url`, `public/robots.txt` and `public/sitemap.xml` all use that address; if Vercel assigns a different production hostname, update all four together before announcing the site.

Import `rxzsu/vps-linux` at [vercel.com/new](https://vercel.com/new) and use these settings:

| Setting | Value |
| --- | --- |
| Root Directory | `website` |
| Framework Preset | Vite (auto-detected) |
| Install Command | `bun install --frozen-lockfile` |
| Build Command | `bun run build` |
| Output Directory | `dist` |
| Production Branch | `main` |

The committed `bun.lock` makes Vercel select Bun; `packageManager` declares the intended Bun 1.4.4 version and `engines.node` pins the build runtime to Node 22. Confirm the actual Bun version in the first build log. No environment variables, API tokens or project IDs are required in the repository.

[`vercel.json`](vercel.json) sets the framework, install/build/output commands, security headers and immutable caching for hashed `/assets`. The old Cloudflare `public/_headers` file is intentionally removed because Vercel ignores it.

Vercel Git integration deploys every push to `main` and creates preview deployments for pull requests. Preview deployments are not indexed by search engines by default.

## Custom domain

1. Add the custom domain in the Vercel project and make it the primary domain.
2. Configure the DNS records Vercel shows (usually an apex `A`/`ALIAS` and a `www` `CNAME`).
3. Update the canonical link and `og:url` in `index.html`, plus `public/robots.txt` and `public/sitemap.xml`.
4. Redeploy and verify HTTPS, `www` redirects and the four public URLs.

No DNS records, tokens or credentials belong in this repository.

## Content boundaries

Release image and checksum links target the published v0.2 assets. The OS image was not downloaded or boot-tested as part of website development; acceptance evidence lives in `docs/validation.md`. The repository now includes the source-controlled automated build system, so the site must not repeat the old v0.1 claim that build scripts are unavailable.

## Visual system and tooling

The hero uses original CSS/SVG server layers, atmospheric aurora, drifting particles and animated circuit paths, inspired by the Vue Bits visual language. Feature cards use pointer-following spotlights. These are local implementations, with no Vue Bits source copied or added WebGL dependency. All continuous effects disable themselves under `prefers-reduced-motion`; touch devices do not run pointer tracking. Pointer updates are coalesced with `requestAnimationFrame` and listeners are removed on unmount.

`bun run build` uses Vite directly. `vue-tsc` and its build gate were removed intentionally; production builds do not provide full Vue SFC type checking. TypeScript source and strict compiler configuration are retained. Run `bun outdated` to review available library updates and `bun run format:check` to check formatting.

## English and Russian

Use the always-visible **RU / EN** control in the header. Language selection follows this order: valid `?lang=ru` / `?lang=en` query parameter, saved preference, browser language (Russian for `ru-*`, English otherwise). A manual choice updates the URL without reloading and is saved locally when storage is available. The site remains functional when browser storage is blocked.

UI copy, documentation, accessible labels, title and description metadata are localized; product names, shell commands and genuine terminal output retain their original spelling. `src/locales/ru.ts` holds the Russian dictionary using the English source text as keys. `src/composables/useLocale.ts` shares the reactive language across components. No backend or extra translation dependency is required. Browser tests cover both languages, persistence, explicit links, blocked storage and Russian layouts at widths from 320px to 1440px.
