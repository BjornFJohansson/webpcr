#!/usr/bin/env bash

eval "$(conda shell.bash hook)"

conda activate flaskapp

export FLASK_APP=webpcr.py&&export FLASK_ENV=development&&flask run

echo "press any key to close"
read -n1 slask