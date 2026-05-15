from datetime import timedelta
import requests
from django.conf import settings
from django.utils import timezone
from apps.integrations.models import GitLabIntegration


def _headers():
    return {'PRIVATE-TOKEN': settings.GITLAB_TOKEN} if settings.GITLAB_TOKEN else {}


def _get(path, params=None):
    url = f'{settings.GITLAB_BASE_URL.rstrip("/")}/api/v4{path}'
    r = requests.get(url, headers=_headers(), params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()


def radar_summary() -> str:
    if not settings.GITLAB_TOKEN:
        return 'GitLab token is not configured.'

    lines = []
    stale_cutoff = timezone.now() - timedelta(days=3)
    for integration in GitLabIntegration.objects.filter(enabled=True):
        project_id = integration.gitlab_project_id
        try:
            issues = _get(f'/projects/{project_id}/issues', {'state': 'opened', 'per_page': 20})
            mrs = _get(f'/projects/{project_id}/merge_requests', {'state': 'opened', 'per_page': 20})
        except Exception as exc:
            lines.append(f'{integration.project_name}: GitLab error: {exc}')
            continue

        stale_issues = []
        for issue in issues:
            updated = timezone.datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
            if updated < stale_cutoff:
                stale_issues.append(issue)

        lines.append(f'Project: {integration.project_name}')
        lines.append(f'- Open issues: {len(issues)}')
        lines.append(f'- Stale issues >3 days: {len(stale_issues)}')
        lines.append(f'- Open merge requests: {len(mrs)}')
        for item in stale_issues[:5]:
            lines.append(f'  • #{item.get("iid")} {item.get("title")}')
    return '\n'.join(lines) if lines else 'No GitLab projects configured yet.'
