PY ?= .venv/bin/python

.PHONY: all venv prompts test smoke pilot run robust parse estimate figures tables paper-assets paper clean

# From the cached responses in data/responses/: prompts -> tests -> parse -> estimate -> figures -> tables -> paper numbers.
# No GPU needed; `make run` / `make robust` regenerate the responses (GPU, Ollama).
all: prompts test parse estimate figures tables paper-assets

venv:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

prompts:
	$(PY) -m src.prompts.build

test:
	$(PY) -m pytest -q tests

# Live: 2 prompts x every installed model (needs Ollama).
smoke:
	$(PY) -m pytest -q -m smoke tests

pilot:
	$(PY) -m src.run.runner --decodings greedy --subset pilot20 --out data/pilot

# Primary greedy run, 240 prompts x every model (resumable).
run:
	$(PY) -m src.run.runner --decodings greedy

# Robustness: no-system-prompt and temperature 0.7 x 2 seeds on the robust-60 subset (resumable).
robust:
	$(PY) -m src.run.runner --decodings nosys,t07_s1,t07_s2

parse:
	$(PY) -m src.pipeline parse

estimate:
	$(PY) -m src.pipeline estimate

figures:
	$(PY) -m src.pipeline figures

tables:
	$(PY) -m src.pipeline tables

paper-assets:
	$(PY) -m src.pipeline paper

# Build paper/paper.pdf (pinned Tectonic; needs network on first run for the binary and TeX bundle).
paper: paper-assets
	bash paper/build.sh

clean:
	rm -rf data/processed/*.parquet output/figures/*.png output/figures/*.svg output/tables/*
