#!/usr/bin/env bash
# install.sh — installer for the `tcap` thumbnail helper CLI.
# Run this script to set up the CLI plus dependencies automatically.

set -euo pipefail

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  export PATH="/usr/sbin:/usr/bin:/sbin:/bin"
  unset PYTHONPATH PYTHONHOME PYTHONUSERBASE \
        LD_PRELOAD LD_LIBRARY_PATH DYLD_LIBRARY_PATH
fi
IFS=$'\n\t'
umask 022

APP="tcap"
VERSION="1.0.0"
SCRIPT_NAME="$(basename "$0")"

SYSTEM_PREFIX="/opt/$APP"
SYSTEM_BIN_DIR="/usr/local/bin"
USER_PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/$APP"
USER_BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"

INSTALL_MODE="auto"
PREFIX=""
BIN_DIR=""
FORCE=0
SKIP_PACKAGE_INSTALL=0
APT_UPDATED=0

log_info()  { printf '[%s] %s\n' "$APP" "$*"; }
log_warn()  { printf '[%s] WARN: %s\n' "$APP" "$*" >&2; }
log_error() { printf '[%s] ERROR: %s\n' "$APP" "$*" >&2; }
need_cmd()  { command -v "$1" >/dev/null 2>&1; }

usage() {
  cat <<USAGE
$SCRIPT_NAME $VERSION — install the '$APP' CLI

Usage: $SCRIPT_NAME [options]

Options:
  --system         Install for every user (into /opt/$APP with launcher at /usr/local/bin)
  --user           Install just for you (into ~/.local/share/$APP with launcher at ~/.local/bin)
  --prefix DIR     Install into DIR (combine with --bin-dir for a custom launcher path)
  --bin-dir DIR    Place the launcher script in DIR
  --force          Reinstall even if files already exist (recreates the virtualenv)
  --skip-packages  Do not install system packages automatically
  -h, --help       Show this help and exit

Examples:
  ./$SCRIPT_NAME             # user install in ~/.local
  sudo ./$SCRIPT_NAME        # system install using sudo
  sudo ./$SCRIPT_NAME --force  # rebuild an existing system install
USAGE
}

detect_pkg_manager() {
  for candidate in apt-get dnf yum pacman zypper apk brew; do
    if need_cmd "$candidate"; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  printf 'none\n'
}

install_packages() {
  local pm="$1"; shift
  local runner=()

  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    if need_cmd sudo; then
      runner=(sudo -E)
    else
      log_error "Need sudo/root privileges to install packages. Install dependencies manually."
      exit 1
    fi
  fi

  case "$pm" in
    apt-get)
      if [ $APT_UPDATED -eq 0 ]; then
        "${runner[@]}" env DEBIAN_FRONTEND=noninteractive apt-get update -y
        APT_UPDATED=1
      fi
      "${runner[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"
      ;;
    dnf)
      "${runner[@]}" dnf install -y "$@"
      ;;
    yum)
      "${runner[@]}" yum install -y "$@"
      ;;
    pacman)
      "${runner[@]}" pacman -Sy --noconfirm "$@"
      ;;
    zypper)
      "${runner[@]}" zypper --non-interactive install "$@"
      ;;
    apk)
      "${runner[@]}" apk add --no-cache "$@"
      ;;
    brew)
      brew install "$@"
      ;;
    *)
      log_error "Package manager '$pm' is not supported."
      exit 1
      ;;
  esac
}

ensure_dependency() {
  local binary="$1" package_hint="$2"
  if need_cmd "$binary"; then
    return
  fi
  if [ $SKIP_PACKAGE_INSTALL -eq 1 ]; then
    log_error "Missing dependency '$binary'. Install package '$package_hint' manually and rerun."
    exit 1
  fi
  log_info "Installing dependency: $package_hint"
  install_packages "$PKG_MANAGER" "$package_hint"
  if ! need_cmd "$binary"; then
    log_error "Dependency '$binary' is still missing after attempted install."
    exit 1
  fi
}

ensure_path_visibility() {
  local target_dir="$1"
  local mode="$2"

  if [ -z "$target_dir" ]; then
    return 1
  fi

  if printf ':%s:' "$PATH" | grep -q ":$target_dir:"; then
    hash -r 2>/dev/null || true
    return 0
  fi

  if [ "$mode" = "system" ]; then
    return 1
  fi

  case "$target_dir" in
    "$HOME"/*) ;;
    *)
      return 1
      ;;
  esac

  local profiles=("$HOME/.profile" "$HOME/.bash_profile" "$HOME/.bashrc" "$HOME/.zprofile" "$HOME/.zshrc")
  local profile=""
  for candidate in "${profiles[@]}"; do
    if [ -f "$candidate" ]; then
      profile="$candidate"
      break
    fi
  done
  if [ -z "$profile" ]; then
    profile="$HOME/.profile"
    touch "$profile"
  fi

  local now
  now="$(date -u '+%Y-%m-%d %H:%M:%SZ')"

  if ! grep -F "$target_dir" "$profile" >/dev/null 2>&1; then
    if ! {
      printf '\n# Added by install.sh (%s)\n' "$now"
      printf 'export PATH="%s:$PATH"\n' "$target_dir"
    } >> "$profile"; then
      log_warn "Could not update $profile automatically. Add $target_dir to PATH manually."
      return 1
    fi
    log_info "Appended $target_dir to PATH in $profile (new shells will use it)."
  else
    log_info "$profile already references $target_dir."
  fi

  if ! printf ':%s:' "$PATH" | grep -q ":$target_dir:"; then
    PATH="$target_dir:$PATH"
    export PATH
  fi

  log_info "To use $APP immediately, run: export PATH=\"$target_dir:\$PATH\""
  hash -r 2>/dev/null || true
  return 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --system) INSTALL_MODE="system" ;;
    --user) INSTALL_MODE="user" ;;
    --prefix)
      [[ $# -lt 2 ]] && { log_error "--prefix requires a directory"; exit 1; }
      PREFIX="$2"; shift ;;
    --bin-dir)
      [[ $# -lt 2 ]] && { log_error "--bin-dir requires a directory"; exit 1; }
      BIN_DIR="$2"; shift ;;
    --force) FORCE=1 ;;
    --skip-packages) SKIP_PACKAGE_INSTALL=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log_error "Unknown option '$1'"
      usage
      exit 1
      ;;
  esac
  shift
done

if [ "$INSTALL_MODE" = "auto" ]; then
  if [ "${EUID:-$(id -u)}" -eq 0 ]; then
    INSTALL_MODE="system"
  else
    INSTALL_MODE="user"
  fi
fi

PKG_MANAGER="$(detect_pkg_manager)"

if [ -z "$PREFIX" ]; then
  if [ "$INSTALL_MODE" = "system" ]; then
    PREFIX="$SYSTEM_PREFIX"
  else
    PREFIX="$USER_PREFIX"
  fi
fi

if [ -z "$BIN_DIR" ]; then
  if [ "$INSTALL_MODE" = "system" ]; then
    BIN_DIR="$SYSTEM_BIN_DIR"
  else
    BIN_DIR="$USER_BIN_DIR"
  fi
fi

if [ "$INSTALL_MODE" = "system" ] && [ "${EUID:-$(id -u)}" -ne 0 ]; then
  if ! need_cmd sudo; then
    log_error "System-wide install requires sudo/root privileges. Re-run with sudo or use --user."
    exit 1
  fi
  log_info "Re-running under sudo for system installation..."
  args=("--system")
  if [ $FORCE -eq 1 ]; then args+=("--force"); fi
  if [ $SKIP_PACKAGE_INSTALL -eq 1 ]; then args+=("--skip-packages"); fi
  if [ -n "$PREFIX" ]; then args+=("--prefix" "$PREFIX"); fi
  if [ -n "$BIN_DIR" ]; then args+=("--bin-dir" "$BIN_DIR"); fi
  exec sudo -- "$0" "${args[@]}"
fi

INSTALL_DIR="$PREFIX"
VENV_DIR="$INSTALL_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python3"
ENTRYPOINT="$INSTALL_DIR/$APP.py"
LAUNCHER="$BIN_DIR/$APP"

log_info "Installing $APP $VERSION"
log_info "Install mode: $INSTALL_MODE"
log_info "Install dir: $INSTALL_DIR"
log_info "Launcher dir: $BIN_DIR"

if ! need_cmd install; then
  log_error "Required command 'install' (coreutils) not found."
  exit 1
fi

if [ $SKIP_PACKAGE_INSTALL -eq 0 ] && [ "$PKG_MANAGER" = "none" ]; then
  log_warn "No supported package manager detected; dependencies must already be present."
fi

ensure_dependency python3 python3
if [ "$PKG_MANAGER" = "apt-get" ] && [ $SKIP_PACKAGE_INSTALL -eq 0 ]; then
  if ! python3 -m venv --help >/dev/null 2>&1; then
    log_info "Installing python3-venv"
    install_packages "$PKG_MANAGER" python3-venv
  fi
fi

ensure_dependency ffmpeg ffmpeg
if ! need_cmd ffprobe; then
  if [ $SKIP_PACKAGE_INSTALL -eq 0 ] && [ "$PKG_MANAGER" != "none" ]; then
    log_info "Installing ffprobe (provided by most ffmpeg packages)"
    install_packages "$PKG_MANAGER" ffmpeg || true
  fi
  if ! need_cmd ffprobe; then
    log_error "ffprobe still missing. Install ffmpeg/ffprobe manually and rerun."
    exit 1
  fi
fi

if [ $FORCE -eq 1 ]; then
  log_info "--force requested: removing previous virtualenv and launcher"
  rm -rf "$VENV_DIR"
  rm -f "$ENTRYPOINT" "$LAUNCHER"
fi

log_info "Creating directories"
install -d -m 0755 "$INSTALL_DIR"
install -d -m 0755 "$BIN_DIR"

if [ ! -d "$VENV_DIR" ]; then
  log_info "Creating virtual environment"
  python3 -m venv "$VENV_DIR"
else
  log_info "Using existing virtual environment"
fi

log_info "Upgrading pip inside the virtual environment"
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null

# Ensure the target directory exists
mkdir -p "$(dirname "$ENTRYPOINT")"

log_info "Resolving CLI source for $ENTRYPOINT"

# 1) Explicit override via env var (useful for dev/testing)
if [ -n "${TCAP_CLI_FILE:-}" ] && [ -f "$TCAP_CLI_FILE" ]; then
  CLI_SOURCE_FILE="$TCAP_CLI_FILE"
else
  CLI_SOURCE_FILE=""

  # 2) Try next to this script (works when running install.sh from a checked-out repo)
  if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    _bs_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P || true)"
    if [ -n "$_bs_dir" ] && [ -f "$_bs_dir/tcap.py" ]; then
      CLI_SOURCE_FILE="$_bs_dir/tcap.py"
    fi
  fi

  # 3) Try current working directory (if user runs installer from repo root)
  if [ -z "$CLI_SOURCE_FILE" ] && [ -f "./tcap.py" ]; then
    CLI_SOURCE_FILE="$(pwd -P)/tcap.py"
  fi

  # 4) Try Git repo root (developer convenience)
  if [ -z "$CLI_SOURCE_FILE" ] && need_cmd git; then
    if _root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
      if [ -f "$_root/tcap/tcap.py" ]; then
        CLI_SOURCE_FILE="$_root/tcap/tcap.py"
      fi
    fi
  fi
fi

if [ -n "$CLI_SOURCE_FILE" ]; then
  log_info "Copying CLI from $CLI_SOURCE_FILE"
  install -m 0755 "$CLI_SOURCE_FILE" "$ENTRYPOINT"
else
  # Fallback: download from GitHub Raw (branch/tag overridable via REF)
  REF="${REF:-tcap_testing}"
  CLI_SOURCE_URL="${TCAP_CLI_URL:-https://raw.githubusercontent.com/Kamil-Krawiec/yt/${REF}/tcap/tcap.py}"
  log_info "Downloading CLI from $CLI_SOURCE_URL"
  if need_cmd curl; then
    curl -fsSL "$CLI_SOURCE_URL" -o "$ENTRYPOINT"
  elif need_cmd wget; then
    wget -qO "$ENTRYPOINT" "$CLI_SOURCE_URL"
  else
    log_error "Neither curl nor wget is available to download tcap.py"
    exit 1
  fi
  chmod 0755 "$ENTRYPOINT"
fi

log_info "Creating launcher at $LAUNCHER"
cat > "$LAUNCHER" <<LAUNCHER
#!/usr/bin/env bash
export TCAP_CLI_VERSION="$VERSION"
exec "$PYTHON_BIN" "$ENTRYPOINT" "\$@"
LAUNCHER
chmod +x "$LAUNCHER"

preexisting_path="$(command -v "$APP" 2>/dev/null || true)"
if ensure_path_visibility "$BIN_DIR" "$INSTALL_MODE"; then
  log_info "Configured PATH to include $BIN_DIR."
else
  log_warn "Launcher directory $BIN_DIR is not on PATH. Invoke '$LAUNCHER' directly or add it manually."
fi

post_path="$(command -v "$APP" 2>/dev/null || true)"
if [ -n "$preexisting_path" ] && [ "$preexisting_path" != "$LAUNCHER" ]; then
  log_warn "A previous '$APP' was detected at $preexisting_path. Remove it if you prefer the new launcher to take precedence."
fi
if [ -n "$post_path" ] && [ "$post_path" != "$LAUNCHER" ]; then
  log_warn "Another '$APP' is still first on PATH at $post_path. Adjust PATH or remove it so $LAUNCHER is picked up."
fi

log_info "Installation complete. Try: $APP --info"
log_info "To start using it in the same terminal session, you can either run export command listed above or refresh your shell with 'exec bash -l' (or exec zsh -l)."
