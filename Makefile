# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 The tt Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

PYTHON ?= python3
PIP ?= pip

VENV_DIR = $(CURDIR)/venv
VENV_TT_DIR = $(CURDIR)/data

all: install

$(VENV_DIR): requirements-dev.txt
	$(PYTHON) -m venv "$(VENV_DIR)"
	echo "export TT_DIR=\"$(VENV_TT_DIR)\"" >> "$(VENV_DIR)"/bin/activate
	echo "set -x TT_DIR \"$(VENV_TT_DIR)\"" >> "$(VENV_DIR)"/bin/activate.fish
	"$(VENV_DIR)"/bin/pip install -U setuptools wheel pip
	"$(VENV_DIR)"/bin/pip install -Ur $<

.PHONY: env
env: $(VENV_DIR)

.PHONY: install
install:
	$(PYTHON) setup.py install

.PHONY: install-dev
install-dev:
	$(PIP) install -r requirements-dev.txt
	$(PYTHON) setup.py develop

.PHONY: check
check: clean
	$(PYTHON) setup.py test

.PHONY: clean
clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d | xargs rm -fr

.PHONY: distclean
distclean: clean
	rm -fr *.egg *.egg-info/ .eggs/

.PHONY:
mostlyclean: clean distclean
	rm -rf "$(VENV_DIR)"

.PHONY: docs
docs: install-dev
	$(PYTHON) scripts/gen-cli-docs.py
	mkdocs build

.PHONY: completion-scripts
completion-scripts:
	scripts/create-completion-script.sh bash
	scripts/create-completion-script.sh zsh
