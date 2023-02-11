set -eo pipefail

cr="$(printf "\r")"

any_matches=1

grep --exclude-dir=".git" -Ilsr "${cr}$" . || any_matches=0


if [[ $any_matches -gt 0 ]]; then
    buildkite-agent annotate --style "error" --context validate-changes "Repository contains CRLF line-endings. To avoid diff issues and cross-platform issues we require that all commits are done using a LF-style.

If you're doing development on Windows, use \`git config --global core.autocrlf true\` to let Git fix this for you on commit."
    exit 1
fi
