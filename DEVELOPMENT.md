# Development

Guide for contributors and maintainers. End-user server deployment is documented in [README.md](README.md).

## Local setup

```bash
git clone https://github.com/your-org/smtp-to-ses.git
cd smtp-to-ses
uv sync --group dev
cp .env.example .env
# Edit .env for your AWS region and allowed domains
```

Run locally:

```bash
uv run smtp-to-ses
```

Or as a module:

```bash
uv run python -m smtp_to_ses
```

## Project layout

```
src/smtp_to_ses/
  config.py       # .env / environment configuration
  handler.py      # aiosmtpd session handler
  server.py       # process lifecycle and signals
  checks/
    email.py      # address syntax, domain allowlists, MX checks
    spam.py       # DNSBL and SpamAssassin screening
deploy/
  smtp-to-ses.service   # systemd unit template
```

## Dependencies

Managed with [uv](https://docs.astral.sh/uv/). After changing `pyproject.toml`:

```bash
uv lock
uv sync
```

Dev dependencies (build and publish tools):

```bash
uv sync --group dev
```

## Building

Build sdist and wheel artifacts:

```bash
uv build
ls dist/
```

## Publishing to PyPI

Update `[project.urls]` in `pyproject.toml` with your repository URLs before publishing.

Test on TestPyPI first:

```bash
uv build
uv run twine upload --repository testpypi dist/*
```

Publish to PyPI:

```bash
uv run twine upload dist/*
```

Install from PyPI (once published):

```bash
pip install smtp-to-ses
smtp-to-ses
```

## Release checklist

- [ ] Bump `version` in `pyproject.toml` and `src/smtp_to_ses/__init__.py`
- [ ] Update `README.md` / `DEVELOPMENT.md` if behavior or config changed
- [ ] Run `uv build` and verify the wheel contents
- [ ] Upload to TestPyPI and smoke-test install
- [ ] Upload to PyPI
- [ ] Tag the release in git

## License

MIT — see [LICENSE](LICENSE).
