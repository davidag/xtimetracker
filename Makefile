.PHONY: deps

deps:  ## Install dependencies
	python -m pip install --upgrade pip
	python -m pip install black flake8 mypy pylint pytest pytest-datafiles pytest-mock tox

lint:  ## Lint and static-check
	python -m flake8 xtimetracker tests
	python -m mypy xtimetracker

tox:  ## Run tox
	python -m tox
