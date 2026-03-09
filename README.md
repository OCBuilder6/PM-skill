# PM-skill

AI-powered Telegram task tracker skill for [OpenClaw](https://openclaw.ai).

Monitors a Telegram group and automatically syncs task updates to a Google Sheet — no commands, just natural conversation.

## Quick start

See [`PM-skill/DEV_CONTEXT.md`](PM-skill/DEV_CONTEXT.md) for full setup, architecture, and install instructions.

## What's inside

```
PM-skill/
├── SKILL.md          ← Agent instructions
├── AGENTS.md         ← Operating rules
├── agent.py          ← Core logic + workspace binding
├── skill.json        ← Skill descriptor
├── requirements.txt  ← Python deps
├── DEV_CONTEXT.md    ← Full developer context & handoff doc
└── tools/
    ├── sheets.py     ← Google Sheets CRUD
    ├── intent.py     ← LLM intent parser
    └── telegram.py   ← Telegram send helpers
```

## Version

`v1.1.0`
