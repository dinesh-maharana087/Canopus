# Stage 1 Verification V04 — Frontend Foundation

## Scope and result

- Verification base: `4da340b20b82544e172ca88a83f0bbd7d772bdee`.
- Scope: Stage 1 Step 10 only.
- Overall result: **FAIL**, with environment blocks recorded separately.
- No frontend or application source was modified and no defect was repaired.
- Server, agent, deployment, Caddy, Stage 2, and unrelated documentation were
  not reviewed.

## Components reviewed

- The approved Stage 1 frontend design, Step 10 master-index/current-status
  entries, Step 10 execution card, and original Task 6 plan.
- `web/package.json` and the root project entry in `web/package-lock.json`.
- Vite, Vitest, TypeScript, and ESLint configuration under `web/`.
- All application source and tests under `web/src/`.
- Generated `web/dist` file shape after the independent production build.
- The installed React Router `NavLink` implementation only to verify its
  active-link accessibility behavior.

## Stable contracts verified

| Contract | Result | Evidence |
| --- | --- | --- |
| Independently buildable React/TypeScript application shell with separated app, layout, page, and theme boundaries | **PASS** | `web/src/main.tsx:1-11`, `web/src/app/App.tsx:1-21`, and the four requested quality gates |
| Exactly Dashboard `/`, Devices `/devices`, Alerts `/alerts`, Inventory `/inventory`, and Settings `/settings` route boundaries | **PASS** | Literal five-entry table at `web/src/app/routes.tsx:5-11`; router mapping at `web/src/app/App.tsx:11-16` |
| Accessible and responsive navigation | **PASS** | Named `nav`, list semantics, and `NavLink` anchors at `web/src/components/layout/Navigation.tsx:5-21`; installed `NavLink` applies `aria-current="page"`; visible focus, wrapping, responsive, and reduced-motion rules at `web/src/styles.css:31-45` |
| Rendered browser verification of navigation and controls | **BLOCKED BY ENVIRONMENT** | The in-app browser reported no available browser target; availability was checked once and no alternate browser backend was substituted |
| Light and dark modes, exact `device-watch-theme` persistence key, persisted restoration, and initial system preference resolution | **PASS** | `web/src/theme/ThemeProvider.tsx:10-39`; cyclic control at `web/src/components/layout/AppShell.tsx:6-25`; persisted-mode tests passed |
| System mode remains synchronized when the operating-system preference changes | **FAIL** | `ThemeProvider.tsx:28-39` reads `matchMedia().matches` only when `mode` changes and installs no media-query change listener |
| Every route page contains only its title and `Not implemented in Stage 1` | **FAIL** | `web/src/pages/FoundationPage.tsx:8` adds `Device Watch / Stage 1` inside every route page, beyond the two permitted strings at the Step 10 card line 40 and original plan line 734 |
| No fabricated monitoring/device data or active-monitoring wording | **PASS** | Scoped production-source scan found no counts, statuses, charts, sample devices, health records, or monitoring fixtures |
| No Stage 2 business API client behavior | **PASS** | Production source contains no business network primitive; manifest/lock root contain no HTTP, query, or chart client; only the approved Vite development proxy mentions `/api` |
| Vite development `/api` proxy preserves the path and uses the approved configurable localhost target | **PASS** | `web/vite.config.ts:5-17` defines only `server.proxy["/api"]`, defaults to `http://127.0.0.1:8000`, enables `changeOrigin`, and has no rewrite |
| Production build is static | **PASS** | Build produced only `dist/index.html`, one hashed CSS asset, and one hashed JavaScript asset |
| Required local UI primitive boundary exists | **FAIL** | The approved plan requires `web/src/components/ui/Button.tsx`; `web/src/components/ui/` is absent and `AppShell.tsx:19-26` uses a raw button |
| Step 10 automated tests cover every required contract | **FAIL** | `App.test.tsx:17-22` checks all headings but not each page message, navigation links, or current-page state; `ThemeProvider.test.tsx:11-23` does not test system media handling. These checks are required by the original plan line 708 |
| Frontend tests, strict TypeScript check, lint, and production build | **PASS** | Fresh commands all exited zero; 2 test files and 8 tests passed |
| Quality gates execute on a dependency-supported Node version | **BLOCKED BY ENVIRONMENT** | Host Node is `v22.14.0`; locked React Router 8.3.1 requires Node `>=22.22.0`. The gates nevertheless completed successfully, but this host cannot verify the supported-engine path |

## Commands actually executed

| Command | Result |
| --- | --- |
| `node --version` | **BLOCKED BY ENVIRONMENT** for the supported dependency engine — host is `v22.14.0`, below React Router's locked `>=22.22.0` requirement |
| `npm.cmd --version` | **PASS** — `10.9.2`; the PowerShell `npm.ps1` shim was blocked by local execution policy, so the installed command shim was used |
| `npm.cmd --prefix web run test -- --run` | **PASS** — 2 files, 8 tests |
| `npm.cmd --prefix web run typecheck` | **PASS** — `tsc -b --noEmit` exited zero |
| `npm.cmd --prefix web run lint` | **PASS** — ESLint exited zero |
| `npm.cmd --prefix web run build` | **PASS** — Vite 8.2.2 transformed 80 modules and generated the three static files listed above |
| Scoped `rg` scans for business I/O/client libraries and fabricated monitoring state in `web/src` and `web/package.json` | **PASS** — no production match |
| `rg` scan for media-query listener registration in `ThemeProvider.tsx` | **FAIL** — no listener exists |
| `Test-Path web/src/components/ui/Button.tsx` and component file listing | **FAIL** — required primitive is absent |
| Generated bundle string check for all non-root route paths and both empty-state strings | **FAIL** — build contains all routes and required message, but also contains the prohibited extra page string |
| Installed React Router `NavLink` `aria-current` inspection | **PASS** — active links receive `aria-current="page"` |
| In-app browser discovery | **BLOCKED BY ENVIRONMENT** — no browser target available |
| `git diff --check` | **PASS** |
| `git diff --stat`, `git diff`, and `git status --short` | **PASS** — final status contained only this V04 evidence document as a new file |

## Defects discovered

1. **V04-01 — route pages violate the exact empty-state content contract.**
   `FoundationPage` adds `Device Watch / Stage 1` in addition to the permitted
   title and `Not implemented in Stage 1` message.
2. **V04-02 — system theme is not reactive.** An operating-system theme change
   while the saved mode remains `system` leaves `data-theme` stale because no
   `MediaQueryList` change listener is registered.
3. **V04-03 — the approved local UI primitive boundary is missing.** The
   required local `Button` component was not created.
4. **V04-04 — required Step 10 regression coverage is incomplete.** The suite
   does not assert every route's message, navigation-link/current-page
   accessibility, or system-mode media changes.

## Environment blocks

- **BLOCKED BY ENVIRONMENT:** No in-app browser target was available for an
  independent rendered-DOM interaction pass.
- **BLOCKED BY ENVIRONMENT:** Node `v22.14.0` is below the locked React Router
  engine requirement of `>=22.22.0`. No system software was installed or
  upgraded. All four requested commands still exited successfully on this host.

## Source locations future stages may rely on

- Route table: `web/src/app/routes.tsx:5-14`.
- Router composition: `web/src/app/App.tsx:7-20`.
- Shell/navigation boundaries: `web/src/components/layout/AppShell.tsx:8-31`
  and `web/src/components/layout/Navigation.tsx:5-23`.
- Stage 1 route page: `web/src/pages/FoundationPage.tsx:1-13`.
- Theme contract and persistence: `web/src/theme/ThemeProvider.tsx:10-49`.
- Design tokens and accessibility styles: `web/src/styles.css:3-45`.
- Development proxy: `web/vite.config.ts:5-18`.
- Static build scripts and dependency boundary: `web/package.json:6-37`.

V04 stops here. No Stage 1 baseline is created by this document.
