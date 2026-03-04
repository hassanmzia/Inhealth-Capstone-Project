#!/usr/bin/env python3
"""
InHealth Chronic Care - Superuser & Default Organization Creator

Creates the initial Django superuser account and default organization
by communicating with the Django management command system.

Can be run:
  1. Directly against a running Django container via subprocess
  2. As a Django management command wrapper
  3. Via direct DB connection (for bootstrapping)
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path=None):
        pass

# ============================================================
# Configuration
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

# Default superuser credentials (override via env or CLI args)
DEFAULT_SUPERUSER_USERNAME = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
DEFAULT_SUPERUSER_EMAIL = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@inhealth.io")
DEFAULT_SUPERUSER_PASSWORD = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "InHealth2024!")
DEFAULT_SUPERUSER_FIRST_NAME = os.environ.get("DJANGO_SUPERUSER_FIRST_NAME", "System")
DEFAULT_SUPERUSER_LAST_NAME = os.environ.get("DJANGO_SUPERUSER_LAST_NAME", "Administrator")

# Default organization
DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_ORG_NAME = "InHealth Demo Organization"
DEFAULT_ORG_SLUG = "inhealth-demo"

# Docker service name
DJANGO_SERVICE = os.environ.get("DJANGO_SERVICE_NAME", "django")


# ============================================================
# Django management command runner
# ============================================================
def run_django_management_command(
    command: list,
    via_docker: bool = True,
    service: str = DJANGO_SERVICE,
) -> tuple:
    """
    Run a Django management command.

    Returns (return_code, stdout, stderr).
    """
    if via_docker:
        full_command = [
            "docker", "compose", "exec", "-T", service,
            "python", "manage.py"
        ] + command
    else:
        full_command = ["python", str(PROJECT_DIR / "backend" / "manage.py")] + command

    logger.debug(f"Running: {' '.join(full_command)}")

    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR)
    )
    return result.returncode, result.stdout, result.stderr


def create_superuser_via_shell(
    username: str,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    via_docker: bool = True,
    service: str = DJANGO_SERVICE,
) -> bool:
    """
    Create Django superuser using a Python shell command.
    Uses get_or_create to be idempotent.
    """
    python_script = f"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

username = {json.dumps(username)}
email = {json.dumps(email)}
password = {json.dumps(password)}
first_name = {json.dumps(first_name)}
last_name = {json.dumps(last_name)}

if User.objects.filter(username=username).exists():
    print(f"SKIP: Superuser '{{username}}' already exists")
else:
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    user.is_staff = True
    user.is_active = True
    user.save()
    print(f"CREATED: Superuser '{{username}}' ({{email}})")
"""

    if via_docker:
        full_command = [
            "docker", "compose", "exec", "-T", service,
            "python", "-c", python_script
        ]
    else:
        full_command = ["python", "-c", python_script]

    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR)
    )

    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        logger.info(f"  {output}")
        return True
    else:
        logger.error(f"  Failed: {output}")
        return False


def create_default_organization(
    org_id: str = DEFAULT_ORG_ID,
    org_name: str = DEFAULT_ORG_NAME,
    org_slug: str = DEFAULT_ORG_SLUG,
    via_docker: bool = True,
    service: str = DJANGO_SERVICE,
) -> bool:
    """
    Create the default organization in Django if it doesn't exist.
    """
    python_script = f"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Try to import the Organization model (may be named differently)
org_model = None
for model_path in [
    'organizations.models.Organization',
    'tenants.models.Organization',
    'accounts.models.Organization',
    'core.models.Organization',
]:
    try:
        module_path, class_name = model_path.rsplit('.', 1)
        import importlib
        module = importlib.import_module(module_path)
        org_model = getattr(module, class_name)
        break
    except (ImportError, AttributeError):
        continue

if org_model is None:
    print("SKIP: Organization model not found - create manually via Django admin")
else:
    import uuid
    org_id = {json.dumps(org_id)}
    org_name = {json.dumps(org_name)}
    org_slug = {json.dumps(org_slug)}

    obj, created = org_model.objects.get_or_create(
        slug=org_slug,
        defaults={{
            'id': uuid.UUID(org_id),
            'name': org_name,
            'short_name': 'InHealth Demo',
            'org_type': 'health_system',
            'status': 'demo',
            'plan_tier': 'enterprise',
        }}
    )
    if created:
        print(f"CREATED: Organization '{{org_name}}' (id: {{obj.id}})")
    else:
        print(f"SKIP: Organization '{{org_slug}}' already exists (id: {{obj.id}})")
"""

    if via_docker:
        full_command = [
            "docker", "compose", "exec", "-T", service,
            "python", "-c", python_script
        ]
    else:
        full_command = ["python", "-c", python_script]

    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR)
    )

    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        logger.info(f"  {output}")
        return True
    else:
        logger.error(f"  Failed to create organization: {output}")
        return False


def run_migrations(
    via_docker: bool = True,
    service: str = DJANGO_SERVICE,
) -> bool:
    """Run Django migrations."""
    logger.info("Running Django migrations...")

    if via_docker:
        command = ["docker", "compose", "exec", "-T", service, "python", "manage.py", "migrate", "--run-syncdb"]
    else:
        command = ["python", str(PROJECT_DIR / "backend" / "manage.py"), "migrate", "--run-syncdb"]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR)
    )

    if result.returncode == 0:
        logger.info("  Migrations completed successfully")
        return True
    else:
        logger.error(f"  Migration failed: {result.stderr[:500]}")
        return False


def collect_static(
    via_docker: bool = True,
    service: str = DJANGO_SERVICE,
) -> bool:
    """Collect Django static files."""
    logger.info("Collecting static files...")

    if via_docker:
        command = [
            "docker", "compose", "exec", "-T", service,
            "python", "manage.py", "collectstatic", "--noinput"
        ]
    else:
        command = ["python", str(PROJECT_DIR / "backend" / "manage.py"), "collectstatic", "--noinput"]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR)
    )

    if result.returncode == 0:
        logger.info("  Static files collected")
        return True
    else:
        logger.warning(f"  collectstatic warning: {result.stderr[:200]}")
        return False


def main(
    username: str = DEFAULT_SUPERUSER_USERNAME,
    email: str = DEFAULT_SUPERUSER_EMAIL,
    password: str = DEFAULT_SUPERUSER_PASSWORD,
    first_name: str = DEFAULT_SUPERUSER_FIRST_NAME,
    last_name: str = DEFAULT_SUPERUSER_LAST_NAME,
    via_docker: bool = True,
    service: str = DJANGO_SERVICE,
    run_migrations_first: bool = False,
    run_collectstatic: bool = False,
) -> bool:
    """Main setup function."""
    logger.info("=" * 60)
    logger.info("InHealth Chronic Care - Django Setup")
    logger.info("=" * 60)
    logger.info(f"Service:   {service} (via Docker: {via_docker})")
    logger.info(f"Superuser: {username} ({email})")
    logger.info("")

    success = True

    # 1. Run migrations (optional)
    if run_migrations_first:
        if not run_migrations(via_docker=via_docker, service=service):
            logger.warning("Migrations failed - continuing anyway...")

    # 2. Create default organization
    logger.info("Creating default organization...")
    if not create_default_organization(via_docker=via_docker, service=service):
        logger.warning("Organization creation failed - may already exist")

    # 3. Create superuser
    logger.info("Creating superuser...")
    if not create_superuser_via_shell(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        via_docker=via_docker,
        service=service,
    ):
        success = False

    # 4. Collect static files (optional)
    if run_collectstatic:
        collect_static(via_docker=via_docker, service=service)

    logger.info("")
    logger.info("=" * 60)
    if success:
        logger.info("Setup Complete!")
        logger.info(f"  Admin URL:      http://localhost:8000/admin")
        logger.info(f"  Username:       {username}")
        logger.info(f"  Email:          {email}")
        logger.info(f"  Password:       [as configured]")
    else:
        logger.error("Setup completed with errors - check logs above")
    logger.info("=" * 60)

    return success


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create InHealth Django superuser and default organization"
    )
    parser.add_argument("--username", default=DEFAULT_SUPERUSER_USERNAME)
    parser.add_argument("--email", default=DEFAULT_SUPERUSER_EMAIL)
    parser.add_argument("--password", default=DEFAULT_SUPERUSER_PASSWORD)
    parser.add_argument("--first-name", default=DEFAULT_SUPERUSER_FIRST_NAME)
    parser.add_argument("--last-name", default=DEFAULT_SUPERUSER_LAST_NAME)
    parser.add_argument(
        "--service",
        default=DJANGO_SERVICE,
        help="Docker Compose service name (default: django)"
    )
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Run directly without Docker (Django must be in PATH)"
    )
    parser.add_argument(
        "--with-migrations",
        action="store_true",
        help="Run Django migrations before creating superuser"
    )
    parser.add_argument(
        "--with-collectstatic",
        action="store_true",
        help="Run collectstatic after creating superuser"
    )

    args = parser.parse_args()

    success = main(
        username=args.username,
        email=args.email,
        password=args.password,
        first_name=args.first_name,
        last_name=args.last_name,
        via_docker=not args.no_docker,
        service=args.service,
        run_migrations_first=args.with_migrations,
        run_collectstatic=args.with_collectstatic,
    )
    sys.exit(0 if success else 1)
