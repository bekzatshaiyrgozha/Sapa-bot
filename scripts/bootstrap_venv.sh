#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=.venv311
PYTHON=${PYTHON:-python3}

if [ ! -x "${VENV_DIR}/bin/activate" ]; then
  echo "Creating venv ${VENV_DIR} using ${PYTHON}"
  ${PYTHON} -m venv ${VENV_DIR} || {
    echo "venv creation failed; trying virtualenv"
    python3 -m pip install --user virtualenv
    python3 -m virtualenv -p ${PYTHON} ${VENV_DIR}
  }
fi

echo "Activating venv and installing pip/setuptools/wheel"
. ${VENV_DIR}/bin/activate
python -m ensurepip --upgrade || true
python -m pip install --upgrade pip setuptools wheel

echo "Installing requirements"
pip install -r requirements.txt

echo "Done. Activate with: source ${VENV_DIR}/bin/activate"
