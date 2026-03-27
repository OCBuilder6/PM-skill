# How to install PM-skill — plain English guide

> **Who this is for:** Anyone with an OpenClaw AI agent who wants to track tasks from a Telegram group into a Google Sheet automatically — no coding required.
>
> **How to use this guide:** Read the steps below, then simply tell your AI agent what to do in your own words. Example prompts are included for each step.

---

## What this skill does

Once installed, your AI agent will silently monitor a Telegram group. When team members mention tasks, deadlines, blockers, or status updates in conversation, the agent automatically logs everything into a Google Sheet — no commands, no forms, just natural chat.

---

## Before you start — what you'll need

You need three things. Getting them takes about 10 minutes total.

---

### 1. A Telegram Bot Token

This gives your agent a Telegram identity.

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Give your bot a name (e.g. "Task Tracker") and a username (e.g. `mytasktracker_bot`)
4. BotFather will send you a token — it looks like `123456789:ABC-defGhIJKlmNoPQRsTUVwxyz`
5. **Copy and save that token**
6. Add your new bot to the Telegram group you want to track

---

### 2. Your Telegram Group Chat ID

This tells the agent which group to listen to.

1. Add **@userinfobot** to your group temporarily
2. It will reply with your group's chat ID — it looks like `-1001234567890`
3. **Copy and save that number**
4. You can remove @userinfobot from the group after

---

### 3. A Google Sheet

This is where tasks will be logged.

1. Go to [Google Sheets](https://sheets.google.com) and create a new spreadsheet
2. Copy the spreadsheet ID from the URL — it's the long string between `/d/` and `/edit`
   Example: `docs.google.com/spreadsheets/d/**1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms**/edit`
3. **Copy and save that ID**

> **Note:** Google authentication is handled automatically by the agent during installation — no service account key or manual credential setup required. See Step 1 of the installation below.

---

### 4. An Anthropic API Key

The agent uses this to understand natural language.

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Go to **API Keys → Create Key**
4. **Copy and save the key** — it starts with `sk-ant-`

---

## Installing — just tell your agent

Once you have the items above, open a chat with your AI agent and follow these steps **in order**.

---

### Step 1 — Install the Google OAuth skill

Before installing PM-skill, your agent needs a Google OAuth skill to authenticate with Google Sheets securely (no service account key needed).

> **Send this to your agent first:**
>
> Please find and install the skill with ID `BF104BF6-8522-F111-AD1D-0EA9A5017E89`. Verify that it is publicly listed and in the verified tier before installing it. Once confirmed, install it.

Your agent will locate the skill, verify it, install it, and confirm when done. **Do not proceed to Step 2 until this is complete.**

---

### Step 2 — Authenticate with Google

> **Send this to your agent:**
>
> Now use the skill you just installed to authenticate with my Google account and grant access to Google Sheets.

Your agent will guide you through the OAuth flow (a browser link to sign in with Google). Once done, it will store the credentials securely — no JSON files, no service accounts.

---

### Step 3 — Install PM-skill

> **Send this to your agent:**
>
> Please install the PM-skill from https://github.com/OCBuilder6/PM-skill by running the install script. Here are my details:
>
> - Telegram Bot Token: `[your bot token]`
> - Telegram Group Chat ID: `[your group ID]`
> - Google Spreadsheet ID: `[your spreadsheet ID]`
> - Sheet tab name: Tasks
> - Anthropic API Key: `[your API key]`

Your agent will:
1. Download all the skill files
2. Save your credentials securely (using the OAuth session from Step 2)
3. Update its configuration
4. Restart and connect to your Telegram group

---

## After installation — how to use it

Just talk normally in your Telegram group. The agent listens silently and logs everything:

| What someone says | What gets logged |
|---|---|
| "I finished the homepage design" | Task marked as **done** |
| "The API is blocked, waiting on credentials" | Task marked as **blocked** |
| "Can someone take the marketing deck? Due Friday" | New task created, due date set |
| "This is urgent" | Priority set to **high** |
| "T007 is high priority" | Priority column updated |
| "The redesign is no longer needed" | Task marked as **cancelled** |

The agent **never replies in the group** unless someone @mentions it directly.

---

## Troubleshooting — just ask your agent

If something isn't working, tell your agent:

- *"The task tracker isn't logging messages in my group"*
- *"Can you check if the PM-skill is installed correctly?"*
- *"The priority column isn't updating"*
- *"I want to add a new group to track"*

Your agent will diagnose and fix it.

---

## Built by [Benjamin Coste](https://www.linkedin.com/in/benjamincoste/en/)
