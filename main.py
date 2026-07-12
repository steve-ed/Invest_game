import sys
import io
import os
import re
import subprocess
import threading
import argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from game_bus import GameBus
from kernel import SimulationKernel
from visualisation.dashboard_server import start_server


def _start_tunnel(port):
    """Open a public tunnel via serveo.net (SSH reverse proxy, no TLS issues)."""
    def _run():
        cmd = ["ssh", "-o", "StrictHostKeyChecking=no",
               "-R", f"80:localhost:{port}", "serveo.net"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1)
        for line in proc.stdout:
            line = line.strip()
            m = re.search(r"https?://\S+", line)
            if m:
                print(f"Public URL: {m.group(0)}", flush=True)
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["student", "expert"], default="student")
    parser.add_argument("--ngrok", action="store_true", help="Expose via ngrok tunnel")
    args = parser.parse_args()

    bus = GameBus()
    port = start_server(bus=bus)

    if args.ngrok:
        _start_tunnel(port)

    game_num = 0
    while True:
        game_num += 1
        print(f"\n=== GAME {game_num} STARTING ===", flush=True)

        kernel = SimulationKernel(turns=20, mode=args.mode, bus=bus)
        results = kernel.run()

        if results.get("aborted"):
            print("Game aborted (client disconnected). Waiting for new player…", flush=True)
            continue

        leaderboard = results["leaderboard"]
        print(f"\nEra played: {kernel.era_label}")
        print("\n=== LEADERBOARD ===")
        for rank, entry in enumerate(leaderboard, start=1):
            print(
                f"  {rank}. {entry['name']:<20} "
                f"Score: £{entry['final_score']:>12,.0f}  "
                f"(Portfolio: £{entry['portfolio_value']:>10,.0f}  "
                f"Cash: £{entry['cash']:>10,.0f})"
            )

        print("\nGame complete. Restarting in 10 seconds — press Ctrl+C to exit.", flush=True)
        try:
            import time
            time.sleep(10)
        except KeyboardInterrupt:
            print("\nExiting.")
            break


if __name__ == "__main__":
    main()
