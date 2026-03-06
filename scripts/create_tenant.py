#!/usr/bin/env python3
"""
InHealth Chronic Care - Tenant Provisioning CLI

Creates a new tenant organization with admin user.
Usage: python scripts/create_tenant.py --name "Hospital A" --slug hospital-a --admin admin@hospital-a.com
"""

import argparse
import os
import sys
import uuid

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def get_django():
    """Initialize Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    import django
    django.setup()


def create_tenant(name: str, slug: str, admin_email: str, admin_password: str, tier: str = 'professional'):
    """Create a new tenant organization with an admin user."""
    get_django()

    from apps.tenants.models import Organization
    from apps.accounts.models import User

    # Check for existing tenant
    if Organization.objects.filter(slug=slug).exists():
        print(f"ERROR: Organization with slug '{slug}' already exists.")
        sys.exit(1)

    if User.objects.filter(email=admin_email).exists():
        print(f"ERROR: User with email '{admin_email}' already exists.")
        sys.exit(1)

    # Create organization
    org = Organization.objects.create(
        name=name,
        slug=slug,
        subscription_tier=tier,
        is_active=True,
        settings={
            'features': {
                'telemedicine': tier in ('professional', 'enterprise'),
                'research': tier == 'enterprise',
                'federated_learning': tier == 'enterprise',
                'population_analytics': tier in ('professional', 'enterprise'),
                'custom_branding': tier in ('professional', 'enterprise'),
            },
            'limits': {
                'max_users': {'basic': 10, 'professional': 100, 'enterprise': -1}[tier],
                'max_patients': {'basic': 500, 'professional': 10000, 'enterprise': -1}[tier],
                'api_rate_limit': {'basic': 100, 'professional': 1000, 'enterprise': 10000}[tier],
            },
        },
    )
    print(f"Created organization: {org.name} (ID: {org.id})")

    # Create admin user
    user = User.objects.create_user(
        email=admin_email,
        password=admin_password,
        first_name='Admin',
        last_name=name,
        role='org_admin',
        organization=org,
        is_active=True,
        email_verified=True,
    )
    print(f"Created admin user: {user.email} (ID: {user.id})")

    # Generate API key for the organization
    try:
        from apps.tenants.models import APIKey
        api_key = APIKey.objects.create(
            organization=org,
            name=f'{name} Default Key',
            created_by=user,
        )
        print(f"API Key: {api_key.key}")
    except Exception:
        print("Note: API key model not available, skipping.")

    print(f"\nTenant '{name}' provisioned successfully!")
    print(f"  Organization ID: {org.id}")
    print(f"  Slug: {slug}")
    print(f"  Tier: {tier}")
    print(f"  Admin: {admin_email}")

    return org, user


def main():
    parser = argparse.ArgumentParser(description='Create a new InHealth tenant organization')
    parser.add_argument('--name', required=True, help='Organization display name')
    parser.add_argument('--slug', required=True, help='URL-safe slug (e.g., hospital-a)')
    parser.add_argument('--admin', required=True, help='Admin user email address')
    parser.add_argument('--password', default=None, help='Admin password (prompted if not provided)')
    parser.add_argument('--tier', choices=['basic', 'professional', 'enterprise'], default='professional',
                        help='Subscription tier (default: professional)')

    args = parser.parse_args()

    password = args.password
    if not password:
        import getpass
        password = getpass.getpass('Admin password: ')
        confirm = getpass.getpass('Confirm password: ')
        if password != confirm:
            print('ERROR: Passwords do not match.')
            sys.exit(1)

    create_tenant(
        name=args.name,
        slug=args.slug,
        admin_email=args.admin,
        admin_password=password,
        tier=args.tier,
    )


if __name__ == '__main__':
    main()
