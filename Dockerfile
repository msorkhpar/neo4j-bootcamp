FROM jupyter/minimal-notebook


RUN pip install neo4j networkx 'jupyterlab>=4.1.0,<5.0.0a0' jupyterlab-lsp \
    'python-lsp-server[all]' jupyterlab_code_formatter black isort \
    yfiles_jupyter_graphs

