
#!/usr/bin/env bash
set -euo pipefail

REPO_ZIP="https://github.com/ak495867/Blot/archive/refs/heads/master.zip"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/blot"
BIN_DIR="${HOME}/.local/bin"
VENV_PYTHON="$INSTALL_DIR/bin/python"
BLOT_EXEC="$INSTALL_DIR/bin/blot"
PYTHON=""

for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
        PYTHON="$(command -v "$candidate")"
        break
    fi
done

if [[ -z "$PYTHON" ]]; then
    printf '%s\n' "Blot requires Python 3.9 or newer." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

if [[ ! -x "$VENV_PYTHON" ]]; then
    "$PYTHON" -m venv "$INSTALL_DIR"
fi

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install --upgrade "$REPO_ZIP"

"$VENV_PYTHON" -m pip show blot-loc >/dev/null

if [[ ! -x "$BLOT_EXEC" ]]; then
    printf '%s\n' "Blot executable was not created." >&2
    exit 1
fi

"$BLOT_EXEC" --help >/dev/null

cat > "$BIN_DIR/blot" <<'WRAPPER'
#!/usr/bin/env bash
set -e
exec "${XDG_DATA_HOME:-$HOME/.local/share}/blot/bin/blot" "$@"
WRAPPER

chmod +x "$BIN_DIR/blot"

case ":${PATH}:" in
    *":${BIN_DIR}:"*)
        ;;
    *)
        printf '\n%s\n' "Add this directory to your PATH: $BIN_DIR"
        printf '%s\n' 'For Bash, add: export PATH="$HOME/.local/bin:$PATH"'
        printf '%s\n' 'For Zsh, add: export PATH="$HOME/.local/bin:$PATH"'
        ;;
esac

printf '\n%s\n' "Blot installed successfully."
printf '%s\n' "Run: blot --help"
