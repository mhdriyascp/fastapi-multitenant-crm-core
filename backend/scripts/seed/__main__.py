"""Run the complete initial-setup seed."""

import argparse
import asyncio

from .master_data import main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed CRM master data, RBAC, menus, and demo users."
    )
    parser.add_argument(
        "--without-demo-users",
        action="store_false",
        dest="include_demo_users",
        help="Seed master data without creating demo user accounts.",
    )
    parser.set_defaults(include_demo_users=True)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main(include_demo_users=parse_args().include_demo_users))
