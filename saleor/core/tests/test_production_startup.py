import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PRODUCTION_STARTUP = """
import importlib.abc
import sys
from contextlib import ExitStack

class RejectTestDependencies(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] == 'pytest' or (
            fullname.startswith('saleor.') and 'tests' in fullname.split('.')
        ):
            raise ImportError(f'Production imported test dependency: {fullname}')

sys.meta_path.insert(0, RejectTestDependencies())

import django
from django.conf import settings
from django.core.management import call_command
from django.db import connections

settings.PROJECT_ROOT = sys.argv[1]
settings.STATIC_ROOT = sys.argv[1] + '/static'
django.setup()
call_command('collectstatic', interactive=False, dry_run=True, verbosity=0)

from saleor.webhook.event_types import WebhookEventAsyncType
from saleor.webhook.payloads import generate_sample_payload

def reject_query(execute, sql, params, many, context):
    raise AssertionError('Synthetic customer payload queried the database')

with ExitStack() as stack:
    for connection in connections.all():
        stack.enter_context(connection.execute_wrapper(reject_query))
    payload = generate_sample_payload(WebhookEventAsyncType.CUSTOMER_CREATED)
    assert len(payload) == 1
    assert payload[0]['addresses'] is None
    assert payload[0]['email'].rsplit('@', 1)[1] in (
        'example.com', 'example.org', 'example.net'
    )
print('production startup and synthetic customer payload passed')
"""


def test_collectstatic_without_test_dependencies(tmp_path):
    # given
    environment = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "saleor.settings",
        "SECRET_KEY": "production-startup-test-only",
        "DEBUG": "True",
    }

    # when
    result = subprocess.run(
        [sys.executable, "-c", PRODUCTION_STARTUP, str(tmp_path)],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
    )

    # then
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith(
        "production startup and synthetic customer payload passed"
    )
