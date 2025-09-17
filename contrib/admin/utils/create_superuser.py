# -*- coding: utf-8 -*-
"""
create_superuser

Django-like createsuperuser utility.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from getpass import getpass
from typing import Optional, Any

# Your project imports – keep as in your repo
from ..boot import admin as boot_admin
from ..adapters import BaseAdapter
from ..core.services.auth import AuthService
from config.settings import settings
from config.orm import init_orm, close_orm


class SuperuserCreator:
    def __init__(self, adapter: BaseAdapter | None = None) -> None:
        self.adapter = adapter or boot_admin.adapter
        self.auth_service = AuthService(self.adapter)

    def _env_or(self, arg: Optional[str], env_name: str) -> Optional[str]:
        v = arg if arg else os.getenv(env_name)
        return v if v not in {"", None} else None

    def _prompt_nonempty(self, label: str, *, allow_empty: bool = False) -> str:
        while True:
            val = input(f"{label}: ").strip()
            if allow_empty or val:
                return val
            print("Value cannot be empty. Try again.")

    def _prompt_password_twice(self) -> str:
        while True:
            p1 = getpass("Password: ")
            if not p1:
                print("Password cannot be empty.")
                continue
            p2 = getpass("Password (again): ")
            if p1 != p2:
                print("Passwords do not match. Try again.")
                continue
            # trivial sanity checks; feel free to extend
            if len(p1) < 4:
                print("Password too short (min 4 chars for now).")
                continue
            return p1

    async def _set_password(self, user: Any, raw_password: str) -> None:
        """
        Prefer model's set_password if provided; fallback to plain assignment
        (your model is expected to have set_password).
        """
        if hasattr(user, "set_password") and callable(user.set_password):
            await user.set_password(raw_password)  # model handles hashing
        else:
            # In case someone removed set_password, do a last-resort direct set
            from contrib.admin.utils.passwords import password_hasher

            user.password = await password_hasher.make_password(raw_password)

    async def _create_or_update(
        self,
        username: str,
        email: Optional[str],
        password: Optional[str],
        *,
        update_if_exists: bool,
        reset_password_if_exists: bool,
    ) -> int:
        # Ensure ORM is up
        await init_orm(settings.DATABASE_URL)

        try:
            AdminUser = self.adapter.user_model
            # Does this user already exist?
            existing = await self.adapter.get_or_none(AdminUser, username=username)

            if existing is None:
                # Create new superuser
                if password is None:
                    # interactive safety: if password still not provided, ask
                    password = self._prompt_password_twice()
                await self.auth_service.create_superuser(
                    username=username, email=email or "", password=password
                )
                print(f"Superuser '{username}' created.")
                return 0

            # User exists
            if not update_if_exists:
                print(
                    f"User '{username}' already exists. Use --update-if-exists to modify.",
                    file=sys.stderr,
                )
                return 1

            # Update flags; optionally reset password
            changed = False
            for attr, val in (
                ("is_superuser", True),
                ("is_staff", True),
                ("is_active", True),
            ):
                if getattr(existing, attr) is not val:
                    setattr(existing, attr, val)
                    changed = True

            if reset_password_if_exists:
                if password is None:
                    password = self._prompt_password_twice()
                await self._set_password(existing, password)
                changed = True

            if email is not None and existing.email != email:
                existing.email = email
                changed = True

            if changed:
                await self.adapter.save(existing)
                print(f"User '{username}' updated.")
            else:
                print(f"User '{username}' already has desired flags.")
            return 0

        finally:
            await close_orm()

    def _build_arg_parser(self) -> argparse.ArgumentParser:
        p = argparse.ArgumentParser(
            description="Create a Django-like superuser."
        )
        p.add_argument("--username", help="Username for the superuser")
        p.add_argument("--email", help="Email for the superuser")
        p.add_argument(
            "--password",
            help="Password for the superuser (use with --no-input)",
        )
        p.add_argument(
            "--no-input",
            action="store_true",
            help="Do not prompt for input; read from args/env",
        )
        p.add_argument(
            "--update-if-exists",
            action="store_true",
            help="If user exists, update is_superuser/is_staff/is_active; do not fail",
        )
        p.add_argument(
            "--reset-password-if-exists",
            action="store_true",
            help="Together with --update-if-exists: also reset password",
        )
        return p

    def main(self) -> int:
        args = self._build_arg_parser().parse_args()

        # resolve values from flags/env
        username = self._env_or(args.username, "ADMIN_USERNAME")
        email = self._env_or(args.email, "ADMIN_EMAIL")
        password = self._env_or(args.password, "ADMIN_PASSWORD")

        if args.no_input:
            # non-interactive: must have username; email optional; password optional unless reset requested
            if not username:
                print("Missing --username (or ADMIN_USERNAME) with --no-input.", file=sys.stderr)
                return 1
            if args.reset_password_if_exists and not password:
                print(
                    "Missing --password (or ADMIN_PASSWORD) with --reset-password-if-exists in --no-input mode.",
                    file=sys.stderr,
                )
                return 1
        else:
            # interactive prompts for missing pieces
            if not username:
                username = self._prompt_nonempty("Username")
            if email is None:
                email = self._prompt_nonempty("Email (can be empty)", allow_empty=True)
            if password is None and not args.update_if_exists:
                # for new user we're likely to need a password
                password = self._prompt_password_twice()

        # run async routine
        return asyncio.run(
            self._create_or_update(
                username=username,
                email=email,
                password=password,
                update_if_exists=args.update_if_exists,
                reset_password_if_exists=args.reset_password_if_exists,
            )
        )


if __name__ == "__main__":
    raise SystemExit(SuperuserCreator().main())

# The End

