"""Shared CLI arg parsing for pipeline stage entry points.

Every stage - agent or media engine - is invoked the same way by the
orchestrator's subprocess runner: `python -m <module> --job <job_id>`.
"""
import argparse


def parse_job_arg() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, help="Job ID")
    return parser.parse_args().job
