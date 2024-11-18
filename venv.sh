#!/usr/bin/env bash

set -eou pipefail

#set -x

# Function to parse Python version from pyproject.toml
parse_pyproject() {
    # Assuming the version is specified in the format 'requires-python = ">=3.10,<4.0"'
    sed -E 's|python.*"~(.*)"|\1|g' < pyproject.toml
}

# Function to parse Python version from .python-version
parse_python_version_file() {
    cat .python-version
}

#VERSION="$(sed -E 's|python.*"~(.*)"|\1|g' < pyproject.toml)"

# Main logic
if [[ -f "pyproject.toml" ]]; then
    PYTHON_VERSION=$(parse_pyproject)
elif [[ -f ".python-version" ]]; then
    PYTHON_VERSION=$(parse_python_version_file)
else
    PYTHON_VERSION="3.13"
fi


python"${PYTHON_VERSION}" -m venv "$(pwd)/.venv"
source "$(pwd)/.venv/bin/activate"
which python
python -V

if [[ -f "pyproject.toml" ]]; then
  cat <<-TOML > poetry.toml
[virtualenvs]
create = true
in-project = true
prefer-active-python = true
TOML
fi

python3 -m pip install --upgrade pip

if [[ -f "pyproject.toml" ]]; then
  poetry env info
  poetry env info --version
  poetry env info --path
  poetry env info --executable
  poetry lock
  poetry install --sync
fi

#set +x