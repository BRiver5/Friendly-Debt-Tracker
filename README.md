# Friendly Debt Tracker

> Good friends keep good tabs.

A lightweight, manual ledger for tracking informal debts between friends — "who
owes whom." **Not** a banking or payment app: no bank linking, no payment
processing, no money movement. Just a friendly, structured way to record who
paid for what and see running balances per person.

- **Mobile:** Expo SDK **54** · React Native 0.81 · TypeScript · expo-router ·
  Reanimated (timing/easing animations only — no springs) · custom
  `react-native-svg` charts.
- **Backend:** FastAPI · SQLAlchemy · SQLite (Postgres-portable) · scoped by an
  anonymous device UUID (no accounts, no login, no PII).

```
Friendly Debt Tracker/
├── backend/     FastAPI + SQLAlchemy REST API  (12 passing tests)
└── mobile/      Expo SDK 54 app (expo-router)
```

## 1. Run the backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pytest -q          # 12 passing
.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Docs at http://localhost:8000/docs. See [backend/README.md](backend/README.md).

## 2. Run the mobile app

```bash
cd mobile
npm install --legacy-peer-deps
npm run typecheck        # clean
npx expo start           # then press "a" for Android
```

**Point the app at your backend.** The API base URL is read from
`app.json → expo.extra.apiBaseUrl` (default `http://localhost:8000`), overridable
with `EXPO_PUBLIC_API_BASE_URL`. Notes:

- Android **emulator** reaches your host at `10.0.2.2` — the client rewrites
  `localhost` → `10.0.2.2` automatically.
- A **physical device** needs your machine's LAN IP, e.g.
  `EXPO_PUBLIC_API_BASE_URL=http://192.168.1.20:8000 npx expo start`.

## Screens

Onboarding → Home (net balance + friends) → Friend detail (history, settle up,
per-entry settle/edit/delete) → Add/Edit entry (friend picker, amount, direction
toggle, date) → Stats (real net-trend + per-friend charts) → Settings (clear all
data, honest about section).

## Design & scope decisions

- **Palette:** warm pastel base with a deep **sage** ("they owe you" / green) and
  **terracotta** ("you owe them" / warm) accent pair, tuned for WCAG-AA text
  contrast. Original layout and hand-drawn SVG iconography — not a clone of any
  reference.
- **Motion:** every animation uses `withTiming` with ease-out / ease-in-out
  curves. No springs, no bounce, no overshoot anywhere (balance count-ups,
  screen transitions, list entry, chart reveal, button presses).
- **No placeholders:** every button and screen is fully functional. Out-of-scope
  MVP features (bill splitting, reminders, export, multi-currency, cloud sync,
  photo receipts) are simply omitted — never shown as disabled stubs.
- **No accounts / no PII:** the app generates an anonymous device UUID stored in
  `expo-secure-store` and sends it as `X-Device-UUID`; all data is scoped to it.
- Balances are always **computed** server-side from entries, never stored, so
  they can never drift out of sync.

## Google Play readiness

- No login/registration flow to review.
- No sensitive permissions (no contacts, camera, or location; avatar is an
  emoji/color, not a photo upload).
- Clean empty states on a fresh install — no blank or broken views.
- Data Safety: collects only a randomly generated device identifier to associate
  locally-entered data with the device; no third-party sharing, no ads, no
  analytics SDKs.
