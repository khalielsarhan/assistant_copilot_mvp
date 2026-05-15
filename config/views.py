from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.html import escape
from django.utils import timezone

from apps.reminders.models import Reminder
from apps.tasks.models import Task


def home(request):
    open_count = Task.objects.filter(status=Task.Status.OPEN).count()
    waiting_count = Task.objects.filter(status=Task.Status.WAITING).count()
    done_count = Task.objects.filter(status=Task.Status.DONE).count()
    due_count = Task.objects.filter(
        status__in=[Task.Status.OPEN, Task.Status.WAITING],
        due_date__lte=timezone.now().replace(hour=23, minute=59, second=59, microsecond=0),
    ).count()
    reminder_count = Reminder.objects.filter(status=Reminder.Status.PENDING).count()
    recent_tasks = Task.objects.order_by("-created_at")[:5]

    task_rows = "".join(
        f"""
        <tr>
          <td>#{task.id}</td>
          <td>{escape(task.title)}</td>
          <td>{task.status}</td>
          <td>{task.category}</td>
          <td>{task.due_date.strftime("%Y-%m-%d %H:%M") if task.due_date else "No due date"}</td>
        </tr>
        """
        for task in recent_tasks
    ) or '<tr><td colspan="5">No tasks yet. Try the sample webhook request below.</td></tr>'

    html = f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>CEO Copilot MVP</title>
        <style>
          :root {{
            color-scheme: light;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: #172026;
            background: #f5f7f8;
          }}
          body {{ margin: 0; }}
          main {{ max-width: 980px; margin: 0 auto; padding: 40px 20px; }}
          header {{ display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; margin-bottom: 28px; }}
          h1 {{ margin: 0 0 8px; font-size: 32px; line-height: 1.1; letter-spacing: 0; }}
          p {{ margin: 0; color: #51606a; line-height: 1.5; }}
          a {{ color: #0f6b5f; font-weight: 650; text-decoration: none; }}
          a:hover {{ text-decoration: underline; }}
          .status {{ padding: 8px 12px; border: 1px solid #bdd9d3; border-radius: 6px; background: #e9f6f3; color: #0f5d53; font-weight: 700; white-space: nowrap; }}
          .grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin: 24px 0; }}
          .metric, .panel {{ background: #fff; border: 1px solid #dce3e7; border-radius: 8px; box-shadow: 0 1px 2px rgba(20, 30, 35, .04); }}
          .metric {{ padding: 16px; }}
          .metric strong {{ display: block; font-size: 28px; line-height: 1; margin-bottom: 8px; }}
          .metric span {{ color: #60707a; font-size: 13px; }}
          .panel {{ padding: 18px; margin-top: 16px; }}
          h2 {{ margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }}
          table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
          th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid #edf1f3; vertical-align: top; }}
          th {{ color: #60707a; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
          code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
          pre {{ margin: 0; overflow-x: auto; background: #101820; color: #eef6f7; padding: 14px; border-radius: 6px; font-size: 13px; line-height: 1.45; }}
          .links {{ display: flex; gap: 14px; flex-wrap: wrap; margin-top: 12px; }}
          @media (max-width: 760px) {{
            header {{ display: block; }}
            .status {{ display: inline-block; margin-top: 14px; }}
            .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
          }}
        </style>
      </head>
      <body>
        <main>
          <header>
            <div>
              <h1>CEO Copilot MVP</h1>
              <p>Task capture, reminders, briefing, Telegram commands, Ollama summaries, and GitLab radar.</p>
              <div class="links">
                <a href="{reverse("admin:index")}">Django admin</a>
                <a href="{reverse("telegram_webhook")}">Telegram webhook health</a>
              </div>
            </div>
            <div class="status">Running on port 8000</div>
          </header>

          <section class="grid" aria-label="Current counts">
            <div class="metric"><strong>{open_count}</strong><span>Open tasks</span></div>
            <div class="metric"><strong>{waiting_count}</strong><span>Waiting tasks</span></div>
            <div class="metric"><strong>{due_count}</strong><span>Due today</span></div>
            <div class="metric"><strong>{reminder_count}</strong><span>Pending reminders</span></div>
            <div class="metric"><strong>{done_count}</strong><span>Done tasks</span></div>
          </section>

          <section class="panel">
            <h2>Recent Tasks</h2>
            <table>
              <thead>
                <tr><th>ID</th><th>Title</th><th>Status</th><th>Category</th><th>Due</th></tr>
              </thead>
              <tbody>{task_rows}</tbody>
            </table>
          </section>

          <section class="panel">
            <h2>Try It Locally</h2>
            <pre>curl -X POST http://localhost:8000/telegram/webhook/ \\
  -H 'Content-Type: application/json' \\
  -d '{{"message":{{"chat":{{"id":"replace-with-your-telegram-chat-id"}},"text":"/add Follow up with Ahmed tomorrow"}}}}'</pre>
          </section>
        </main>
      </body>
    </html>
    """
    return HttpResponse(html)


def healthz(request):
    return JsonResponse({"ok": True})
