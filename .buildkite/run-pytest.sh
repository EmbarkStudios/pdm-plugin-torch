set -eo pipefail

source .buildkite/install-repo.sh

echo --- Running pytest

EXIT_CODE=0
$1 run pytest --color=yes tests --pdm-bin $1 > errors.txt || EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
	cat << EOF | buildkite-agent annotate --style "error" --context "pytest"
:warning: Tests failed. Please see below errors and correct any issues. You can run tests locally with \`pdm run pytest tests pdm-plugin-torch\`.

\`\`\`term
$(cat errors.txt)
\`\`\`

EOF
else
	buildkite-agent annotate "✅ All tests passed." --style "success" --context "pytest"
fi

exit $EXIT_CODE
