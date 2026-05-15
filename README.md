# CEO Copilot MVP

Zero-subscription personal CEO assistant for task capture, reminders, daily briefing, Telegram commands, Ollama summaries, and GitLab radar.

## Quick start

```bash
cp .env.example .env
# edit .env with Telegram token/chat id, GitLab token if needed

docker compose up --build

docker compose exec web python manage.py migrate
```

## Telegram webhook

For local testing, use ngrok/cloudflared to expose `/telegram/webhook/`, then set webhook:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=https://YOUR_DOMAIN/telegram/webhook/"
```

## Commands

- `/help`
- `/add Follow up with Ahmed tomorrow`
- `/tasks`
- `/today`
- `/overdue`
- `/done 12`
- `/briefing`
- `/gitlab`
- `/draft_followup`

## Ollama

Install Ollama on the host machine and run:

```bash
ollama pull qwen2.5:7b
ollama serve
```

Keep Ollama private/local. Do not expose port 11434 publicly.
