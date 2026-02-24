#!/bin/bash

# Ativa o ambiente virtual correto
source /root/venv/bin/activate

# Vai para a pasta da aplicação
cd /root/venv/portal-automation/app

# Executa o streamlit
exec streamlit run index.py --server.port 8502
