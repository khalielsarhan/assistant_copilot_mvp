# CEO Copilot MVP

A local-first Django project for task capture, reminders, daily briefings, Telegram commands, Ollama summaries, and GitLab radar.

## Stack

- Django 5
- PostgreSQL 16
- Redis 7
- Celery worker and beat
- Ollama for local AI summaries
- Telegram webhook command interface

## Quick Start

```bash
make setup
```

Then open:

```text
http://localhost:8000/
```

The setup command copies `.env.example` to `.env` if needed, builds the Docker services, starts the stack, and runs migrations.

## Common Commands

```bash
make up              # start existing containers
make build           # rebuild and start containers
make migrate         # run Django migrations
make test            # run Django tests
make check           # run Django system checks
make logs            # follow app logs
make createsuperuser # create an admin user
make down            # stop containers
```

## Local URLs

- Dashboard: `http://localhost:8000/`
- Health check: `http://localhost:8000/healthz/`
- Admin: `http://localhost:8000/admin/`
- Telegram webhook: `http://localhost:8000/telegram/webhook/`

## Try The Webhook Locally

With the default `.env.example` values, this creates a task without calling Telegram:

```bash
curl -X POST http://localhost:8000/telegram/webhook/ \
  -H 'Content-Type: application/json' \
  -d '{"message":{"chat":{"id":"replace-with-your-telegram-chat-id"},"text":"/add Follow up with Ahmed tomorrow"}}'
```

Refresh `http://localhost:8000/` and the task should appear in the dashboard.

## Telegram Commands

- `/help`
- `/add Follow up with Ahmed tomorrow`
- `/tasks`
- `/today`
- `/overdue`
- `/done 12`
- `/briefing`
- `/gitlab`
- `/draft_followup`

For real Telegram usage, edit `.env`:

```env
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_ALLOWED_CHAT_ID=your-chat-id
```

Expose the local app with ngrok or cloudflared, then set the webhook:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=https://YOUR_DOMAIN/telegram/webhook/"
```

## Ollama

Install Ollama on the host machine and run:

```bash
ollama pull qwen2.5:7b
ollama serve
```

The Docker app reads Ollama through:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b
```

Keep Ollama private/local. Do not expose port 11434 publicly.
