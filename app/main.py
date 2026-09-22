"""CLI entry point: run a single content job end to end.

Usage:
    python -m app.main --media-type poster --brief-file brief.json
"""
import argparse
import json

from app.orchestrator.orchestrator import run_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an mpostele content job.")
    parser.add_argument("--media-type", choices=["poster", "video"], required=True)
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--brief-file", required=True, help="Path to a JSON campaign brief")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Schedule the finished artifact to social platforms via Postiz (see app/config/settings.py)",
    )
    parser.add_argument(
        "--publish-now",
        action="store_true",
        help="Publish immediately instead of scheduling a review window (implies --publish)",
    )
    args = parser.parse_args()

    with open(args.brief_file, "r", encoding="utf-8") as f:
        input_brief = json.load(f)

    job_id = run_job(
        args.media_type,
        args.aspect_ratio,
        input_brief,
        publish=args.publish or args.publish_now,
        publish_now=args.publish_now,
    )
    print(job_id)


if __name__ == "__main__":
    main()
