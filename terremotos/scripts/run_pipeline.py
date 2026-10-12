from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa as análises GOT S2-S8, terremotos e CollegeMsg.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--keep-results", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "scripts"))
    from got_temporal_modern import analyze_got
    from earthquakes_temporal_modern import run_earthquakes
    from college_msg_temporal import run as run_college

    raw = root / "data" / "raw"
    results = root / "results"
    if not args.keep_results:
        for folder in [results / "got_s02_s08", results / "terremotos", results / "college_msg"]:
            if folder.exists():
                shutil.rmtree(folder)
    (results / "got_s02_s08").mkdir(parents=True, exist_ok=True)
    (results / "terremotos").mkdir(parents=True, exist_ok=True)
    (results / "college_msg").mkdir(parents=True, exist_ok=True)

    got = analyze_got(raw, results / "got_s02_s08", raw / "got-s2-edges(1).csv" if (raw / "got-s2-edges(1).csv").exists() else None)
    earthquakes = run_earthquakes(raw / "terremotos.csv", results / "terremotos", cell_size_degrees=10.0)
    college = run_college(results / "college_msg", window_days=7)
    summary = {"got": got, "terremotos": earthquakes, "college_msg": college}
    (results / "resumo_pipeline_integrado.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
