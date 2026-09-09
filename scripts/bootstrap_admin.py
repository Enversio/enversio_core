"""Create the initial Saleor staff user on a freshly migrated database.

A container deployment has no interactive shell to run `createsuperuser` in,
and `createsuperuser --noinput` leaves the account with an unusable password.
This runs as part of the deploy, reading its inputs from the environment:

    SALEOR_ADMIN_EMAIL
    SALEOR_ADMIN_PASSWORD

Both unset is the normal case for a deployment that manages its own accounts —
the script then does nothing and exits 0.

It only ever *creates*. If the account already exists the password is left
alone, so rotating it in the admin is not undone by the next deploy.
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saleor.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402  (needs django.setup)


def main() -> int:
    email = os.environ.get("SALEOR_ADMIN_EMAIL", "").strip()
    password = os.environ.get("SALEOR_ADMIN_PASSWORD", "")

    if not email or not password:
        print("bootstrap_admin: SALEOR_ADMIN_EMAIL/PASSWORD unset, skipping.")
        return 0

    user_model = get_user_model()
    user, created = user_model.objects.get_or_create(
        email=email,
        defaults={"is_staff": True, "is_superuser": True, "is_active": True},
    )

    if not created:
        print(f"bootstrap_admin: {email} already exists, leaving it untouched.")
        return 0

    # set_password hashes it; assigning to .password would store it verbatim.
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.save()
    print(f"bootstrap_admin: created staff user {email}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
