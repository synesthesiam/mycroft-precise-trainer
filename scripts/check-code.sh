#!/usr/bin/env bash
set -e

# Directory of *this* script
this_dir="$( cd "$( dirname "$0" )" && pwd )"
src_dir="$(realpath "${this_dir}/..")"

venv="${src_dir}/.venv"
if [[ -d "${venv}" ]]; then
    echo "Using virtual environment at ${venv}"
    source "${venv}/bin/activate"
fi

code_files=("${src_dir}/dodo.py")

# -----------------------------------------------------------------------------

flake8 "${code_files[@]}"
pylint "${code_files[@]}"
mypy "${code_files[@]}"
black --check "${code_files[@]}"
isort --check-only "${code_files[@]}"

# -----------------------------------------------------------------------------

echo "OK"
