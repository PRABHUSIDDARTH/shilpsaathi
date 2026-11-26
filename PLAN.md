# ShilpSaathi Prototype: Build Plan

**Team size:** 1 (solo)
**Plan date:** Thu 26 Nov 2026
**Deadline:** 6/12/26, read as **Sun 6 Dec 2026** (DD/MM/YY). The other reading, 12 June 2026, has already passed.
**Time available:** 10 calendar days, Fri 27 Nov to Sun 6 Dec. The schedule assumes all 10 are working days, weekends included.

**Scope**
- **MUST:** An artisan sends photos and a voice note (Tamil or English) on Telegram. ShilpSaathi creates a listing under the artisan's name, with a story written from their own words and a price band that cites real comparables. The artisan approves it, and the listing is published to a public page.
- **SHOULD:** A buyer posts a requirement. ShilpSaathi matches it to artisans and drafts a proposal. The artisan approves the proposal. **This is not in the schedule** (see §3.3). It is built only if MUST is finished early.

**Rules**
- An approval gate is enforced in code. Tests prove that nothing is committed without approval.
- Comparables come from a dataset we verify, with a source URL and a date for each one. Comparables are never invented.
- Only free tiers are used. Telegram is the default channel.
- Secrets live only in `.env`.

---

## 1. Stack (all free tier)

| Layer | Choice |
|---|---|
| Language and tooling | Python 3.12 with `uv`. `pytest` and `hypothesis` for tests. GitHub Actions for CI. |
| Chat channel | Telegram Bot API through `python-telegram-bot`, using long polling. Approve, Edit and Reject are inline buttons. |
| Web | FastAPI with Jinja2. The server renders `/p/{id}` and the audit-log view. `qrcode` generates the QR. |
| Data | SQLite through SQLAlchemy 2, with `PRAGMA foreign_keys=ON`. SQL triggers enforce the gate invariants. Media is stored on local disk with a sha256 hash. |
| LLM | **Gemini**, using a Google AI Studio free-tier key. It handles vision, fact extraction and the story, with JSON-schema-constrained output validated by Pydantic. |
| Speech-to-text | Chosen by a spike on D4: Gemini audio against Whisper-large-v3 on Groq's free tier, scored by word error rate (WER) on our own Tamil clips. `ffmpeg` converts Telegram's OGG/Opus voice notes. |
| Images | Input: normal Telegram photos by default (compressed by Telegram). Images sent as files (JPEG, PNG, WebP or HEIC, up to 20 MB) are also accepted, and those originals are kept. Every stored file is kept unchanged. Pillow makes non-generative edits to copies only: auto-orient, crop and resize. Originals sent as files can carry EXIF data, including GPS location, so **never publish a stored file directly**: publish a re-encoded copy with metadata removed. HEIC needs an extra decoder (for example `pillow-heif`). |
| Demo hosting | Runs locally. A `cloudflared` quick tunnel, which needs no account, gives a public link to `/p/{id}`. |

## 2. Differences from ARCHITECTURE.md

| Topic | Architecture | This plan | Why |
|---|---|---|---|
| **Comparables** | "Simulated (curated seed set)" | **Real rows, collected and verified by hand** (§5) | Project rule. The "real vs. simulated" tables in README.md and Architecture.md must be updated on D10. |
| Channel | WhatsApp is the target | Telegram, behind the same adapter interface | Free, no business verification needed, and it has inline buttons |
| Webhooks | Webhooks with signature checks | Long polling. A webhook with `secret_token` only if the bot is deployed. | No public URL is needed for the bot |
| Database | Postgres with pgvector | SQLite | No setup. Comparable matching is a structured filter on craft, material and size, so vectors are not needed. SQLAlchemy keeps a later move to Postgres cheap. |
| Object storage | Object storage | Local disk plus sha256 | Prototype scale |
| Languages | One regional language, plus English and Hindi | Tamil and English | Scope |
| Read-back | Voice read-back through TTS | Text read-back in Tamil and English. TTS is out of scope. | Time. The quality of free Tamil TTS is unverified. |
| Agents | Six agents | Typed functions in one process. Only Intake, Vision, Story and Pricing are built for MUST. | Less to build, with the same guarantees |
| Buyer side | Buyer feed, requirement form, matching and proposal | Published listing page only. Matching and proposals are SHOULD and unscheduled. | Solo with 10 days |
| Image checks | Colour-difference cap | Non-generative operations only, original kept | Time |
| Repo layout | `/apps /agents /core …` | One package `shilpsaathi/{channel,gate,agents,guard,pricing,web}`, plus `/data` and `/eval` | Fewer moving parts |

## 3. Milestones
Effort is in person-days (pd). Every milestone ends with something that runs.

| # | Milestone | Runnable result | Effort |
|---|---|---|---|
| M0 ✅ | **Done 26 Nov** (live photo and voice note test passed; CI has not run yet because nothing is pushed). Skeleton: `.gitignore` and `.env.example` committed before any key exists, CI, and a Telegram echo bot that stores photos and voice notes | Send a photo and a voice note; the bot confirms both are stored with their hashes | 0.5 |
| **M1** | **Approval gate first, using fakes.** A hardcoded listing goes Drafted → Checked → Pending → Approve button → Approved → Committed, and is published at `/p/{id}`. All gate tests in §3.1 are written in this milestone. | The full MUST path runs with no AI, and `pytest` passes all the gate tests | 1.5 |
| M2 | Intake: STT spike, transcript, fact extraction, vision attributes, at most one follow-up question, a story built from the transcript, and text read-back. Edit sends the listing back through the gate. | A real Tamil voice note with photos produces a draft listing, read back under the maker's name | 2 |
| M3 | Minimal Faithfulness Guard: every claim cites a transcript span or a photo attribute the artisan confirmed, and a blocked-terms list is applied. Planted-error eval with 10 listings. | A planted false claim is blocked live, and the eval prints the catch rate | 0.5 |
| M4 | Pricing: comps validation script, cost floor, and a 25th–75th percentile band. With fewer than 8 matched verified comps it shows low confidence and the cost floor only. The top 3 comps are shown with source URL and date. | The read-back shows a price band with cited comps | 1 |
| M5 | Polish: the published page shows the maker's name first, with the QR code and an audit-log view. Full demo run and a backup video. | **MUST complete** | 1 |
| | **Coding subtotal** | | **6.5** |
| Data | Craft data check 0.5, Tamil clips 0.5, comps collection 1, comps verification 0.5 (§5) | Verified comps CSV and a Tamil clip set | **2.5** |
| Buffer | | | **1** |
| | **Total** | | **10** = days available |

### 3.1 Gate tests (all must pass)
1. A commit without an `Approved` record is rejected.
2. Only the artisan's own Telegram user ID can approve.
3. Forged or replayed button data is rejected. `callback_data` is an opaque single-use ID looked up on the server. Telegram caps it at 64 bytes, so the content never travels in the button.
4. An approval for version N cannot publish version N+1. This is enforced by a content-hash mismatch.
5. `Expired` never becomes `Approved`.
6. Any edit to the content after approval starts a new approval cycle. For a listing this covers price and text; for a proposal (SHOULD), price, quantity and deadline.
7. A double tap on Approve is idempotent.
8. The approvals table is append-only. SQL triggers abort any `UPDATE` or `DELETE`.
9. A direct DB insert into the published table that bypasses the gate function fails at the SQL trigger. The trigger requires a matching `Approved` record with the same content hash.
10. A property test runs random action sequences and never reaches `Committed` without a matching approval.

### 3.2 Schedule

| Day | Date | Work |
|---|---|---|
| D1 | Fri 27 Nov | Craft data check (§4), choose the craft, M0 |
| D2 | Sat 28 Nov | M1: state machine, approvals table, triggers |
| D3 | Sun 29 Nov | M1: gate tests, Telegram Approve button, `/p/{id}`. Evening: record 10 Tamil clips and type their reference transcripts |
| D4 | Mon 30 Nov | STT spike (WER), then start M2 |
| D5 | Tue 1 Dec | Finish M2 |
| D6 | Wed 2 Dec | Collect comps: one craft, target 25 rows, each with a Wayback snapshot |
| D7 | Thu 3 Dec | M3. Verify comps in a separate pass from D6 (§5) |
| D8 | Fri 4 Dec | M4 |
| D9 | Sat 5 Dec | M5, demo rehearsal, backup video. **MUST done.** |
| D10 | Sun 6 Dec | Buffer. Fix the "real vs. simulated" tables in README.md and Architecture.md. Submit. |

### 3.3 Cut rules
- If a day slips, use the D10 buffer first, then reduce M5 polish. **The gate tests, comps verification and claim trace are never cut.**
- SHOULD (M6: buyer requirement form → scored-filter match → drafted proposal → artisan approves through the same gate) needs about 1.5–2 pd. It is not scheduled. Start it only if M5 is done by end of D8.

## 4. Choosing the demo craft (D1, half a day)
Choose the craft based on where the data is, not the other way round.
- Check where public, dated prices exist for Tamil crafts. Sources: Co-optex, Poompuhar, Tribes India, iTokri and Amazon Karigar. Candidates: cotton sarees, palm-leaf baskets and Thanjavur art plates.
- Pick **one** craft and a narrow size bucket where at least 25 comps look reachable.
- If no craft reaches 8 matched comps, the demo honestly shows "low confidence, cost floor only".

## 5. Collect by hand
- **Comps CSV**, one row per listing. Columns:
  - `craft`, `material`, `size_cm`, `price_inr`
  - `source_url`, `observed_at`
  - `archived_url`: a Wayback "Save Page Now" snapshot
  - `collected_by`, `verified_by`, `verified_at`

  Verifying a row means opening `archived_url` and confirming the price. Ideally a second person does this. If no one is available, do it as a separate pass on a different day (D7) and record `verified_by` as a self-verification. The pricing code refuses any row missing `verified_by` or `archived_url`. Collect by hand only, with no scraping. Store links, not copied content.
- **Product photos.** Use items you own, or items photographed with permission. Never use images from the web.
- **Tamil voice clips.** Record 10 clips from speakers who consent. Each clip needs a reference transcript typed by hand, for the WER score.
- **Planted-error set.** 10 listings, each with an injected unsupported claim.
- **Blocked-terms list.** GI, Silk Mark, Handloom Mark, organic, "ancient", "royal", and similar terms.
- **Personas.** 2 artisans, each with a consent note.

## 6. Accounts and keys (`.env` only, git-ignored)
- **Telegram:** a bot token from @BotFather, plus the Telegram user IDs of the demo artisans.
- **Google AI Studio:** a Gemini API key.
- **Groq (optional):** an API key, needed only if Whisper wins the STT spike.
- **Check at sign-up:** current rate limits, data-use terms, and whether a card is required. Free tiers change. Free LLM tiers may use inputs for training, so **use test personas only, never real artisans' voices** (see the consent and DPDP note in Architecture.md).
- **No account needed:** Wayback snapshots and the cloudflared quick tunnel.

## 7. Risks

| Risk | Mitigation |
|---|---|
| 10 days, solo, no slack beyond D10 | The approval gate runs end to end on D3. Strict cut rules (§3.3). SHOULD is unscheduled. |
| Tamil STT errors flow into the story | Choose the provider by WER on our clips. Read-back with Edit is part of the MUST path. |
| Too few comps, or comps spread too widely | Choose the craft from the data on D1. Use a narrow size bucket. Show low confidence honestly. |
| Comps self-verified (solo) | Use a second person if possible. Otherwise do a separate-day pass labelled as self-verified. |
| Marketplace terms of service | Collect by hand. Store minimal fields and link to the source. |
| Free-tier limits, terms changes or outages | Cache AI outputs for the demo personas. Record a backup video on D9. |
| Judges expect WhatsApp | Keep the adapter interface. Explain the choice in the README. |

## 8. Decisions and open questions
**Decided:** team size 1. Deadline Sun 6 Dec 2026. Gemini for vision and text. Telegram as the channel. Normal Telegram photos (compressed) are the default; images sent as files are also accepted, and those originals are kept.

**Open:**
1. Is there a second person who can verify the comps? If not, the D7 self-verification applies.
2. Confirm the deadline reading: 6 Dec 2026 (DD/MM/YY).
