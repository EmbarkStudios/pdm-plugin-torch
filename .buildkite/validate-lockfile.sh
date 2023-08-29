set -eo pipefail

EXIT_CODE=0
${PDM_COMMAND:1:-1} lock --check || EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    buildkite-agent annotate --style "error" --context "lockfile" ":lock: Failed validating lockfile. See logs for more info."
	exit 1
fi

GIT_STATUS=$(git status --porcelain --untracked-files=no -- pdm.lock)
if  [ -n "$GIT_STATUS" ] ; then
	lock_diff=$(git diff pdm.lock)
	cat << EOF | buildkite-agent annotate --style "error" --context "lockfile"
:lock: Lockfile is outdated. Please run \`pdm lock --no-update\` and commit the result.

\`\`\`diff
$lock_diff
\`\`\`
EOF
	exit 1
else
    buildkite-agent annotate --style "success" --context "lockfile" ":lock: Lockfile is up to date."
fi
