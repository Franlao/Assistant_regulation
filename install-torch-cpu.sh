#!/bin/bash
# Script pour installer PyTorch CPU-only après l'installation des autres requirements
echo "Installation de PyTorch CPU-only..."
pip install torch==2.7.1+cpu -f https://download.pytorch.org/whl/cpu
echo "PyTorch CPU-only installé avec succès"