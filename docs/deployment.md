# Free Always-On Deployment

The practical zero-cost deployment target for this MVP is an Oracle Cloud Always Free Ampere A1 VM running Docker, PostgreSQL, Redis, Celery, the Telegram long-polling process, and Ollama.

This production path uses Telegram long polling, not webhooks. That means the bot can work without a domain, HTTPS certificate, ngrok, or Cloudflare Tunnel. The Django dashboard stays bound to `127.0.0.1:8000` on the VM and can be viewed through an SSH tunnel.

## Why Oracle Always Free

Oracle documents Always Free Ampere A1 resources as up to 3,000 OCPU hours and 18,000 GB hours per month, equivalent to 4 OCPUs and 24 GB RAM for Always Free tenancies. That is enough for this small Django stack and a small Ollama model.

Official reference:

- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

## 1. Create The VM

Create an Oracle Cloud Ubuntu VM:

- Shape: `VM.Standard.A1.Flex`
- OCPUs: `2` minimum, `4` preferred if available
- Memory: `8 GB` minimum, `16-24 GB` preferred
- Image: Ubuntu 24.04 or 22.04
- Boot volume: 50 GB or more
- Add your SSH public key

If Oracle shows an out-of-capacity error, try another availability domain or retry later.

## 2. Install Runtime Packages On The VM

SSH into the VM, then run:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git make

curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
```

Log out and back in so Docker group membership applies.

Install Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:0.5b
sudo systemctl enable --now ollama
```

Keep Ollama private. Do not open port `11434` to the public internet.

## 3. Clone And Configure

```bash
git clone https://github.com/khalielsarhan/assistant_copilot_mvp.git
cd assistant_copilot_mvp
cp .env.production.example .env.production
```

Generate a Django secret:

```bash
docker run --rm python:3.12-slim python - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
```

Edit `.env.production`:

```env
SECRET_KEY=the-generated-secret
DEBUG=false
POSTGRES_PASSWORD=strong-password
DATABASE_URL=postgres://ceo:strong-password@db:5432/ceo_copilot
TELEGRAM_BOT_TOKEN=your-rotated-token
TELEGRAM_ALLOWED_CHAT_ID=your-chat-id
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:0.5b
```

Rotate the Telegram bot token before production if it was ever pasted into chat or committed anywhere.

## 4. Start Production Services

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d
docker compose -f docker-compose.prod.yml --env-file .env.production exec web python manage.py migrate
docker compose -f docker-compose.prod.yml --env-file .env.production exec web python manage.py collectstatic --noinput
```

Check containers:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f telegram-poller celery celery-beat
```

The bot should now answer in Telegram even when your laptop is off, as long as the Oracle VM is running.

## 5. View The Dashboard

From your laptop:

```bash
ssh -L 8000:127.0.0.1:8000 ubuntu@YOUR_VM_PUBLIC_IP
```

Then open:

```text
http://localhost:8000/
```

## 6. Useful Production Commands

```bash
make prod-up
make prod-migrate
make prod-logs
make prod-status
make prod-down
```
