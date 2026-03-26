# coggle

A lightweight, fully offline CLI tool for file processing, conversion, format specific operations and bulk management using tiny NLP pipelines, no GPU required.

### Development Setup

Install all dependencies using uv

```sh
uv install
```

Load the `en_core_web_sm` model provided by SpaCY

```sh
uv run python -m spacy download en_core_web_sm
```
Running Tests

```sh
uv run python -m pytest
```