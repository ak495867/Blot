# Blot

Cross-platform command-line LOC analyzer. Recursively counts code, comments, blank lines, and totals by language.

## Install

**Windows (PowerShell)**

```powershell
irm https://raw.githubusercontent.com/ak495867/Blot/master/install.ps1 | iex
```

**macOS / Linux**

```bash
curl -fsSL https://raw.githubusercontent.com/ak495867/Blot/master/install.sh | bash
```

## Usage

```bash
blot .                              # Scan current directory
blot ./src                          # Scan a folder
blot . --format json                # JSON output
blot . --format csv                 # CSV output
blot . --format json -o loc.json    # Save report
blot . --hidden                     # Include hidden files
blot . --exclude "*.min.js"         # Exclude matching files
blot . --top 10                     # Top 10 languages
blot --help
blot --version
```

Blot uses Pygments lexers. Unknown and binary files are skipped; common dependency, cache, and build directories are ignored by default. LOC results vary by language and counting rules.

## License

MIT
