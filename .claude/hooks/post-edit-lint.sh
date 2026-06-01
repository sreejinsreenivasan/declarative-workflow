#!/usr/bin/env bash
# Runs after every file edit on Python files.
# Surfaces ruff violations immediately so they're fixed before accumulating.

FILE="$1"

if [[ "$FILE" == *.py ]]; then
  poetry run ruff check "$FILE" --quiet
  if [ $? -ne 0 ]; then
    echo "ruff: lint errors in $FILE — fix before continuing."
    exit 1
  fi
fi

exit 0
