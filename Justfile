default:
    @just --list

# Generate a cryptographically secure alphanumeric password and copy it on macOS or Windows.
pass length='32':
    @{{ if os() == "windows" { "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/generate-password.ps1" } else { "./scripts/generate-password.sh" } }} "{{length}}" | {{ if os() == "windows" { "clip.exe" } else if os() == "macos" { "pbcopy" } else { "cat" } }}

up:
    docker compose up

up-prod:
    docker compose up -d

down:
    docker compose down

