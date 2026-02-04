#!/usr/bin/env bash
set -euo pipefail

# conf.sh
# Generate run_stack.sh and copy run_all_runs.sh into /work/{PROJECT_NAME}/processing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env if present to get PROJECT_PATH/PROJECT_NAME
if [ -f "${SCRIPT_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${SCRIPT_DIR}/.env"
  set +a
fi

# Prefer PROJECT_PATH if provided; otherwise fall back to PROJECT_NAME under /work
project_path="${PROJECT_PATH:-}"
proj_name="${PROJECT_NAME:-}"
if [ -n "${project_path}" ]; then
  base_dir="${project_path}"
elif [ -n "${proj_name}" ]; then
  base_dir="/work/${proj_name}"
else
  echo "[conf] ERROR: neither PROJECT_PATH nor PROJECT_NAME set in ${SCRIPT_DIR}/.env" >&2
  exit 1
fi

processing_dir="${base_dir}/processing"
mkdir -p "${processing_dir}" || true

# Create run_stack.sh with requested default arguments
cat > "${processing_dir}/run_stack.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail

stackSentinel.py \
  -s ${base_dir}/imgs \
  -o ${base_dir}/processing/orbit \
  -a ${base_dir}/AuxDie \
  -d ${base_dir}/DEM \
  -w ${base_dir}/processing \
  -W interferogram \
  -C NESD \
  -m 20200302 \
  -c 2 \
  -r 9 \
  -z 3 \
  -f 0.5 \
  -e 0.85 \
  --snr_misreg_threshold 10 \
  -O 3 \
  -u snaphu \
  -b '-6.4584126 -5.7196546 106.427925 107.148735' \
  --num_proc 8 \
  --num_proc4topo 4
EOF
chmod +x "${processing_dir}/run_stack.sh"

# Create run_all_runs.sh directly in the processing directory
cat > "${processing_dir}/run_all_runs.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${SCRIPT_DIR}/run_files"

if [ ! -d "$RUN_DIR" ]; then
  echo "[ERROR] run_files directory not found: $RUN_DIR" >&2
  exit 1
fi

# run_files/run_* を番号順に実行
mapfile -t RUN_SCRIPTS < <(find "$RUN_DIR" -maxdepth 1 -type f -name 'run_*' | sort)

if [ "${#RUN_SCRIPTS[@]}" -eq 0 ]; then
  echo "[ERROR] no run_* scripts found in $RUN_DIR" >&2
  exit 1
fi

echo "[INFO] scripts to run:"
for s in "${RUN_SCRIPTS[@]}"; do
  echo "  - $(basename "$s")"
done
echo

i=1
for s in "${RUN_SCRIPTS[@]}"; do
  echo "=============================="
  echo "[STEP $i/${#RUN_SCRIPTS[@]}] $(basename "$s")"
  echo "=============================="
  bash "$s"
  echo "[DONE] $(basename "$s")"
  echo
  ((i++))
done

echo "[ALL DONE] all run_* scripts finished."
EOF
chmod +x "${processing_dir}/run_all_runs.sh"

echo "[conf] ✅ Created run_stack.sh and run_all_runs.sh in ${processing_dir}"

echo "[conf] Done."

exit 0
