# MongoDB + Custom Emoji Upgrade

- Added optional MongoDB backend selected with `MONGODB_URL`, with SQLite fallback.
- Added MongoDB indexes for heroes, users, history, channels, donations, and AI usage.
- Added one-time SQLite → MongoDB migration script.
- Added the supplied Telegram custom emoji IDs and reusable HTML helper.
- Applied custom emojis to the main menu, profile, clear-history confirmation, and About page.
- Added `.env.example` and MongoDB deployment documentation.

# AI Retrieval v3 — Armenian Name Resolution Fix

- Fixed natural-language hero lookup so full names inside Armenian questions resolve before broad keyword matches.
- Added Armenian orthography normalization for `Սևակ`/`Սեվակ`, punctuation, grammatical endings, and small typos.
- Prevented same-first-name records from contaminating the AI context.
- Added deterministic answers for simple region, war, birth, and death questions.
- Added a grounded fallback when the model incorrectly claims that an existing database record is missing.
- Versioned AI cache keys so older incorrect cached answers are ignored.
- Added focused retrieval regression tests for Ռոբերտ Աբաջյան and Սեվակ Սերոբյան.

# Advanced v3 — Support Edition

- Renamed the public bot experience to **Հայոց Հերոսներ**.
- Added a complete privacy-conscious **Աջակցություն** section.
- Added Telegram Stars invoices with pre-checkout validation, successful-payment verification, idempotent records, and charge ID storage.
- Added Cryptomus USDT/crypto hosted invoices with signed API requests, status checks, optional signed webhooks, and payment notifications.
- Added optional hosted bank-card and extra payment-method buttons without collecting card or wallet secrets in the bot.
- Added `/support`, `/donate`, `/terms`, and `/paysupport` commands.
- Added user payment history, minimal SQLite audit records, and admin payment statistics.
- Added duplicate-update protection, HTTPS-only external payment links, configurable limits, and disabled-state guards.
- Updated Docker, `.env.example`, tests, and deployment documentation.

# Advanced v2 — DeepSeek Edition

- Added DeepSeek grounded Q&A, hero summaries, quizzes, retry logic, concurrency limits, circuit breaker, usage quotas, and cache.
- Replaced the broken Mongo/SQLite mixture with a secure SQLite WAL data layer.
- Removed hard-coded credentials and excluded `.env` from the package.
- Added all missing database methods and fixed channel/user/history lookups.
- Rebuilt the admin panel with working statistics, hero CRUD/import/export, broadcast, backup, cache, channel, and AI tools.
- Removed duplicated hero search responses and fixed image/temp-file cleanup.
- Added Unicode-aware Armenian search and local context ranking.
- Added Docker, environment template, tests, lint-clean source, and deployment documentation.

## Custom emoji UI + colored buttons

- Added the second custom emoji pack (`search`, `book`, `robot`, `heart`, `phone`, `church`, `statue`, `lion`, `candle`, `star`).
- Added an outgoing aiogram client-session middleware that converts supported native UI emoji into `<tg-emoji>` custom emoji entities.
- Existing custom emoji entities are protected from double conversion.
- Inline and reply keyboard emoji are moved to `icon_custom_emoji_id`, so buttons use Telegram custom emoji icons instead of static text emoji.
- Button colors are inferred automatically: `primary` (blue), `success` (green), and `danger` (red).
- Unsupported static UI emoji are removed from outgoing UI text instead of being left non-custom.
