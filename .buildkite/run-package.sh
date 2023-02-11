set -eo pipefail

source .buildkite/install-repo.sh

echo --- Packaging plugin

EXIT_CODE=0
pdm build > errors.txt || EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
	cat << EOF | buildkite-agent annotate --style "error" --context "package"
:warning: Packaging failed. Please see below errors and correct any issues. You can try packaging locally with `pdm build`.

\`\`\`shell
$(cat errors.txt)
\`\`\`

EOF
else
	buildkite-agent annotate "✅ Packaging succeeded." --style "success" --context "package"
fi

exit $EXIT_CODE
