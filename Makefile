.PHONY: html setup clean

SPHINXBUILD ?= $(shell if [ -x .venv/bin/sphinx-build ]; then echo .venv/bin/sphinx-build; else echo sphinx-build; fi)
SOURCEDIR = .
BUILDDIR = html

html:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)"

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r setup/sphinx_requierment.txt

clean:
	rm -rf "$(BUILDDIR)"
