#!/bin/bash
# Your custom commands here
echo "Executing custom commands..."


echo "######################################################"
cd "${HOME}/work/"

exec tini -g -- start-notebook.py  "$@"

