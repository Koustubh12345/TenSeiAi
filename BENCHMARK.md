# Benchmark

The benchmark is intentionally small and fixed. It checks whether the complete
TenSeiAi system produces acceptable answers on a repeatable set; it is not a
general capability score.

## Setup

| Property | Value |
|---|---|
| Questions | 100, five domains, 20 each |
| Mode | Offline (`TENSEI_OFFLINE=1`), no runtime learning (`TENSEI_NO_LEARN=1`) |
| Database | Temporary copy of the shipped snapshot |
| Machine | Development laptop; CPU only |
| Harness | `source/bench/bench100.py` |

The harness is part of this repository. It does not contain a benchmark-specific
answer table. Answers are produced by the same routing, retrieval, solver, and
composition path used by the application.

## Results

| Check | Result |
|---|---:|
| Correct checks | **100/100** |
| Warm run | **5.0 s** total |
| Average warm latency | **0.05 s/question** |

These numbers vary with hardware, disk cache, and the temporary runtime home.
They are not a promise of the same latency on a phone.

## What the result means

TenSeiAi is a hybrid system. A large part of its factual accuracy comes from
curated knowledge, strict retrieval, and deterministic solvers, not from
open-ended generation by the 19.7M-parameter language core. That is the
intended design for a sub-100 MB local package.

The standalone language model is weak at unconstrained prose. Its held-out
next-token accuracy is 5.43% in the shipped metadata. The hybrid system is much
better on the measured set because it can retrieve a grounded answer or call a
solver when one applies.

Do not quote `100/100` as evidence that TenSeiAi matches a frontier model. Quote
it as a result on this fixed benchmark, with this method, on this build.

## Reproduce

```bash
python scripts/prepare_assets.py
cd source
TENSEI_OFFLINE=1 TENSEI_NO_LEARN=1 python bench/bench100.py
```

Windows PowerShell:

```powershell
python scripts\prepare_assets.py
Set-Location source
$env:TENSEI_OFFLINE = "1"
$env:TENSEI_NO_LEARN = "1"
python bench\bench100.py
```

The harness copies the database and trained weights into a temporary home, so
the source snapshot is never modified. It writes
`bench/bench100_results.json` next to the harness; that result file is generated
output and is not committed.

## Artifact verification

Every release is built by GitHub Actions and accompanied by
`dist/SHA256SUMS`. To verify a downloaded artifact:

```bash
grep 'TenSeiAi.pyz$' SHA256SUMS | sha256sum -c -
```

Windows PowerShell:

```powershell
$expected = (Get-Content SHA256SUMS | Where-Object { $_ -match 'TenSeiAi.pyz$' }).Split()[0]
$actual = (Get-FileHash TenSeiAi.pyz -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expected) { throw "Checksum mismatch" } else { "Checksum OK" }
```

