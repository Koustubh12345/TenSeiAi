## What changed

## Why

## Testing

- [ ] `python -m unittest discover -s source/tests -v`
- [ ] `python scripts/build_release.py`
- [ ] Benchmark run or explanation of why it is not applicable
- [ ] Docs updated for user-visible changes

## Checklist

- [ ] No generated artifacts, model files, databases, logs, or caches are included.
- [ ] No secrets, keystores, passwords, or API tokens are included.
- [ ] The change preserves local-first behavior and does not add a required hosted API.
- [ ] The change does not introduce a Llama/GGUF/pretrained model dependency.
