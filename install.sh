#!/usr/bin/env bash
set -euo pipefail

REPO_ZIP="https://github.com/ak495867/Blot/archive/refs/heads/main.zip"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/blot"
BIN_DIR="${HOME}/.local/bin"
PYTHON=""

for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,9) else 1)'; then
        PYTHON="$(command -v "$candidate")"
        break
    fi
done

if [[ -z "$PYTHON" ]]; then
    printf '%s\n' "Blot requires Python 3.9 or newer." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

if [[ ! -x "$INSTALL_DIR/bin/python" ]]; then
    "$PYTHON" -m venv "$INSTALL_DIR"
fi

"$INSTALL_DIR/bin/python" -m pip install --upgrade "$REPO_ZIP"

cat > "$BIN_DIR/blot" <<'WRAPPER'
#!/usr/bin/env bash
exec "${XDG_DATA_HOME:-$HOME/.local/share}/blot/bin/blot" "$@"
WRAPPER

chmod +x "$BIN_DIR/blot"

case ":${PATH}:" in
    *":${BIN_DIR}:"*)
        ;;
    *)
        printf '\n%s\n' "Add this directory to your PATH: $BIN_DIR"
        printf '%s\n' 'For Bash, add: export PATH="$HOME/.local/bin:$PATH"'
        printf '%s\n' 'For Zsh, add the same line to ~/.zshrc.'
        ;;
esac

printf '\n%s\n' "Blot installed. Run: blot --help"
