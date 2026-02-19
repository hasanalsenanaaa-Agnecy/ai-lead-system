#!/usr/bin/env python3
"""
Seed Script — Create First Client & Admin User
================================================

Creates a client record, admin user, activates the client, and prints
the credentials you need to start using the system.

Usage:
    # Interactive mode (prompts for details):
    python scripts/seed_client.py

    # Non-interactive with flags:
    python scripts/seed_client.py \
        --name "Sunset Dental" \
        --slug "sunset-dental" \
        --industry "dental" \
        --timezone "America/New_York" \
        --admin-email "admin@sunsetdental.com" \
        --admin-password "SecureP@ss123" \
        --admin-first "John" \
        --admin-last "Doe"
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `app.*` imports resolve
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(text: str) -> str:
    """Turn arbitrary text into a URL-safe slug."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def validate_password(pw: str) -> list[str]:
    errors = []
    if len(pw) < 8:
        errors.append("at least 8 characters")
    if not any(c.isupper() for c in pw):
        errors.append("one uppercase letter")
    if not any(c.islower() for c in pw):
        errors.append("one lowercase letter")
    if not any(c.isdigit() for c in pw):
        errors.append("one number")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pw):
        errors.append("one special character (!@#$%^&*…)")
    return errors


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def prompt_client_info() -> dict:
    print("\n╔══════════════════════════════════════════════╗")
    print("║   AI Lead System — Client & Admin Setup      ║")
    print("╚══════════════════════════════════════════════╝\n")

    name = input("  Business name: ").strip()
    if not name:
        print("  ✘ Name is required.")
        sys.exit(1)

    default_slug = slugify(name)
    slug = input(f"  Slug [{default_slug}]: ").strip() or default_slug
    if not SLUG_RE.match(slug):
        print(f"  ✘ Invalid slug '{slug}'. Must be lowercase letters, numbers, hyphens.")
        sys.exit(1)

    industry = input("  Industry (e.g. dental, real-estate, hospitality): ").strip() or "general"
    timezone = input("  Timezone [America/New_York]: ").strip() or "America/New_York"
    language = input("  Primary language [en]: ").strip() or "en"
    plan = input("  Plan (starter/growth/scale) [growth]: ").strip() or "growth"

    owner_name = input("  Owner name (optional): ").strip() or None
    owner_email = input("  Owner email (optional): ").strip() or None
    owner_phone = input("  Owner phone (optional): ").strip() or None
    website = input("  Website (optional): ").strip() or None

    return {
        "name": name,
        "slug": slug,
        "industry": industry,
        "timezone": timezone,
        "primary_language": language,
        "plan": plan,
        "owner_name": owner_name,
        "owner_email": owner_email,
        "owner_phone": owner_phone,
        "website": website,
    }


def prompt_admin_info() -> dict:
    print("\n  ── Admin User ──\n")

    email = input("  Admin email: ").strip()
    if not validate_email(email):
        print("  ✘ Invalid email.")
        sys.exit(1)

    first_name = input("  First name: ").strip()
    last_name = input("  Last name: ").strip()

    while True:
        password = input("  Password (min 8 chars, upper+lower+digit+special): ").strip()
        errors = validate_password(password)
        if not errors:
            break
        print(f"  ✘ Password needs: {', '.join(errors)}")

    phone = input("  Phone (optional): ").strip() or None

    return {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
    }


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

async def seed(client_info: dict, admin_info: dict) -> None:
    """Create client + admin user, activate, and print credentials."""

    # Late imports so dotenv/settings load correctly
    from app.db.session import get_db_context
    from app.services.client_service import ClientService
    from app.services.auth_service import AuthService
    from app.db.models import ClientStatus
    from app.db.models_auth import UserRole

    async with get_db_context() as db:
        client_svc = ClientService(db)
        auth_svc = AuthService(db)

        # 1. Check slug uniqueness
        existing = await client_svc.get_by_slug(client_info["slug"])
        if existing:
            print(f"\n  ✘ A client with slug '{client_info['slug']}' already exists (id={existing.id}).")
            print("    Use a different slug or delete the existing client first.")
            sys.exit(1)

        # 2. Create client
        print("\n  ⏳ Creating client …")
        client, api_key = await client_svc.create_client(
            name=client_info["name"],
            slug=client_info["slug"],
            industry=client_info["industry"],
            owner_name=client_info.get("owner_name"),
            owner_email=client_info.get("owner_email"),
            owner_phone=client_info.get("owner_phone"),
            website=client_info.get("website"),
            timezone=client_info["timezone"],
            primary_language=client_info["primary_language"],
            plan=client_info["plan"],
        )
        print(f"  ✔ Client created: {client.name} (id={client.id})")

        # 3. Activate client
        await client_svc.activate_client(client.id)
        print(f"  ✔ Client activated (status=active)")

        # 4. Register admin user
        print("  ⏳ Creating admin user …")
        user, verification_token = await auth_svc.register_user(
            email=admin_info["email"],
            password=admin_info["password"],
            first_name=admin_info["first_name"],
            last_name=admin_info["last_name"],
            client_id=client.id,
            role=UserRole.ADMIN,
            phone=admin_info.get("phone"),
        )

        # Auto-verify the admin user so they can log in immediately
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires = None

        print(f"  ✔ Admin user created & verified: {user.email} (id={user.id})")

    # --- Print summary ---
    border = "═" * 58
    print(f"\n  ╔{border}╗")
    print(f"  ║  🎉  Setup Complete!                                     ║")
    print(f"  ╠{border}╣")
    print(f"  ║                                                          ║")
    print(f"  ║  Client:  {client_info['name']:<47}║")
    print(f"  ║  Slug:    {client_info['slug']:<47}║")
    print(f"  ║  ID:      {str(client.id):<47}║")
    print(f"  ║  Status:  active                                         ║")
    print(f"  ║                                                          ║")
    print(f"  ║  Admin:   {admin_info['email']:<47}║")
    print(f"  ║  Role:    admin                                          ║")
    print(f"  ║                                                          ║")
    print(f"  ╚{border}╝")

    print(f"\n  ┌─── API Key (save this — it won't be shown again) ───┐")
    print(f"  │                                                       │")
    print(f"  │  {api_key}")
    print(f"  │                                                       │")
    print(f"  └───────────────────────────────────────────────────────┘")

    print(f"\n  Quick test:")
    print(f"    curl -H 'X-API-Key: {api_key}' http://localhost:8000/webhooks/web-form \\")
    print(f"      -H 'Content-Type: application/json' \\")
    print(f"      -d '{{\"client_id\": \"{client.id}\", \"name\": \"Test Lead\", \"message\": \"Hi!\"}}'")
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Seed a client and admin user for the AI Lead System"
    )
    parser.add_argument("--name", help="Business name")
    parser.add_argument("--slug", help="URL-safe slug")
    parser.add_argument("--industry", default="general", help="Industry")
    parser.add_argument("--timezone", default="America/New_York", help="Timezone")
    parser.add_argument("--language", default="en", help="Primary language")
    parser.add_argument("--plan", default="growth", choices=["starter", "growth", "scale"])
    parser.add_argument("--owner-name", help="Owner name")
    parser.add_argument("--owner-email", help="Owner email")
    parser.add_argument("--owner-phone", help="Owner phone")
    parser.add_argument("--website", help="Website URL")
    parser.add_argument("--admin-email", help="Admin user email")
    parser.add_argument("--admin-password", help="Admin user password")
    parser.add_argument("--admin-first", help="Admin first name")
    parser.add_argument("--admin-last", help="Admin last name")
    parser.add_argument("--admin-phone", help="Admin phone")

    args = parser.parse_args()

    # If all required args are provided, run non-interactively
    if args.name and args.admin_email and args.admin_password and args.admin_first and args.admin_last:
        client_info = {
            "name": args.name,
            "slug": args.slug or slugify(args.name),
            "industry": args.industry,
            "timezone": args.timezone,
            "primary_language": args.language,
            "plan": args.plan,
            "owner_name": args.owner_name,
            "owner_email": args.owner_email,
            "owner_phone": args.owner_phone,
            "website": args.website,
        }
        admin_info = {
            "email": args.admin_email,
            "password": args.admin_password,
            "first_name": args.admin_first,
            "last_name": args.admin_last,
            "phone": args.admin_phone,
        }

        # Validate
        if not SLUG_RE.match(client_info["slug"]):
            print(f"  ✘ Invalid slug '{client_info['slug']}'")
            sys.exit(1)
        if not validate_email(admin_info["email"]):
            print(f"  ✘ Invalid email '{admin_info['email']}'")
            sys.exit(1)
        pw_errors = validate_password(admin_info["password"])
        if pw_errors:
            print(f"  ✘ Password needs: {', '.join(pw_errors)}")
            sys.exit(1)
    else:
        # Interactive mode
        client_info = prompt_client_info()
        admin_info = prompt_admin_info()

    asyncio.run(seed(client_info, admin_info))


if __name__ == "__main__":
    main()
