#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..
VENV_DIR=$ROOT_DIR/.venv
VENV_BIN=$VENV_DIR/bin

$VENV_BIN/pip install -r $ROOT_DIR/requirements.txt
$VENV_BIN/waitress-serve --host 127.0.0.1 app:app