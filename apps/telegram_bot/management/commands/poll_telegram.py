import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.telegram_bot.client import delete_webhook, get_updates, send_message
from apps.telegram_bot.views import _authorized, handle_message


class Command(BaseCommand):
    help = 'Run the Telegram bot with long polling instead of a public webhook.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--drop-webhook',
            action='store_true',
            help='Delete the active Telegram webhook before polling.',
        )
        parser.add_argument(
            '--drop-pending-updates',
            action='store_true',
            help='Ask Telegram to discard queued updates when deleting the webhook.',
        )

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == 'replace-me':
            self.stderr.write('TELEGRAM_BOT_TOKEN is not configured.')
            return

        if options['drop_webhook']:
            delete_webhook(drop_pending_updates=options['drop_pending_updates'])
            self.stdout.write('Telegram webhook deleted. Starting long polling.')

        offset = None
        while True:
            try:
                updates = get_updates(offset=offset, timeout=30)
                for update in updates:
                    offset = update['update_id'] + 1
                    if 'edited_message' in update and 'message' not in update:
                        continue
                    message = update.get('message') or {}
                    chat = message.get('chat') or {}
                    chat_id = str(chat.get('id', ''))
                    if not _authorized(chat_id):
                        continue
                    reply = handle_message(chat_id, message.get('text', ''))
                    send_message(chat_id, reply[:3900])
            except Exception as exc:
                self.stderr.write(f'Telegram polling error: {exc}')
                time.sleep(5)
