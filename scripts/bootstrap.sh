#!/usr/bin/env bash
# Linux x86_64/aarch64 and Apple Silicon. No preinstalled Python required.
set -euo pipefail
skill_root="$(cd "$(dirname "$0")/.." && pwd)"
runtime="${TEACHING_VIDEO_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/teaching-video-skill}"
accept=0; check=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --runtime) runtime="$2"; shift 2;;
    --accept-miniconda-terms) accept=1; shift;;
    --check-only) check=1; shift;;
    *) echo "Unknown option: $1" >&2; exit 2;;
  esac
done
umask 077
mkdir -p "$runtime"
runtime="$(cd "$runtime" && pwd)"
export TEACHING_VIDEO_HOME="$runtime"
[ -f "$runtime/.env" ] || cp "$skill_root/assets/config-template.txt" "$runtime/.env"
prefix="$runtime/envs/teaching-video"; mini="$runtime/miniconda3"
conda_cmd="${CONDA_EXE:-}"
if [ -n "$conda_cmd" ] && ! "$conda_cmd" --version >/dev/null 2>&1; then conda_cmd=""; fi
if [ -z "$conda_cmd" ]; then
  for candidate in "$mini/bin/conda" "$HOME/miniconda3/bin/conda" "$HOME/anaconda3/bin/conda" "$(command -v conda || true)"; do
    if [ -x "$candidate" ] && "$candidate" --version >/dev/null 2>&1; then conda_cmd="$candidate"; break; fi
  done
fi
os="$(uname -s)"; arch="$(uname -m)"
case "$os/$arch" in
 Linux/x86_64) file=Miniconda3-py311_26.9.4-0-Linux-x86_64.sh; hash=da5d4d5a6d381090d9337728f73b0ab1086e861df572a18aa4f7b66eace3c92a;;
 Linux/aarch64) file=Miniconda3-py311_26.9.4-0-Linux-aarch64.sh; hash=a8bd6056edd7813597b74ea227e5d31cb463794ce262ab8b76b6eec2c3f10c9c;;
 Darwin/arm64) file=Miniconda3-py311_26.9.4-0-MacOSX-arm64.sh; hash=a478b63ab42779a1df9fad54f674f43c08c9e0131bac459051f6a6573419ffd6;;
 *) echo "Unsupported platform; see first-run.md. No installer executed." >&2; exit 23;;
esac
if [ "$check" -eq 1 ]; then
  if [ -n "$conda_cmd" ]; then echo "conda_found"; else echo "miniconda_required"; fi
  echo "config_file=$runtime/.env"; exit 0
fi
if [ -z "$conda_cmd" ]; then
  if [ "$accept" -ne 1 ]; then echo "needs_miniconda_terms: open https://www.anaconda.com/legal for user acceptance, then use --accept-miniconda-terms"; exit 20; fi
  [ ! -e "$mini" ] || { echo "Partial Miniconda preserved; choose a new runtime." >&2; exit 22; }
  command -v curl >/dev/null || { echo "curl missing; install it using the OS package manager." >&2; exit 22; }
  if command -v sha256sum >/dev/null; then hash_cmd=sha256sum
  elif command -v shasum >/dev/null; then hash_cmd=shasum
  else echo "SHA-256 utility missing; no installer executed." >&2; exit 22; fi
  mkdir -p "$runtime/downloads"
  installer="$runtime/downloads/$file"
  if [ ! -f "$installer" ]; then
    curl --fail --location --proto '=https' --tlsv1.2 --retry 2 --connect-timeout 30 --max-time 900 \
      "https://repo.anaconda.com/miniconda/$file" -o "$installer.partial"
    if [ "$hash_cmd" = sha256sum ]; then actual="$(sha256sum "$installer.partial" | awk '{print $1}')"
    else actual="$(shasum -a 256 "$installer.partial" | awk '{print $1}')"; fi
    [ "$actual" = "$hash" ] || { echo "Installer hash mismatch." >&2; exit 21; }
    mv "$installer.partial" "$installer"
  fi
  if [ "$hash_cmd" = sha256sum ]; then actual="$(sha256sum "$installer" | awk '{print $1}')"
  else actual="$(shasum -a 256 "$installer" | awk '{print $1}')"; fi
  [ "$actual" = "$hash" ] || { echo "Cached installer hash mismatch." >&2; exit 21; }
  bash "$installer" -b -p "$mini"
  conda_cmd="$mini/bin/conda"
fi
export PATH="$prefix/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
healthy=0
if [ -x "$prefix/bin/python" ]; then
  if "$prefix/bin/python" "$skill_root/scripts/doctor.py" --health-only; then healthy=1; fi
fi
if [ "$healthy" -eq 0 ]; then
  [ ! -e "$prefix" ] || { echo "Existing environment preserved; see recovery.md or choose a new runtime." >&2; exit 22; }
  "$conda_cmd" create --yes --prefix "$prefix" --override-channels -c conda-forge --file "$skill_root/assets/portable-spec.txt"
fi
"$prefix/bin/python" "$skill_root/scripts/doctor.py"
echo "ready_local: fill .env and connect a provider. Native Jianying draft editing requires Windows."
