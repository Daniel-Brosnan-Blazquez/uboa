#!/bin/bash
# Reset the users database in the dedicated development/test environment.
set -euo pipefail
exec uboa_init.py -y "$@"
