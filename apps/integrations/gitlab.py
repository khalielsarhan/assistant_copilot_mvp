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
    if not settings.GITLAB_TOKEN or settings.GITLAB_TOKEN == 'replace-me':
        return 'GitLab token is not configured.'

    lines = []
    stale_cutoff = timezone.now() - timedelta(days=3)
    mr_stale_cutoff = timezone.now() - timedelta(days=2)
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
        stale_mrs = []
        for mr in mrs:
            updated = timezone.datetime.fromisoformat(mr['updated_at'].replace('Z', '+00:00'))
            if updated < mr_stale_cutoff:
                stale_mrs.append(mr)
        unassigned = [issue for issue in issues if not issue.get('assignees')]

        lines.append(f'Project: {integration.project_name}')
        lines.append(f'- Open issues: {len(issues)}')
        lines.append(f'- Stale issues >3 days: {len(stale_issues)}')
        lines.append(f'- Unassigned issues: {len(unassigned)}')
        lines.append(f'- Open merge requests: {len(mrs)}')
        lines.append(f'- Stale merge requests >2 days: {len(stale_mrs)}')
        for item in stale_issues[:5]:
            lines.append(f'  - Stale issue #{item.get("iid")} {item.get("title")}')
        for item in stale_mrs[:5]:
            lines.append(f'  - Stale MR !{item.get("iid")} {item.get("title")}')
    return '\n'.join(lines) if lines else 'No GitLab projects configured yet.'
