# -*- coding: utf-8 -*-
"""
cli

Command-line interface for the admin package.

Version: 0.1.0
Author: Timur Kady
Email: timurkady@yandex.com
"""

from __future__ import annotations


class AdminCLI:
    """Simple command-line interface for administration tasks."""

    def run(self) -> int:
        """Run the CLI and return an exit code."""
        print("Admin CLI executed.")
        return 0

    @classmethod
    def main(cls) -> int:
        """Entry point for console scripts."""
        return cls().run()


main = AdminCLI.main

# The End
