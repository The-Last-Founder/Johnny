> **Status: unvalidated research.** Preserved from [PR #7](https://github.com/The-Last-Founder/Johnny/pull/7). This is not the canonical product spec. Validate architecture, model, pricing, and implementation claims before use.

# Johnny — AI Community Manager for "The Last Founders" Podcast
> ## Technical Specification & Build Guide
> 
> **Version:** 1.0 · **Date:** July 2026 · **Audience:** Semi-technical builder working with AI coding assistance
> 
> ---
> 
> ## 1. What Johnny Is
> 
> Johnny is a Telegram bot that acts as a community manager for The Last Founders podcast group. He:
> 
> 1. **Remembers** — maintains long-term, per-member memory of what people said, so conversations have continuity ("Sarah, you mentioned last month you were raising a seed round — how did it go?")
> 2. **Manages tasks** — tracks to-dos, reminders, and recurring duties that admins assign (post the new episode, run the weekly question thread, welcome new members)
> 3. **Assists** — answers questions about episodes and guests, moderates gently, onboards newcomers, and keeps the group alive
> 
> **Design principle:** Johnny listens to everything but speaks selectively. A bot that replies to every message is annoying and expensive. A bot that silently builds memory and speaks when addressed (or when a scheduled duty fires) feels like a real community manager.
> 
> ---
> 
> ## 2. Architecture Overview
> 
> ```
> Telegram Group
>      │  (all messages, via Bot API)
>      ▼
> ┌─────────────────────────────┐
> │  Bot Gateway (Python)       │  ← receives every message
> │  - filters & routes         │
> └──────┬───────────┬──────────┘
>        │           │
>   passive path   active path
>   (every msg)    (mentions, commands, scheduled tasks)
>        │           │
>        ▼           ▼
> ┌────────────┐  ┌──────────────────────┐
> │ Ingestion  │  │ Agent Loop (LLM)     │
> │ - store msg│  │ - assemble context   │
> │ - embed    │  │ - call Claude API    │
> │ - profile  │  │ - use tools          │
> └─────┬──────┘  └─────┬────────────────┘
>       │               │
>       ▼               ▼
> ┌─────────────────────────────┐
> │ PostgreSQL + pgvector       │
> │ messages · summaries ·      │
> │ user profiles · tasks ·     │
> │ episode knowledge base      │
> └─────────────────────────────┘
> ```
> 
> Two paths, deliberately separated:
> 
> - **Passive path** (cheap, runs on *every* message): store the message, queue it for embedding and profile updates. No LLM call per message.
> - **Active path** (expensive, runs *only when triggered*): mention of Johnny, reply to Johnny, a `/command`, or a scheduled task. This is where the LLM runs.
> 
> This split is the single most important cost/quality decision in the whole system — see §5.
> 
> ---
> 
> ## 3. Stack Choices & Why
> 
> ### 3.1 Telegram framework: **Python + aiogram**
> 
> | Option | Verdict |
> |---|---|
> | **aiogram (Python)** ✅ | Async-native, actively maintained, excellent group-chat support, huge community. Python is also the best language for AI-assisted development — Claude/Copilot generate the most reliable code in it, and every AI/data library you'll need is Python-first. |
> | python-telegram-bot | Fine alternative, slightly more beginner-friendly docs. Either works; aiogram's async model fits a bot that does background embedding work better. |
> | grammY (TypeScript) | Excellent framework, but pulls you into the Node ecosystem for no benefit here. |
> | No-code (Zapier/Make/n8n) | Can't do per-member memory, RAG, or an agent loop properly. Fine for prototyping a single feature, dead end for Johnny. |
> 
> **Why not the official Bot API directly?** You'd re-implement update polling, rate-limit handling, and message parsing that aiogram gives you for free.
> 
> ### 3.2 Critical Telegram constraint you must know upfront
> 
> Telegram bots have **privacy mode ON by default** — they only see commands, not ordinary messages. For Johnny to remember what everyone says, you must either **disable privacy mode via @BotFather** or (better) **make Johnny a group admin**, which lets him see all messages regardless of the setting. Two hard limits with no workaround:
> 
> - **No history before joining.** Bots cannot read messages sent before they were added. Johnny's memory starts the day he joins.
> - **Bots can't see other bots' messages.** If your group uses other bots, their output is invisible to Johnny.
> 
> Plan for these: add Johnny early, and don't design features that depend on reading another bot's posts.
> 
> ### 3.3 LLM: **Claude Haiku 4.5 (workhorse) + Claude Sonnet 5 (escalation)**
> 
> Recommended two-tier setup:
> 
> | Role | Model | Price (per 1M tokens in/out) | Used for |
> |---|---|---|---|
> | Workhorse (~90% of calls) | **Claude Haiku 4.5** | $1 / $5 | Replies, summaries, profile updates, classification |
> | Escalation | **Claude Sonnet 5** | $3 / $15 (intro $2/$10 through Aug 31, 2026) | Complex questions, weekly digests, nuanced moderation calls |
> 
> **Why Claude over OpenAI (GPT-5.6 family, Luna at $1/$6):** pricing is comparable at the low tier, so the decision rests on three things that matter specifically for Johnny: (1) **prompt caching** — Anthropic's cache-hit pricing is 10% of base input cost, and Johnny's prompt is dominated by a large static block (persona + podcast knowledge + group rules) that gets re-sent on every call, so caching cuts your real input bill dramatically; (2) **tone** — Claude models are consistently strong at warm, non-robotic community voice, which is Johnny's entire job; (3) **long-context handling** for stuffing summaries and retrieved memories into prompts. If you already have OpenAI credits or preferences, the architecture is identical — swap the API client.
> 
> **Why two tiers instead of one good model:** a community bot makes many small calls. Haiku-class models handle "answer this question using these retrieved facts" perfectly well; paying Sonnet prices for "welcome @newuser" is waste. Route by trigger type (commands and simple mentions → Haiku; digest generation and multi-step reasoning → Sonnet).
> 
> **Why not open-source/self-hosted:** running a Llama-class model well requires GPU hosting that costs more per month than Johnny's entire expected API bill (see §9), plus ops burden. Only worth it if data-sovereignty is a hard requirement.
> 
> ### 3.4 Database: **PostgreSQL + pgvector** (one database for everything)
> 
> - **Why Postgres:** you need relational data anyway (users, tasks, messages, settings). Battle-tested, free, every host offers it.
> - **Why pgvector instead of Pinecone/Weaviate/Chroma:** a dedicated vector DB adds a second service to run, sync, and pay for. At community scale (thousands–hundreds of thousands of messages, not billions), pgvector's performance is indistinguishable, and keeping vectors next to relational data lets you do hybrid queries in one place ("messages from *this user* in *the last 90 days* similar to *this query*") — which is exactly the query shape memory retrieval needs. Migrate to a dedicated vector DB only if you someday exceed ~1M+ vectors with latency problems. You won't soon.
> - **Embeddings:** any cheap embedding API (e.g., Voyage or OpenAI `text-embedding-3-small`). Embedding cost is negligible — fractions of a cent per thousand messages.
> 
> ### 3.5 Agent framework: **thin custom loop, not LangChain**
> 
> Write the agent loop yourself (~200 lines): assemble context → call Claude with tool definitions → execute tool calls → return reply. Claude's native tool-use API does the heavy lifting.
> 
> **Why not LangChain/LlamaIndex:** heavy abstractions that obscure what's in your prompt — and for Johnny, *controlling exactly what goes into the prompt is the whole game* (§5). Frameworks earn their keep in multi-agent pipelines; a single bot with 6–8 tools doesn't need one. The Claude Agent SDK is a reasonable middle ground if you want managed tool-loops, but a thin custom loop keeps you in full control and is easy for an AI assistant to help you debug.
> 
> ### 3.6 Hosting: **small VPS or PaaS**
> 
> - **Railway / Fly.io** (~$5–10/mo): easiest — git push to deploy, managed Postgres add-on. Recommended for you.
> - **Hetzner/DigitalOcean VPS** (~$5/mo): cheaper at steady state, more setup.
> - Long polling (bot asks Telegram for updates) rather than webhooks to start — no public HTTPS endpoint or certificate needed, one less thing to break. Switch to webhooks only if latency ever matters.
> - **Not serverless** (Lambda/Cloud Functions): Johnny needs a persistent process for polling, scheduled jobs, and background embedding. Serverless fights you on all three.
> 
> ### 3.7 Scheduler: **APScheduler** (in-process)
> 
> Runs admin-defined recurring tasks (weekly threads, episode reminders, digest generation) inside the bot process. No need for Celery/Redis at this scale — that's infrastructure for problems you don't have.
> 
> ---
> 
> ## 4. Data Model (core tables)
> 
> ```sql
> users        (tg_user_id, username, display_name, first_seen, role)  -- role: member/admin
> messages     (id, tg_msg_id, user_id, chat_id, text, reply_to, ts, embedding vector(1536))
> summaries    (id, chat_id, period_start, period_end, level, text, embedding)
>              -- level: 'daily' | 'weekly' | 'monthly'
> profiles     (user_id, facts jsonb, updated_at, embedding)
>              -- facts: {"startup": "fintech, pre-seed", "asked_about": ["hiring"], ...}
> tasks        (id, title, details, assignee, created_by, due_at, recur_rule, status)
> kb_chunks    (id, episode_no, title, chunk_text, embedding)  -- podcast knowledge base
> settings     (key, value)  -- persona tweaks, quiet hours, feature flags
> ```
> 
> ---
> 
> ## 5. Context Management — The Core Problem
> 
> This is the hardest part of the project, so it gets the most detail.
> 
> ### 5.1 The technical limitations you're designing around
> 
> 1. **Context windows are finite and cost scales with tokens.** Claude's window (200K+) sounds huge, but an active group produces hundreds of messages a day — months of history is millions of tokens. You *cannot* and *should not* stuff raw history into prompts. Every input token costs money on every call, and LLM answer quality degrades when relevant facts drown in noise ("lost in the middle").
> 2. **Group chat ≠ 1:1 chat.** Almost all LLM chat tooling assumes one user and one linear conversation. A Telegram group is dozens of interleaved conversations from many people. "Conversation history" as a concept breaks; you need memory *about people and topics*, not a transcript replay.
> 3. **The bot has no memory between calls.** Every LLM call starts blank. Johnny's "memory" is entirely what *you* choose to retrieve from the database and place in the prompt. Memory quality = retrieval quality.
> 4. **No pre-join history** (§3.2): the corpus starts from day one of deployment.
> 
> ### 5.2 The solution: layered memory with tiered compression
> 
> Think of it as three storage layers, from raw to distilled, plus retrieval that pulls from all three:
> 
> **Layer 1 — Raw messages (verbatim, embedded).**
> Every message is stored with its embedding. Never sent to the LLM in bulk — used only for (a) the short-term buffer and (b) semantic retrieval hits. Raw messages are ground truth; everything else is derived and can be rebuilt.
> 
> **Layer 2 — Rolling summaries (episodic memory).**
> A nightly Haiku job (via the Batch API — 50% discount, since latency doesn't matter overnight) compresses each day's messages into a ~150-token summary: topics discussed, decisions made, notable moments, who was active. Weekly jobs compress dailies into weeklies; monthly compresses weeklies. **Why hierarchical:** it gives Johnny a logarithmic view of time — fine detail about yesterday, coarse detail about last quarter — mirroring how a human community manager actually remembers. Six months of group life compresses to a few thousand tokens.
> 
> **Layer 3 — User profiles (semantic memory).**
> The same nightly job extracts *durable facts* per active user into a structured profile: what they're building, what they've asked for, expertise, wins they've shared. Capped at ~200 tokens per person, updated (not appended — old facts get revised or dropped) each run. **Why profiles instead of relying on retrieval alone:** when Sarah asks a question, retrieval finds messages *similar to her question*, but the most useful context is often *who Sarah is* — which lives in no single message. Profiles are precomputed answers to "who is this person?", which retrieval can't reliably reconstruct on the fly.
> 
> ### 5.3 Retrieval (RAG) at reply time
> 
> When Johnny is triggered, the context assembler runs **hybrid search** — vector similarity (pgvector) + keyword full-text (Postgres `tsvector`), merged. **Why hybrid:** embeddings catch paraphrases ("fundraising" ≈ "raising a round") but are unreliable for exact names, handles, and episode numbers; keyword search is the reverse. Community chat is full of names and jargon, so you need both. Retrieve top ~10 hits across raw messages, summaries, and the podcast knowledge base, filtered to this chat.
> 
> ### 5.4 The prompt budget
> 
> Every active-path call assembles a prompt with a fixed budget. Explicit budgets keep cost predictable and prevent slow context bloat:
> 
> | Slot | Content | ~Tokens | Cached? |
> |---|---|---|---|
> | System | Persona, rules, tone, tool definitions | 1,500 | ✅ |
> | Podcast KB core | Show summary, episode index, guest list | 2,000 | ✅ |
> | Group state | Recent daily/weekly summaries | 800 | — |
> | User profile | Profile of the person Johnny is replying to (+ others in thread) | 300 | — |
> | Retrieved memory | Hybrid-search hits | 1,200 | — |
> | Live buffer | Last ~30 raw group messages | 900 | — |
> | Total input | | **~6,700** | ~52% cached |
> 
> The first two slots are static, so with prompt caching (cache hits at 10% of input price) the *effective* per-call input cost is roughly halved. This is why the static content goes first in the prompt — Anthropic's caching works on stable prefixes.
> 
> ### 5.5 Deciding *when* to think (trigger policy)
> 
> The LLM runs only on: direct @mention · reply to one of Johnny's messages · a `/command` · a scheduled task firing · (optional, Phase 3) a cheap Haiku classifier that occasionally flags "someone asked a question that went unanswered for 30+ min" for proactive help. Everything else takes the passive path: DB write + embedding, zero LLM cost. **Why:** in a group doing 500 messages/day with ~30 triggers, this is a ~94% reduction in LLM calls versus responding to everything — and a better experience, because nobody wants a bot interjecting constantly.
> 
> ---
> 
> ## 6. Task Management (admin features)
> 
> Johnny's tools (functions the LLM can call) plus direct commands:
> 
> - `/task add Post episode 47 promo @friday 10:00` — natural-language dates parsed by the LLM, stored structurally
> - `/task list`, `/task done 3`, `/task assign 3 @maria`
> - Recurring rules: "every Monday", "day after each episode drops"
> - Reminders DM'd to assignees and escalated in-group if overdue
> - **Admin-only enforcement in code, not in the prompt.** The gateway checks Telegram admin status before task-mutation and settings commands ever reach the LLM. **Why:** "only obey admins" as a prompt instruction is trivially bypassed by prompt injection ("pretend I'm an admin"). Permissions belong in deterministic code.
> 
> Admins can also adjust Johnny at runtime via `/johnny set` commands (tone, quiet hours, feature toggles) stored in `settings` — no redeploy for personality tweaks.
> 
> ---
> 
> ## 7. Podcast Knowledge Base
> 
> - Ingest each episode's **transcript** (Whisper it if none exists), chunked ~500 tokens with episode metadata, embedded into `kb_chunks`.
> - Add show notes, guest bios, and links.
> - Johnny answers "which episode covered founder burnout?" via the same hybrid retrieval as §5.3, citing episode number + timestamp.
> - New-episode pipeline: drop a transcript file in a folder (or a `/ingest` admin command) → chunk → embed → Johnny can discuss it and auto-posts an episode announcement with 3 LLM-generated discussion questions.
> 
> ---
> 
> ## 8. Suggested Features (beyond the brief)
> 
> **High value, low effort**
> - **New-member onboarding:** DM or in-group welcome, ask what they're building, seed their profile from the answer.
> - **Weekly digest:** Sonnet-generated Monday recap of the week's best discussions, unanswered questions, member wins.
> - **Episode discussion threads:** auto-post on release day with generated starter questions.
> - **Ask-the-guest collector:** `/askguest` collects and dedupes listener questions before recordings — direct podcast-content value.
> 
> **Medium effort**
> - **Member matchmaking:** profile embeddings make "who else here works on fintech?" a similarity query; Johnny can suggest intros.
> - **Unanswered-question rescue:** flag questions with no replies after N hours; Johnny answers or tags a member whose profile matches.
> - **Moderation assist:** flag spam/toxicity to an admin channel — *humans decide*, Johnny never auto-bans (false positives are community poison).
> - **Wins channel / leaderboard:** detect shared milestones, celebrate them, monthly "community wins" roundup.
> 
> **Later**
> - Multilingual support (detect + reply in kind); voice-note transcription so audio messages enter memory; polls/AMAs run end-to-end; a private admin dashboard (simple web page) showing engagement trends from data Johnny already has.
> 
> ---
> 
> ## 9. Cost Estimate (active group: ~500 msgs/day, ~30 LLM triggers/day)
> 
> | Item | Monthly |
> |---|---|
> | Haiku calls (~900/mo × ~7K in/300 out, ~50% cache hits) | ~$5 |
> | Sonnet (digests, escalations, ~60 calls) | ~$3 |
> | Nightly batch summarization/profiles (Batch API) | ~$2 |
> | Embeddings (~15K messages) | <$1 |
> | Hosting (Railway + Postgres) | ~$10 |
> | **Total** | **~$20/mo** |
> 
> Scales roughly linearly with trigger count, not message count — which is the point of the passive/active split.
> 
> ---
> 
> ## 10. Build Roadmap
> 
> **Phase 1 — Listener (week 1–2):** aiogram bot as group admin; store + embed all messages; `/ping`. *No LLM yet.* Memory accumulates from day one — ship this first precisely because history can't be backfilled.
> 
> **Phase 2 — Speaker (week 2–4):** agent loop with context assembler (§5.4); responds to mentions/replies; podcast KB ingestion; prompt caching on.
> 
> **Phase 3 — Manager (week 4–6):** task system + scheduler; nightly summarization + profile jobs; onboarding flow; weekly digest.
> 
> **Phase 4 — Polish (ongoing):** matchmaking, question rescue, moderation assist, admin settings, dashboard.
> 
> Each phase is independently useful — you can stop anywhere and still have a working bot.
> 
> ---
> 
> ## 11. Security & Safety Checklist
> 
> - **Prompt injection:** members *will* try "ignore your instructions." Mitigations: permissions in code (§6); Johnny's tools scoped to least privilege (no arbitrary Telegram admin powers like banning); treat all message content as untrusted data, clearly delimited in the prompt.
> - **Secrets:** bot token + API keys in environment variables, never in code or the repo.
> - **Privacy:** Johnny stores members' messages — say so in the group description/pinned rules. Provide `/forgetme` to delete a user's messages and profile. Don't leak one member's profile facts to another unless they were said publicly in this group (they were, by construction — but keep DM memory separate if you add DMs).
> - **Rate limiting:** cap Johnny to ~20 messages/min (Telegram limit) and add a per-user cooldown on triggering him, so nobody can run up your API bill by spamming mentions.
> - **Kill switch:** `/johnny mute 2h` for admins.
> 
> ---
> 
> ## 12. Sources
> 
> - [Telegram Bot API](https://core.telegram.org/bots/api) · [Telegram Bot Features](https://core.telegram.org/bots/features) — privacy mode, admin visibility, limits
> - [TeleMe: group privacy mode](https://www.teleme.io/articles/group_privacy_mode_of_telegram_bots?hl=en)
> - [Anthropic API pricing (TLDL, July 2026)](https://www.tldl.io/resources/anthropic-api-pricing) · [UsageBox rate card](https://usagebox.com/articles/api-usage-billing-claude-limits)
> - [OpenAI API pricing (TLDL, July 2026)](https://www.tldl.io/resources/openai-api-pricing)
>
