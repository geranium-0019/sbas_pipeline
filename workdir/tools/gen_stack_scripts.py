#!/usr/bin/env python3
import argparse, os, sys, shlex, pathlib

try:
    import yaml  # PyYAML
except Exception as e:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

def q(x: str) -> str:
    return shlex.quote(str(x))

def load_cfg(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def snwe_to_str(snwe):
    # SNWE -> "S N W E"
    return f"{snwe[0]} {snwe[1]} {snwe[2]} {snwe[3]}"

def build_stack_cmd(cfg: dict) -> list[str]:
    """Return argv list for stackSentinel.py based on our YAML schema."""
    proj   = cfg.get("project", {})
    data   = cfg.get("data", {})
    aoi    = cfg.get("aoi", {}) or {}
    coreg  = cfg.get("coreg", {})
    ifgram = cfg.get("ifgram", {})
    unwrap = cfg.get("unwrap", {})
    comp   = cfg.get("compute", {})

    cmd = ["stackSentinel.py"]

    # required-ish (paths)
    cmd += ["-s", data["slc_dir"]]
    cmd += ["-o", data["orbit_dir"]]
    cmd += ["-a", data["aux_dir"]]
    cmd += ["-d", data["dem"]]
    if proj.get("work_dir"):
        cmd += ["-w", proj["work_dir"]]

    # workflow
    cmd += ["-W", ifgram.get("workflow", "interferogram")]

    # AOI: swath / bbox（併用可）
    swath = aoi.get("swath_num")
    if swath:
        cmd += ["-n", str(swath)]
    bbox = aoi.get("bbox_snwe")
    if bbox:
        cmd += ["-b", snwe_to_str(bbox)]

    # coreg
    cmd += ["-C", coreg.get("method", "NESD")]
    ref = str(coreg.get("reference_date", "")).strip()
    if ref and ref.lower() != "auto":
        cmd += ["-m", ref]
    cmd += ["-e", str(coreg.get("esd_coh_threshold", 0.85))]
    cmd += ["--snr_misreg_threshold", str(coreg.get("snr_misreg_threshold", 10))]
    cmd += ["-O", str(coreg.get("overlap_connections", 3))]

    # pairing / looks / filter
    num_conn = ifgram.get("num_connections", 1)
    cmd += ["-c", str(num_conn)]
    looks = ifgram.get("looks", {}) or {}
    cmd += ["-r", str(looks.get("range", 9))]
    cmd += ["-z", str(looks.get("azimuth", 3))]
    cmd += ["-f", str(ifgram.get("filter_strength", 0.5))]

    # unwrap
    if unwrap.get("method"):
        cmd += ["-u", unwrap["method"]]
    if unwrap.get("rm_filter", False):
        cmd += ["--rmFilter"]

    # compute
    if comp.get("use_gpu", False):
        cmd += ["--useGPU"]
    if comp.get("num_proc") is not None:
        cmd += ["--num_proc", str(comp["num_proc"])]
    if comp.get("num_proc_topo") is not None:
        cmd += ["--num_proc4topo", str(comp["num_proc_topo"])]
    if comp.get("text_cmd"):
        cmd += ["-t", comp["text_cmd"]]

    return cmd

def to_multiline(cmd_argv: list[str]) -> str:
    """Pretty multi-line shell command with safe quoting; keep flag+value on same line."""
    qtokens = [q(t) for t in cmd_argv]

    groups: list[str] = []
    i = 0
    n = len(qtokens)
    while i < n:
        tok = qtokens[i]
        if tok.startswith('-') and i + 1 < n and not qtokens[i + 1].startswith('-'):
            groups.append(f"{tok} {qtokens[i + 1]}")
            i += 2
        else:
            groups.append(tok)
            i += 1

    first = groups[0]
    rest = groups[1:]
    lines = [first + " \\"]
    indent = "  "
    for j, g in enumerate(rest):
        end = " \\" if j < len(rest) - 1 else ""
        lines.append(f"{indent}{g}{end}")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description="Generate stackSentinel.py command from YAML")
    ap.add_argument("--config", "-c", required=True, help="Path to config.yaml")
    ap.add_argument("--out-sh", default="run_stack.sh", help="Output shell script path (relative = same dir as config)")
    ap.add_argument("--out-args", default="stack_args.txt", help="Output text file with the command (same dir as run_stack.sh)")
    ap.add_argument("--print", action="store_true", help="Also print the command to stdout")
    args = ap.parse_args()

    cfg_path = pathlib.Path(args.config).resolve()
    cfg = load_cfg(cfg_path)

    out_sh_path = pathlib.Path(args.out_sh)
    if not out_sh_path.is_absolute():
        out_sh_path = cfg_path.parent / out_sh_path.name
    out_args_path = out_sh_path.with_name(args.out_args)
    run_all_path = out_sh_path.with_name("run_all_runs.sh")

    # sanity checks (warn only)
    missing = []
    for k in ["slc_dir", "orbit_dir", "aux_dir"]:
        p = cfg.get("data", {}).get(k)
        if p and not os.path.isdir(p):
            missing.append(f"dir not found: {p}")
    dem = cfg.get("data", {}).get("dem")
    if dem and not os.path.isfile(dem):
        missing.append(f"DEM not found: {dem}")
    if missing:
        print("WARN:", *missing, sep="\n  ", file=sys.stderr)

    cmd_argv = build_stack_cmd(cfg)
    multi = to_multiline(cmd_argv)

    # args text
    out_args_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_args_path, "w", encoding="utf-8") as f:
        f.write(multi + "\n")

    # runnable run_stack.sh
    sh_body = f"""#!/usr/bin/env bash
set -euo pipefail
# Auto-generated from {q(str(cfg_path))}
# Optional: set -x for verbose
# set -x

{multi}
"""
    out_sh_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_sh_path, "w", encoding="utf-8") as f:
        f.write(sh_body)
    os.chmod(out_sh_path, 0o755)

    # run_all_runs.sh — ログ保存版
    run_all_body = r"""#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${SCRIPT_DIR}/run_files"

TS="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${SCRIPT_DIR}/logs/${TS}"
mkdir -p "${LOG_DIR}"

trap 'echo "[ERROR] Failed at step: ${CURRENT_STEP:-unknown}. See logs in ${LOG_DIR}" >&2' ERR

if [ ! -d "$RUN_DIR" ]; then
  echo "[ERROR] run_files directory not found: $RUN_DIR" | tee -a "${LOG_DIR}/run_all.log"
  exit 1
fi

mapfile -t RUN_SCRIPTS < <(find "$RUN_DIR" -maxdepth 1 -type f -name 'run_*' | sort)

if [ "${#RUN_SCRIPTS[@]}" -eq 0 ]; then
  echo "[ERROR] no run_* scripts found in $RUN_DIR" | tee -a "${LOG_DIR}/run_all.log"
  exit 1
fi

echo "[RUN_DIR] $RUN_DIR" | tee -a "${LOG_DIR}/run_all.log"
echo "[INFO] scripts to run:" | tee -a "${LOG_DIR}/run_all.log"
for s in "${RUN_SCRIPTS[@]}"; do
  echo "  - $(basename "$s")" | tee -a "${LOG_DIR}/run_all.log"
done
echo | tee -a "${LOG_DIR}/run_all.log"

i=1
total="${#RUN_SCRIPTS[@]}"

for s in "${RUN_SCRIPTS[@]}"; do
  base="$(basename "$s")"
  step="${base#run_}"; step="${step%%_*}"
  CURRENT_STEP="${step}"

  STEP_LOG="${LOG_DIR}/${base}.log"
  echo "==============================" | tee -a "${LOG_DIR}/run_all.log"
  echo "[STEP ${i}/${total}] ${base}"    | tee -a "${LOG_DIR}/run_all.log"
  echo "==============================" | tee -a "${LOG_DIR}/run_all.log"

  {
    echo "[START] $(date '+%F %T')  ${base}"
    time bash "$s"
    echo "[END]   $(date '+%F %T')  ${base}"
  } 2>&1 | tee -a "${STEP_LOG}" | tee -a "${LOG_DIR}/run_all.log" >/dev/null

  echo "[DONE] ${base}" | tee -a "${LOG_DIR}/run_all.log"
  echo | tee -a "${LOG_DIR}/run_all.log"
  ((i++))
done

echo "[ALL DONE] all run_* scripts finished. Logs: ${LOG_DIR}" | tee -a "${LOG_DIR}/run_all.log"
"""
    with open(run_all_path, "w", encoding="utf-8") as f:
        f.write(run_all_body)
    os.chmod(run_all_path, 0o755)

    if args.print:
        print(multi)

if __name__ == "__main__":
    main()
