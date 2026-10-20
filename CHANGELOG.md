# Changelog

All notable changes are documented here. The project follows semantic version
numbers for the application and release artifacts.

## 8.1.0 - 2026-10-20

### Added

- **Advanced Standalone Generative Engine**:
  - Repetition and recency penalties to eliminate looping and absorbing n-gram basins.
  - Strict no-repeat 3-gram masking preventing recursive phrase traps.
  - Nucleus sampling (top-p = 0.88, top-k = 35) with configurable temperature.
  - Prompt anchor context retention mechanism preserving prompt subject beyond the 8-token attention window.
  - Dynamic topic-passage steering and automatic semantic memory grounding.
  - Post-generation surface realization with truecasing, acronym restoration, and proper punctuation.
  - Full functional n-gram transition engine (`build_ngrams` / `rebuild_ngrams`).

### Changed

- Fixed token ID initialization bug in `TransMoE.load()` where `unk`, `bos`, `eos`, `pad` were never bound from vocabulary.
- Upgraded `Thinker._generate_reply()` to ground LM generation with retrieved semantic memory passages.
- Optimized model container LZMA compression preset (preset 6) enabling fast on-device export.

## 8.0.0 - 2026-10-20

### Added

- Open-source repository layout with self-contained compressed knowledge DB.
- GitHub Actions build workflow for `TenSeiAi.pyz`, `TenSeiAi.tsei`, and
  checksums.
- Tag-driven GitHub Release publishing.
- CodeQL, Dependabot, issue templates, and security policy.
- Build, architecture, API, Android, model card, benchmark, and FAQ docs.
- SHA-256 verification for the compressed knowledge asset and release files.

### Changed

- Release version is now 8.0.0.
- Web UI no longer loads third-party fonts.
- Android signing is environment-driven; no keystore is shipped.
- Source data is restored from `assets/tensei.db.gz` instead of committing the
  uncompressed SQLite database.

### Removed

- Historical model builds and backups.
- Database backups and generated benchmark dumps.
- Logs, caches, temporary scripts, and downloaded datasets.
- Hard-coded Android signing credentials.

### Verification

- 19,895 Q&A rows, 7,460 passages, 400 topics.
- SQLite integrity check passes.
- 100-question offline benchmark passes.
- Both artifacts build from the clean source tree.
