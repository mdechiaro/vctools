#!/bin/bash
RPATH=$(dirname $(realpath $0))
export PIPENV_VENV_IN_PROJECT=true
export PIPENV_PIPFILE="${RPATH}/Pipfile"

if [[ ! -d "${RPATH}/.venv" ]]; then
    pipenv install
fi

cd ${RPATH} && pipenv run vctools "$@"
