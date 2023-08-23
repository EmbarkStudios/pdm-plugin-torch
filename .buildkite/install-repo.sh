set -eo pipefail

echo --- Setting up google-cloud-sdk

if [ -f '/gcloud/google-cloud-sdk/path.bash.inc' ]; then . '/gcloud/google-cloud-sdk/path.bash.inc'; fi
gcloud config set account monorepo-ci@embark-builds.iam.gserviceaccount.com

echo --- Installing dependencies

eval "$(pyenv init --path)"
eval "$(pyenv init -)"

pyenv global ${PYTHON_VERSION:1:-1}
pyenv rehash

${PDM_COMMAND:1:-1} install -d
