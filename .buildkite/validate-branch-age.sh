merge_base=$(git merge-base -a HEAD origin/main)
last_merge=$(git log -1 "$merge_base" --format="%at")
last_main_commit=$(git log -1 origin/main --format="%at")
time_since_merge=$(( last_main_commit - last_merge ))

if [[ $time_since_merge -gt 604800 ]]; then
    buildkite-agent annotate --style "error" --context validate-changes "This branch is more than one week out of sync with main. Please rebase/merge main to unblock CI."
    exit 1
fi
