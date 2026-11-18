"""
purge_guests.py

Deletes guest accounts older than N hours, with everything they own.

    python -m scripts.purge_guests                  # uses GUEST_PURGE_AFTER_HOURS (default 24)
    python -m scripts.purge_guests --hours 6
    python -m scripts.purge_guests --dry-run        # report only, delete nothing

Safe to run from a scheduler (Railway cron, Render cron job, system cron):
  * only rows with is_guest = true are ever matched; real users and global
    knowledge (knowledge_chunks.owner_id IS NULL) are never touched
  * a Postgres advisory lock makes overlapping runs skip instead of colliding
  * each guest is deleted in its own transaction, so one failure does not block the rest
  * re-running is harmless: there is nothing left to match

Exit code is 1 if any guest could not be purged, so a scheduler can alert on it.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.services import guest_service

app = create_app(os.getenv("FLASK_ENV", "development"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete old guest accounts and their data.")
    parser.add_argument("--hours", type=float, default=None,
                        help="Delete guests older than this many hours (default: GUEST_PURGE_AFTER_HOURS)")
    parser.add_argument("--dry-run", action="store_true", help="Count what would be deleted; delete nothing")
    parser.add_argument("--limit", type=int, default=None, help="Delete at most this many guests this run")
    args = parser.parse_args()

    with app.app_context():
        hours = args.hours if args.hours is not None else app.config["GUEST_PURGE_AFTER_HOURS"]
        if hours <= 0:
            print("Refusing to run with --hours <= 0.", file=sys.stderr)
            return 2

        result = guest_service.purge_guests(hours, dry_run=args.dry_run, limit=args.limit)

    if result["skipped_locked"]:
        print("Another purge is already running; skipped.")
        return 0

    verb = "would delete" if result["dry_run"] else "deleted"
    count = result["matched"] if result["dry_run"] else result["purged"]
    print(f"Guests older than {hours:g}h (created before {result['cutoff']}):")
    print(f"  matched: {result['matched']}")
    print(f"  {verb}: {count}")
    if not result["dry_run"]:
        print(f"  with reserved stock released: {result['orders_released']}")
        print(f"  failed: {result['failed']}")
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
