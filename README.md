# CEO Copilot MVP

A private, local-first CEO assistant for Telegram task capture, reminders, daily briefings, AI suggestions, follow-up drafts, and GitLab engineering radar.

The intended operating mode is approval-first: the assistant drafts, summarizes, and suggests; you decide what to send or do.

## What It Does

- Capture tasks from Telegram messages like `/add Follow up with Ahmed tomorrow`
- Turn natural language into task fields using Ollama when available, with fallback parsing when AI is offline
- Send reminders through Telegram using Celery beat
- Generate a daily CEO briefing
- Suggest next actions with `/suggest`
- Draft follow-up wording with `/draft_followup`
- Check GitLab for stale issues, stale merge requests, and unassigned issues
- Show a local dashboard at `http://localhost:8000/`

## Stack

- Django 5
- PostgreSQL 16
- Redis 7
- Celery worker and beat
- Telegram Bot API
- Ollama for local AI
- GitLab REST API

## Required Local Apps

Install or enable these before running the full project:

- Docker Desktop
- Git
- Ollama, for AI extraction, briefings, suggestions, and drafts
- Optional: ngrok or Cloudflare Tunnel, only if you want Telegram to reach your local machine

## Quick Start

From this folder:

```bash
make setup
```

Then open:

```text
http://localhost:8000/
```

Other useful URLs:

- Dashboard: `http://localhost:8000/`
- Health check: `http://localhost:8000/healthz/`
- Admin: `http://localhost:8000/admin/`
- Telegram webhook health: `http://localhost:8000/telegram/webhook/`

## Environment Variables

Copy the example file if it does not exist:

```bash
cp .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=change-me
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgres://ceo:ceo@db:5432/ceo_copilot
REDIS_URL=redis://redis:6379/0

TELEGRAM_BOT_TOKEN=replace-me
TELEGRAM_ALLOWED_CHAT_ID=replace-with-your-telegram-chat-id

OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:0.5b

GITLAB_BASE_URL=https://gitlab.com
GITLAB_TOKEN=replace-me

BRIEFING_HOUR=8
BRIEFING_MINUTE=30
```

Do not commit `.env`. It contains private tokens.

## Try It Without Real Telegram

With the default placeholder Telegram token, the app will create tasks and return the bot reply as JSON without calling Telegram.

```bash
curl -X POST http://localhost:8000/telegram/webhook/ \
  -H 'Content-Type: application/json' \
  -d '{"message":{"chat":{"id":"replace-with-your-telegram-chat-id"},"text":"/add Follow up with Ahmed tomorrow"}}'
```

Refresh:

```text
http://localhost:8000/
```

You should see the created task.

## Telegram Setup

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`.
3. Choose a display name, for example `Nour CEO Copilot`.
4. Choose a bot username ending in `bot`.
5. Copy the bot token into `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:your-real-token
```

Get your private chat ID:

1. Send any message to your new bot.
2. Run:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates"
```

3. Find `message.chat.id`.
4. Put that value in `.env`:

```env
TELEGRAM_ALLOWED_CHAT_ID=123456789
```

Only this chat ID is authorized. Other Telegram chats receive `403 Unauthorized`.

Expose your local app so Telegram can reach it. Example with ngrok:

```bash
ngrok http 8000
```

Add the public hostname to `.env` without `https://`:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_PUBLIC_HOST
```

Recreate the app containers after changing `.env`:

```bash
make recreate
```

Set the Telegram webhook:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=https://YOUR_PUBLIC_URL/telegram/webhook/"
```

Check the webhook:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

## Ollama Setup

Install Ollama on the host machine, then run:

```bash
ollama pull qwen2.5:0.5b
ollama serve
```

Keep this in `.env` when running Django inside Docker:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:0.5b
```

Ollama is used for:

- extracting better task titles, category, priority, owner, and due date
- `/briefing`
- `/suggest`
- `/draft_followup`

If Ollama is unavailable, the project still works with simpler fallback parsing and raw summaries.

For better quality on a stronger machine, you can later pull `qwen2.5:7b` and change `OLLAMA_MODEL=qwen2.5:7b`.

Important: keep Ollama private. Do not expose port `11434` to the public internet.

## GitLab Setup

Create a GitLab personal access token with read-only API access:

1. In GitLab, open `User Settings -> Access Tokens`.
2. Create a token with `read_api`.
3. Copy it into `.env`:

```env
GITLAB_BASE_URL=https://gitlab.com
GITLAB_TOKEN=glpat-your-token
```

Add projects in Django admin:

1. Create an admin user:

```bash
make createsuperuser
```

2. Open:

```text
http://localhost:8000/admin/
```

3. Add a `GitLabIntegration` with:

- `project_name`: friendly name
- `gitlab_project_id`: GitLab numeric project ID, or URL-encoded path like `group%2Frepo`
- `repo_url`: optional
- `enabled`: checked

Then use:

```text
/gitlab
```

The radar checks open issues, stale issues older than 3 days, unassigned issues, open merge requests, and stale merge requests older than 2 days.

## Telegram Commands

```text
/help
/add Follow up with Ahmed tomorrow
/tasks
/today
/overdue
/done 12
/done Ahmed follow up
/cancel Ahmed follow up
/remove Ahmed follow up
/briefing
/suggest
/gitlab
/draft_followup
```

Plain messages are captured as tasks by default.
Action phrases like `remove the Ahmed follow up task` and `mark Hue integration done` are interpreted as task updates instead of new tasks.

## Daily Briefing And Reminders

Celery beat runs scheduled jobs:

- reminders: every minute, sends due reminders
- daily briefing: checks every minute and sends once at `BRIEFING_HOUR:BRIEFING_MINUTE`

Set the time in `.env`:

```env
BRIEFING_HOUR=8
BRIEFING_MINUTE=30
```

The timezone is configured as `Africa/Cairo` in Django settings.

## Common Commands

```bash
make up              # start existing containers
make build           # rebuild and start containers
make recreate        # recreate app containers after .env changes
make migrate         # run Django migrations
make test            # run Django tests
make check           # run Django system checks
make logs            # follow app logs
make createsuperuser # create an admin user
make down            # stop containers
```

## Recommended First Test

1. Run `make setup`.
2. Open `http://localhost:8000/`.
3. Create one task with the local curl command.
4. Run `/briefing` through the webhook curl or Telegram.
5. Run `/suggest`.
6. Add one GitLab integration in admin.
7. Run `/gitlab`.

## Security Notes

- Keep `.env` private.
- Use one allowed Telegram chat ID only.
- Use a GitLab token with the smallest required scope, preferably `read_api`.
- Do not expose Django admin publicly without proper production hardening.
- Do not expose Ollama publicly.
