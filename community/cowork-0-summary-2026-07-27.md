**TLDR: Cowork 0 produced a working Telegram prototype, editable Markdown context, a prioritized task board, preserved architecture research, and a focused path to task-managing Johnny 1.0.**

# Johnny Cowork 0 summary, 27 July 2026

1. **A working Telegram sandbox.** We set up the bot, test bot, and test group, then verified that Johnny answers tagged or replied-to group messages and every DM through Claude.

2. **A crucial memory limit discovered.** Testing confirmed Johnny cannot see group messages from before it joined, so its history must accumulate from deployment onward.

3. **An editable, reproducible prototype.** [PR #3](https://github.com/The-Last-Founder/Johnny/pull/3) merged the bot, dependency and environment templates, run instructions, and [`memory/johnny.md`](../memory/johnny.md) plus [`memory/project.md`](../memory/project.md), which let contributors change behavior and scope without editing code.

4. **The first prioritized backlog and podcast queues.** We created and prioritized root [`tasks.md`](../tasks.md), loaded [`memory/tasks.md`](../memory/tasks.md) into Johnny's context, and moved the [guest](../podcast/guests.md) and [topic](../podcast/topics.md) queues into `podcast/` to separate generic and podcast state.

5. **Architecture research preserved, not adopted.** We stored the [unvalidated proposal](../research/johnny-ai-community-manager-architecture.md) under `research/`, covering selective replies, long-term memory, and future task management.

6. **A smaller roadmap agreed.** We chose Telegram first while pursuing access to Yaniv's WhatsApp version in parallel, planned early WhatsApp connectivity and system-prompt work, and defined task management as the 1.0 milestone.

## Candidates / unresolved

1. **Count the late task-board cleanup?** [PR #9](https://github.com/The-Last-Founder/Johnny/pull/9) was opened on July 27 and added `Critical now`, editing rules, and T-005/T-006 completion, but it merged on July 28 and may belong outside Cowork 0.

2. **Choose one canonical task file.** Root [`tasks.md`](../tasks.md) is intended as the source of truth, but [`bot.py`](../bot.py) still loads [`memory/tasks.md`](../memory/tasks.md), and their contents differ.

3. **Reconcile the written roadmap and status.** [`SPEC.md`](../SPEC.md) still contains the old version breakdown, and [`tasks.md`](../tasks.md) still marks T-002 Open despite the bot and group test being completed.
