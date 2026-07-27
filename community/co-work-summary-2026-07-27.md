# Johnny co-work summary, 27 July 2026

Today we moved Johnny from a spec toward a working first prototype:

- Set up the Telegram bot, test bot, and test group. Johnny responds when tagged in the group and directly in DMs. Testing confirmed that Telegram does not give bots earlier group history, so future memory can only start after Johnny joins.
- Made GitHub and Markdown the source of truth: added the project backlog in [`tasks.md`](../tasks.md), editable behavior and system-prompt configuration in [`memory/johnny.md`](../memory/johnny.md), project scope in [`memory/project.md`](../memory/project.md), and initial podcast [guest](../podcast/guests.md) and [topic](../podcast/topics.md) queues.
- Merged the Telegram “Hello World” implementation. Johnny now loads its behavior, project context, and [`memory/tasks.md`](../memory/tasks.md) when answering, so its prompt and scope can change without code changes.
- Stored an [unvalidated architecture proposal](../research/johnny-ai-community-manager-architecture.md) for selective replies, long-term memory, and future task management.
- Agreed on a revised roadmap: build on Telegram now while pursuing access to Yaniv’s WhatsApp version, connect to WhatsApp early, improve the system prompt as an early task, and treat task management as the 1.0 milestone.
