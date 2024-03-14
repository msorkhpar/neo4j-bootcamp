#!/bin/bash
# Your custom commands here
echo "Executing custom commands..."
pip install neo4j
pip install networkx
pip install 'jupyterlab>=4.1.0,<5.0.0a0' jupyterlab-lsp
pip install 'python-lsp-server[all]'
pip install jupyterlab_code_formatter
pip install black isort
pip install yfiles_jupyter_graphs

echo "######################################################"

exec tini -g -- start-notebook.py  "$@"

