<<<<<<< HEAD
# Հայոց Հերոսներ — Telegram Mini App v4.0

React + Vite frontend, NestJS API under `/api`, shared MongoDB, Vercel-ready, Telegram Mini App integration, events calendar and web admin.

## v3 changes

- Rebuilt cinematic Home banner using the Hero of the Day.
- Rebuilt Hero Detail UI: portrait stage, iOS story sheet, facts, biography timeline, sharing and Framer Motion shared-element `layoutId` transitions.
- Full-width iOS-style bottom glass surface with safe-area support.
- Mobile input zoom fix: every input/select/textarea uses at least 16px font size (no forced disabling of pinch zoom).
- TanStack React Query with request deduplication, stale times, prefetching and persisted public-query cache.
- Private `/me` and `/admin` queries are excluded from persistent cache.
- New Events page + Event Detail page backed by MongoDB `events` collection.
- New `/admin` web panel with password login, HttpOnly signed session cookie and event CRUD.
- Event editor supports annual dates, categories, description, image URL, source URL, publication status and linked hero search.
- New Terms of Use and Privacy Policy pages.
- Telegram integration includes native SettingsButton, native BackButton on detail/legal routes, haptics, fullscreen, vertical-swipe control, closing confirmation, CloudStorage settings sync, popup, write-access request, QR scanner, Add to Home Screen, share URL and share-to-story wrapper (all feature-detected).
- Hero/meta endpoints remain cache-friendly; Events now use `no-store` so new admin events are visible immediately instead of being hidden behind stale CDN cache.

## Environment variables

Copy `.env.example` to `.env` for local development. On Vercel configure:

```env
MONGODB_URL=mongodb+srv://...
MONGODB_DB_NAME=erablur
BOT_TOKEN=...
VITE_BOT_USERNAME=erablurbot
ADMIN_PASSWORD=...
ADMIN_SESSION_SECRET=...
```

You may use `ADMIN_PASSWORD_SHA256` instead of `ADMIN_PASSWORD`.

To calculate SHA-256 locally:

```bash
node -e "console.log(require('crypto').createHash('sha256').update('YOUR_PASSWORD').digest('hex'))"
```

Keep `ADMIN_SESSION_SECRET` long and random. Do not commit the real `.env`.

## Local development

Terminal 1:

```bash
npm install
npm run api:dev
```

Terminal 2:

```bash
npm run dev
```

Vite proxies `/api` to `http://localhost:3001`.

## Vercel

Use this folder as the Vercel project root. The project already contains `vercel.json` and the serverless entry at `api/index.ts`.

After deployment, test:

```text
https://YOUR_DOMAIN/api/health
https://YOUR_DOMAIN/api/meta
https://YOUR_DOMAIN/api/heroes/random?limit=2
https://YOUR_DOMAIN/api/events/upcoming?limit=5
```

Then set the bot's `WEBAPP_URL=https://YOUR_DOMAIN` and use `integration/telegram_webapp_button.py` for a real Telegram `WebAppInfo` button/menu button.

## Events collection

Events are created from `/admin`; no hardcoded event list is required. Example values:

- title: `Վազգեն Սարգսյանի ծննդյան օր`
- date: `1959-03-05`
- annual: `true`
- category: `birthday`
- hero_id: optional Mongo hero `_id`

Another example:

- title: `Հայաստանի Հանրապետության Անկախության օր`
- date: `1991-09-21`
- annual: `true`
- category: `independence`

Annual events automatically calculate their next occurrence for the public calendar while preserving the historical source date.

## Hero Mongo schema

The API supports the existing nested schema:

```js
{
  name: { first: 'Շիրազ', last: 'Խաչատրյան' },
  date: { birth: '1989 թ․', dead: '2022 թ․' },
  region: 'Գեղարքունիք',
  war: 'Մարտական գործողություն',
  img_url: 'https://...',
  bio_link: 'https://...',
  bio: '<p>...</p>'
}
```

Mongo `_id` is normalized to the public `id` field if a custom `id` does not exist.

## Admin security

- Password validation happens only in NestJS.
- The password is never embedded into the React bundle.
- Successful login creates a 12-hour HMAC-signed HttpOnly SameSite=Lax cookie.
- Production cookies use `Secure` automatically.
- A small in-memory rate limiter slows repeated wrong-password attempts per serverless instance.
- For stronger production rate-limiting across all serverless instances, add a shared Redis/Upstash limiter later.

## Caching

Frontend:

- React Query deduplicates identical requests.
- Hero details are prefetched when cards are touched/hovered.
- Public hero/meta queries persist locally for fast reloads. Event queries intentionally do **not** persist and refetch on mount/focus plus every 30 seconds.
- Telegram profile and admin queries do not persist.

Backend/Vercel:

- hero/meta public GET endpoints may use cache-friendly headers.
- event GET endpoints send `Cache-Control: no-store` to prevent stale calendar data after admin changes.
- admin/profile endpoints remain private/non-persisted on the client.

## iOS input zoom

The app does **not** disable user zoom. Instead, all form inputs use at least `16px`, preventing the common iOS focus auto-zoom while keeping accessibility zoom available.


## v3.1
- Restored the original floating pill-style bottom navigation from v2 while keeping the Events tab and all v3 features.


## v3.2 navigation change
- Restored the original v2 four-item floating iOS pill bottom bar.
- Events remain available from Home/Event links and direct `/events` route.
- Telegram `MainButton` and `SecondaryButton` are forced hidden; the Mini App no longer creates a native Telegram bottom action bar.

## v3.3 desktop-admin update
- Removed the Mini App capabilities diagnostics section from Settings.
- Removed Telegram BackButton integration completely.
- Removed the Admin Panel entry from Settings; admin remains available only by direct `/admin` URL.
- Rebuilt `/admin` as a desktop dashboard with sidebar, statistics, event editor, and events table.
- Admin does not request session/event data below 1024px and shows a desktop-only guard instead.



## v3.4 changes
- Restored the `Օրացույց` tab in the floating iOS bottom navigation.
- Removed the `Վերականգնել սկզբնական կարգավորումները` reset button from Settings.


## v3.5 iOS bottom bar fix
- On Telegram iOS, the floating navigation is lowered to the actual bottom area.
- Prevents double-counting CSS and Telegram bottom safe-area insets.
- Android and desktop positioning are unchanged.


## v3.6 users + realtime moderation

- `/admin` now has **Overview**, **Users**, and **Events** desktop sections.
- Users can be searched by name, username, or Telegram ID and filtered by moderation status.
- User detail includes join/last-seen data, search count, recent search history, and a MongoDB-backed moderation audit log.
- Admin actions: **Restrict** (1h / 24h / 7d / 30d), **Block**, **Restore/Unblock**, moderation reason, internal note, and clear search history.
- Block / restrict / restore uses the **WebSocket first**. If the realtime connection is reconnecting, the admin automatically falls back to the authenticated REST endpoint.
- The Telegram Mini App maintains its own realtime WebSocket connection. A moderation change is pushed into an already-open app immediately and swaps the UI to the access-restricted screen without a manual refresh.
- MongoDB remains the durable source of truth. Realtime sockets use MongoDB change streams when available and automatically fall back to a short polling watcher if change streams are unavailable.
- Authenticated Telegram API requests are also checked server-side, so blocked/restricted users cannot continue normal API activity simply by bypassing the React screen.
- Realtime admin actions are written to the `admin_audit` collection.
- `/admin` is still desktop-only below 1024px and is not linked from Mini App Settings.

### Realtime / Vercel

The project exposes the realtime transport on `/api/realtime` from the same `api/index.ts` Node function. The WebSocket client includes reconnect/backoff logic because Vercel Function WebSocket connections can end when the function reaches its maximum duration. `vercel.json` sets `maxDuration` to 300 seconds; adjust it to the maximum allowed by your Vercel plan if needed.

No additional realtime environment variables are required. It uses the existing `MONGODB_URL`, `MONGODB_DB_NAME`, `BOT_TOKEN`, and `ADMIN_SESSION_SECRET`.


## v3.7 native top controls

- Removed custom in-app top navigation/control buttons from Hero Detail and Event Detail pages.
- Removed the custom back buttons from Terms and Privacy pages.
- Removed the Home header profile/avatar button; Profile remains available from the bottom navigation.
- Telegram's own native top chrome remains the only top-level control surface.
- Telegram BackButton API remains intentionally disabled, matching the earlier navigation decision.
- Telegram SettingsButton remains available as a native Telegram control.

## v3.8 event reminders + scheduled task

Users can now subscribe to Telegram reminders directly from an Event detail page.

### User reminder flow

- Reminder presets: same day, 1, 3, 7, or 14 days before the event.
- Reminders are tied to the authenticated Telegram user and stored in MongoDB collection `event_reminders`.
- The Event detail page requests Telegram write access when supported before enabling a reminder.
- Profile now includes **Իմ առաջիկա հիշեցումները** with open/cancel actions.
- Annual events automatically schedule the following year's reminder after successful delivery.
- One-time events mark their reminder as sent after delivery.

### Delivery task

Vercel Cron calls:

```text
GET /api/tasks/event-reminders
```

`vercel.json` schedules it at `0 5 * * *`, which is approximately 09:00 in Yerevan (UTC+4). The endpoint requires Vercel's `Authorization: Bearer $CRON_SECRET` header.

Required Vercel variables:

```env
CRON_SECRET=long_random_secret
WEBAPP_URL=https://your-project.vercel.app
```

Existing `BOT_TOKEN` is used to send Telegram Bot API reminder messages.

The task includes:

- atomic processing locks to reduce duplicate sends;
- per-event-occurrence deduplication;
- up to 5 delivery attempts;
- moderation checks before delivery;
- automatic schedule refresh when an event date/title changes;
- annual re-scheduling;
- delivery logs in `reminder_deliveries`;
- failed/suppressed state tracking.

### Admin reminder console

Desktop `/admin` now includes **Հիշեցումներ / Event Reminders** with:

- active, due, sent and failed metrics;
- subscription queue and status filters;
- manual **Run now** task trigger;
- admin cancellation;
- recent Telegram delivery log.

The scheduled task and manual admin task share the same deduplicated backend processor.

## v3.9 — Telegram-native back navigation only

- Removed/kept removed all custom in-app Back buttons from Mini App pages.
- Hero, Event, Terms and Privacy pages use Telegram `BackButton` only.
- Native `BackButton` is hidden on root tabs and `/admin`.
- Direct deep-linked detail pages fall back to Home if there is no usable in-app history.
- Desktop admin navigation remains unchanged because `/admin` is a normal web dashboard.


## v4.0 — live Events cache fix + premium Admin + Broadcast

### Events cache fix

The public calendar no longer sits behind the old multi-layer stale cache. Event list/upcoming/detail endpoints now send `Cache-Control: no-store`; the browser request also uses `cache: no-store`. React Query event entries are not persisted, refetch whenever the screen mounts/focuses, and refresh every 30 seconds while active. The React Query persistence key/buster was bumped to v4 so old persisted event data is ignored after deploy.

### Premium desktop Admin

`/admin` was rebuilt as a desktop-first control center with:

- premium glass/dark desktop shell and command-center Overview
- Users + realtime moderation inspector
- Events editor/database table
- Event Reminders queue/logs
- Telegram Broadcast composer, preview, campaigns, delivery counters, per-user delivery log, test delivery, silent mode, image attachment, inline URL button, and audience/language targeting
- WebSocket-first Block / Restrict / Restore with REST fallback
- admin remains blocked below 1024px and is not linked from the Mini App Settings

### Broadcast

Broadcast campaigns use the existing `BOT_TOKEN` and the MongoDB `users` collection. Blocked and restricted users are excluded. Available audience presets are all active users, active in the last 24 hours, 7 days, or 30 days, optionally narrowed by Telegram language code. Delivery results are written to `broadcast_deliveries`; campaign state is stored in `broadcasts`. Failed Telegram deliveries are visible in Admin instead of being silently discarded.

A send action processes up to 300 recipients per admin run by default (server hard limit 500 per request). If a campaign has more recipients, its status remains queued and the Admin shows **Continue queue**.

### Moderation screen

Blocked and restricted users now see a dedicated iOS 26-style liquid-glass access screen with status, restriction expiry, moderation reason, retry, and native Mini App close support. The restriction is still enforced server-side by `UserStatusGuard` and realtime WebSocket updates can replace an already-open Mini App immediately.


## v4.0.1 Vercel / Mongoose ESM fix

Fixed Node.js ESM startup crashes on Vercel by changing Mongoose DI/type-only symbols such as `Connection`, `Model`, and `HydratedDocument` to `import type`. Runtime symbols such as `Types` remain normal imports.


## v4.0.2
- Bottom navigation pill now has `margin-bottom: 15px`.

## v5 Admin / Telegram Broadcast Studio

- Responsive premium Admin Console (`/admin`) for desktop and phone.
- Telegram owner ID defaults to `8182558373` (override with `OWNER_TELEGRAM_ID`).
- Owner can add/remove Telegram admins from the Admins section. Admin records are stored in MongoDB collection `admins`.
- Telegram-admin login uses verified Mini App `initData`; password login remains a fallback admin login but is not owner-level.
- Broadcast Studio supports HTML / MarkdownV2 / Markdown / plain text, media (photo/video/animation/document), silent/protected messages, link previews, custom emoji HTML tags, button custom emoji IDs and Telegram inline buttons (link, Web App, popup callback, copy, login URL, callback, switch-inline variants).
- Popup callback buttons require the aiogram handler in `integration/telegram_broadcast_callbacks.py` to be included in the Python bot router.

### Recommended env

```env
OWNER_TELEGRAM_ID=8182558373
ADMIN_SESSION_SECRET=replace-with-a-long-random-secret
ADMIN_PASSWORD=optional-password-fallback
BOT_TOKEN=...
MONGODB_URL=...
MONGODB_DB_NAME=erablur
```


## v5.0.2.1
- Removed all Framer Motion shared-layout (`layout` / `layoutId`) transitions.
- Hero cards no longer morph into hero detail screens.
- Bottom-tab active indicator no longer uses a shared-layout animation.
- Regular page/content animations remain unchanged.


## v5.0.2 broadcast reliability fix
- Draft broadcasts can be saved before message/media is complete.
- Missing internal titles are generated automatically.
- Send/test validation happens at delivery time with explicit errors.
- Media + caption + inline keyboard are sent as one Telegram message when caption length allows.
- Failed deliveries can be retried; successful deliveries are deduplicated.
- Admin UI now surfaces the exact backend/Telegram error instead of only showing a generic failed request.
=======
# Հայոց Հերոսներ — Advanced DeepSeek & Support Edition

An `aiogram` Telegram museum bot with SQLite fallback plus an optional MongoDB backend, admin tools, channel publishing, inline search, image cards, a database-grounded DeepSeek assistant, and privacy-conscious voluntary support flows.

## Included

- Museum search by name, surname, full name, war/action, deep links, and inline search.
- DeepSeek questions grounded only in local museum records, summaries, and quizzes.
- Armenian-aware hero-name resolution for natural questions, inflected surnames, spelling variants, and minor typos.
- Telegram Stars support with verified `pre_checkout_query` and `successful_payment` handling.
- Cryptomus hosted invoices for USDT/crypto, signed API calls, manual status checking, and optional signed webhook callbacks.
- Optional hosted bank-card URL and up to eight configurable external payment methods.
- Anonymous-by-default public presentation: donor names/usernames are never published.
- Minimal payment audit records in SQLite for verification, duplicate protection, support, and possible refunds.
- `/support`, `/donate`, `/terms`, and `/paysupport` commands.
- User payment history and admin support statistics.
- SQLite WAL fallback, optional MongoDB via `MONGODB_URL`, backups/imports/exports, daily channel posts, and secure secret configuration.
- Centralized Telegram custom emoji IDs with reusable `<tg-emoji>` helpers.

## Important privacy meaning

“Anonymous” means anonymous to the public and to other bot users. It does **not** mean invisible to Telegram, app stores, banks, blockchains, Cryptomus, or another hosted payment provider. The bot does not collect card numbers, CVV codes, wallet seed phrases, or private keys. It stores the Telegram user ID and technical transaction identifiers so payments can be verified and supported.

## Requirements

- Python 3.10–3.14. Python 3.13 is recommended.
- Telegram bot token from BotFather.
- DeepSeek API key for AI features.
- Cryptomus merchant ID and **payment** API key for crypto invoices.
- A public HTTPS endpoint only when automatic Cryptomus webhooks are desired. Manual payment checking works without one.

## Windows setup

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python main.py
```

At minimum:

```env
BOT_TOKEN=...
OWNER_ID=...
BOT_USERNAME=...
DEEPSEEK_API_KEY=...
SUPPORT_CONTACT=@your_username
```

### MongoDB

The bot now switches to MongoDB automatically when `MONGODB_URL` is set. If it is empty, SQLite remains the fallback.

```env
MONGODB_URL=mongodb+srv://USERNAME:PASSWORD@YOUR_CLUSTER/erablur?retryWrites=true&w=majority
MONGODB_DB_NAME=erablur
MONGODB_REQUIRED=false
MONGODB_TIMEOUT_MS=5000
```

To move the bundled SQLite data into MongoDB once:

```bash
python scripts/migrate_sqlite_to_mongo.py
```

Set `MONGODB_REQUIRED=true` only if you want startup to fail instead of falling back to SQLite when MongoDB is unavailable.

For Cryptomus:

```env
CRYPTOMUS_MERCHANT_ID=...
CRYPTOMUS_PAYMENT_KEY=...
CRYPTOMUS_TO_CURRENCY=USDT
CRYPTOMUS_NETWORK=tron
```

Leave `CRYPTOMUS_NETWORK` empty to allow the checkout page to offer available USDT networks according to your merchant configuration.

## Automatic Cryptomus webhook

Manual invoice checking is already available in the bot. For automatic confirmation, expose port `8080` through an HTTPS reverse proxy and configure the same secret in both URLs:

```env
PAYMENT_WEBHOOK_ENABLED=true
PAYMENT_WEBHOOK_PORT=8080
PAYMENT_WEBHOOK_PATH_SECRET=a-long-random-secret
CRYPTOMUS_CALLBACK_URL=https://your-domain.example/cryptomus/a-long-random-secret
```

The webhook validates the Cryptomus signature before changing a payment. `CRYPTOMUS_VERIFY_IP` is disabled by default because many hosting platforms use reverse proxies; enable IP validation only when the real source IP reaches the application directly.

## Bank-card method

The bot must not process card data itself. Put a hosted payment link from your bank/acquirer or donation provider in:

```env
BANK_CARD_PAYMENT_URL=https://your-provider.example/payment-link
```

The user opens the provider page. The provider may require a name, bank authentication, or KYC. Telegram Stars are the most private integrated option from the bot’s perspective because the invoice does not request personal fields.

## Additional methods

```env
EXTRA_PAYMENT_METHODS_JSON=[{"title":"💠 TON Wallet","url":"https://example.com/ton"},{"title":"₿ Bitcoin","url":"https://example.com/btc"}]
```

Use hosted pages or payment links. Never put private keys or seed phrases in `.env`.

## Custom emojis

The supplied custom emoji IDs are stored in `app/config/custom_emojis.py`. Use `ce("user")`, `ce("sword")`, `ce("armenia_1")`, etc. from `app.utils.custom_emoji` inside HTML Telegram messages.

## Commands

- `/start` — main menu
- `/ai` — DeepSeek museum assistant
- `/support` or `/donate` — voluntary support
- `/terms` — support and privacy terms
- `/paysupport` — payment issue contact instructions
- `/admin` — admin panel
- `/ai_status` — AI usage/status for admins

## Telegram Stars notes

The bot creates invoices using currency `XTR`, verifies pre-checkout data, and records the `telegram_payment_charge_id` after a successful payment. Keep transaction backups because charge IDs can be needed for support or refunds.

## Docker

```bash
docker compose up -d --build
docker compose logs -f
```

The `data`, `logs`, and `temp` directories are mounted so the SQLite database and operational files persist.

## Security

The original upload contained live Telegram tokens and previously contained a hard-coded MongoDB credential. Those secrets are not included here. Revoke/rotate old secrets before deploying and keep new values only in `.env` or a hosting secret manager.

Never commit `.env`.

## Telegram Mini App (React + NestJS + Vercel)

A complete Mini App is included in `webapp/`. It uses a React/Vite frontend, NestJS `/api` backend, Telegram `initData` verification, the same MongoDB database as the bot, and an iOS 26-inspired liquid-glass UI.

Deploy the `webapp` folder on Vercel, set the same `MONGODB_URL`, `MONGODB_DB_NAME`, and `BOT_TOKEN`, then set `WEBAPP_URL=https://your-project.vercel.app` in the Python bot environment and restart it. See `webapp/README.md` for the full setup.
>>>>>>> 54c1deb (commit)
