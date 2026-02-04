#!/usr/bin/env bash
set -euo pipefail

# ===== ISCE / MintPy paths =====
ISCE_HOME=$(python - <<'PY'
try:
    import isce, pathlib
    print(pathlib.Path(isce.__file__).parent)
except Exception as e:
    print("")  # fallback
PY
)

if [ -z "${ISCE_HOME}" ]; then
  echo "[init] ⚠ isce (conda-forge) not found. Please check your conda environment."
else
  export ISCE_HOME
fi

export ISCE_SRC=/opt/isce2

# Site-packages 優先の PATH
if [ -n "${ISCE_HOME:-}" ] && [ -d "$ISCE_HOME/applications" ]; then
  case ":$PATH:" in
    *":$ISCE_HOME/applications:"*) :;;
    *) export PATH="$ISCE_HOME/applications:$PATH";;
  esac
fi

# Stack tools（tops/alos）
for d in "$ISCE_SRC/contrib/stack/topsStack" "$ISCE_SRC/contrib/stack/alosStack"; do
  [ -d "$d" ] && case ":$PATH:" in *":$d:"*) :;; *) export PATH="$d:$PATH";; esac
done

# PYTHONPATH（site-packages優先 → ソースは後段）
export PYTHONPATH="${PYTHONPATH:-}"
case ":$PYTHONPATH:" in *":$ISCE_SRC:"*) :;; *) export PYTHONPATH="$PYTHONPATH:$ISCE_SRC";; esac
case ":$PYTHONPATH:" in *":/opt/isce2/contrib/stack:"*) :;; *) export PYTHONPATH="$PYTHONPATH:/opt/isce2/contrib/stack";; esac

# MintPy / SNAPHU
# (conda-forge インストールを想定)
for p in /opt/conda/bin; do
  case ":$PATH:" in *":$p:"*) :;; *) export PATH="$p:$PATH";; esac
done
command -v smallbaselineApp.py >/dev/null 2>&1 || echo "[init] ℹ MintPy apps not found in PATH"
command -v snaphu >/dev/null 2>&1 || echo "[init] ℹ snaphu not found in PATH"

# ===== Auth (.netrc) =====
ensure_netrc () {
  local NETRC="$HOME/.netrc"
  if [ -f "$NETRC" ]; then
    chmod 600 "$NETRC" || true
    return
  fi

  # .env から生成（ある場合のみ）
  # EARTHDATA credentials (from .env)
  if [ -n "${EARTHDATA_USER:-}" ] && [ -n "${EARTHDATA_PASS:-}" ]; then
    {
      echo "machine urs.earthdata.nasa.gov login ${EARTHDATA_USER} password ${EARTHDATA_PASS}"
    } > "$NETRC"
  fi

  # Copernicus Data Space Ecosystem credentials (from .env)
  if [ -n "${COPERNICUS_USER:-}" ] && [ -n "${COPERNICUS_PASSWORD:-}" ]; then
    {
      echo "machine dataspace.copernicus.eu login ${COPERNICUS_USER} password ${COPERNICUS_PASSWORD}"
      echo "machine zipper.dataspace.copernicus.eu login ${COPERNICUS_USER} password ${COPERNICUS_PASSWORD}"
    } >> "$NETRC"
  fi

  if [ -f "$HOME/.netrc.ro" ] && [ ! -s "$NETRC" ]; then
    cp "$HOME/.netrc.ro" "$NETRC"
  fi

  if [ -f "$NETRC" ]; then
    chmod 600 "$NETRC"
    echo "[init] ✅ ~/.netrc ready"
  else
    echo "[init] ⚠ Auth not set (.env with EARTHDATA_*/COPERNICUS_* or mount ~/.netrc.ro)"
  fi
}
ensure_netrc

# requests/curl/GDAL に netrc を使わせる（DL安定化）
export CURL_NETRC=1
export GDAL_HTTP_NETRC=YES
export GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR
export GDAL_NUM_THREADS=ALL_CPUS
export VSI_CACHE=YES

# ===== Project directories =====
# If a .env exists in the current directory, load it to get PROJECT_NAME/PROJECT_ROOT/PROJECT_MOUNT
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1090
  source .env
  set +a
fi

# ===== Logs =====
echo
echo "[init] ✅ ISCE2/MintPy environment ready."
echo "[init] ISCE_HOME = ${ISCE_HOME:-<not found>}"
echo "[init] ISCE_SRC  = $ISCE_SRC"
echo "[init] PATH      = $PATH"
echo "[init] PYTHONPATH= $PYTHONPATH"
echo

exec bash
