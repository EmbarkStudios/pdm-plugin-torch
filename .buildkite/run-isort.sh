set -eo pipefail

source .buildkite/install-repo.sh

echo --- Running isort

EXIT_CODE=0
${PDM_COMMAND:1:-1} run isort --check --diff pdm-plugin-torch tests > diff.txt || EXIT_CODE=$?
cat diff.txt

if [ $EXIT_CODE -ne 0 ]; then
	cat << EOF | buildkite-agent annotate --style "error" --context "isort"
:warning: Your imports aren't sorted  by \`isort\`. Please fix the below diffs, or run \`pdm run isort tests pdm-plugin-torch\` to automatically format it.

\`\`\`diff
$(cat diff.txt)
\`\`\`
EOF
else
	buildkite-agent annotate "✅ Imports sorted correctly " --style "success" --context "isort"
fi

exit $EXIT_CODE
