.PHONY: deps

deps:  ## Install development dependencies
	python -m pip install --upgrade pip
	python -m pip install \
		black \
		flake8 \
		freezegun \
		mypy \
		pylint \
		pytest \
		pytest-datafiles \
		pytest-mock \
		tox

lint:  ## Lint and static-check
	python -m flake8 xtimetracker tests
	python -m mypy xtimetracker

tox:  ## Run tox
	python -m tox

bash:  ## Create completion file for bash
	scripts/create-completion-script.sh bash

zsh:  ## Create completion file for zsh
	scripts/create-completion-script.sh zsh

fish:  ## Create completion file for fish
	scripts/create-completion-script.sh fish
