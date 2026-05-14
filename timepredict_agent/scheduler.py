from __future__ import annotations

from datetime import datetime
import time

from .agent import PaperAgent
from .config import AgentConfig


def run_scheduler(config: AgentConfig, interval_minutes: int) -> None:
    print(f"Scheduler started. Interval: {interval_minutes} minutes.")
    print("Press Ctrl+C to stop.")
    while True:
        started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        agent = PaperAgent(config)
        try:
            result = agent.collect()
            print(
                f"[{started}] fetched={result.fetched} saved={result.saved} "
                f"sources={result.sources} errors={result.errors or {}}"
            )
        except Exception as exc:
            print(f"[{started}] collect failed: {exc}")
        finally:
            agent.close()
        time.sleep(max(1, interval_minutes) * 60)

