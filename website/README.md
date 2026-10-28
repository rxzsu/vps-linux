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

## Cloudflare Workers — static assets

The same static output works in the Workers Git setup UI:

- Root directory / Path: `website`
- Build command: `bun install --frozen-lockfile && bun run build`
- Deploy command: `npx wrangler deploy --assets=./dist --name=vps-linux --compatibility-date=2026-10-28`
- Disable preview builds unless you separately configure a compatible preview command.

Cloudflare assigns a `workers.dev` URL after deployment. When the final hostname is known, update the canonical and Open Graph URL in `index.html`, `public/robots.txt`, and `public/sitemap.xml`. Email Routing permissions are not required for this static website.

## Cloudflare Pages — Git integration

1. In Cloudflare, create a **Pages** project and connect `rxzsu/vps-linux`.
2. Select production branch `main` and framework preset **Vue** (or None with the explicit values below).
3. Set root directory to `website`, build command to `bun run build`, and build output directory to `dist`.
4. Use the current Pages build image and set build environment variable `BUN_VERSION` to `1.4.4`. The committed `bun.lock` controls dependency versions. For a custom install command, use `bun install --frozen-lockfile`.
5. Name the project `vps-linux` if available. Deploy and check its assigned `*.pages.dev` address before promoting or sharing it.

The default metadata assumes `https://vps-linux.pages.dev/`; ownership/availability of that hostname is not verified. If Cloudflare assigns another hostname or you connect a custom domain, update the canonical link, `og:url`, `public/robots.txt`, and `public/sitemap.xml` before publishing. The Vite base is `/`, appropriate for a Pages root domain. There is no GitHub Pages workflow.

Cloudflare's Git integration handles deployments on push and preview deployments. This task only prepares the repository; it does not create a Cloudflare project or publish a site. No Cloudflare API token belongs in the repository. The `_headers` file applies basic browser security headers to the deployed static assets.

## Content boundaries

Release image and checksum links were verified against GitHub's v0.1 expanded-assets listing. The OS image was not downloaded or boot-tested as part of website development. The project does not yet provide reproducible OS build scripts or verified detailed boot/provisioning commands. The documentation explicitly preserves those limitations.

## Visual system and tooling

The hero uses original CSS/SVG server layers, atmospheric aurora, drifting particles and animated circuit paths, inspired by the Vue Bits visual language. Feature cards use pointer-following spotlights. These are local implementations, with no Vue Bits source copied or added WebGL dependency. All continuous effects disable themselves under `prefers-reduced-motion`; touch devices do not run pointer tracking. Pointer updates are coalesced with `requestAnimationFrame` and listeners are removed on unmount.

`bun run build` uses Vite directly. `vue-tsc` and its build gate were removed intentionally; production builds do not provide full Vue SFC type checking. TypeScript source and strict compiler configuration are retained. Run `bun outdated` to review available library updates and `bun run format:check` to check formatting.
