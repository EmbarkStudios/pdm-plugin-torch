set -eo pipefail

source .buildkite/install-repo.sh

echo --- Running black

EXIT_CODE=0
${PDM_COMMAND:1:-1} run black --check --diff pdm-plugin-torch > diff.txt || EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
	cat << EOF | buildkite-agent annotate --style "error" --context "black"
:warning: Your code isn't formatted by \`black\`. Please fix the below diffs, or run \`pdm run black pdm-plugin-torch\` to automatically format it.

\`\`\`diff
$(cat diff.txt)
\`\`\`

EOF
else
	buildkite-agent annotate "✅ Code formatted correctly " --style "success" --context "black"
fi

exit $EXIT_CODE
