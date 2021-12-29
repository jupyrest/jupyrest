#!/bin/bash

pip install pipx
pipx ensurepath

pipx install jupytext --include-deps
pipx install black
pipx install pre-commit
pipx install poetry

pre-commit install

poetry config virtualenvs.create true --local
poetry config virtualenvs.in-project true --local