#!/bin/bash

set -uo pipefail

function print_help() {

  cat <<EOF
Usage: $0 shell-type

This script generates the auto completion receipt required by Bash or Zsh.
Since the receipt is only a wrapper around the click framework, this results
in correct tab completion, regardless of the Watson version.

The argument shell-type must be either "bash" or "zsh".
EOF
}

# Parse command line parameters
if [[ $# -ne 1 ]]
then
  echo "Please provide exactly one input argument." >&2
  exit 1
fi

if [[ $1 == "-h" || $1 == "--help" ]]
then
  print_help
  exit 0
fi

case $1 in
  -h|--help)
    print_help
    exit 0
    ;;
  bash)
    src_command="source"
    dst_script="watson.completion"
    ;;
  zsh)
    src_command="source_zsh"
    dst_script="watson.zsh-completion"
    ;;
  *)
    echo "Unknown argument '$1'. Please consult help text." >&2
    exit 1
esac

inside_venv=$(python -c \
    "import sys; print('1' if hasattr(sys, 'base_prefix') or hasattr(sys, 'real_prefix') else '0')" \
)

if [[ "$inside_venv" == "0" ]]; then
    echo "Error: script should run inside a virtualenv"
    exit 1
fi

_WATSON_COMPLETE=$src_command watson > $dst_script

exit 0