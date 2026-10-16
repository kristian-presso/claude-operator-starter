#!/usr/bin/env bash
# Copies this case's fixture into the eval sandbox working directory.
set -euo pipefail
cp -R "$(dirname "$0")/fixture/." .
