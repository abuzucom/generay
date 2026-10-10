# Eval harness

The golden corpus checks `TIME.md` and `SYNC.md` against known cases. Each case
under `cases/` pairs a small fixture with the result a careful reviewer
produces.

## Purpose

The two documents are a system prompt. A well-written prompt gives no guarantee
of model compliance. The corpus turns trust in the prompt into a check. Any
change to a verdict rule, severity rule, or check ships with a new or updated
case.

## Running

`python3 eval/run_eval.py` validates corpus structure and runs the scanners.
`make check` runs that mode. Structure checks cover these properties:

- every `expected.json` parses and holds the required keys
- the mode is PR, File, Piece, Wholesale, or Contract
- the expected verdict fits the mode
- every expected check exists in `TIME.md` or `SYNC.md`
- the scanners report exactly the check IDs in `expected_prescan`
- PR cases hold `diff.patch` and other cases hold an `input.<ext>` file or a named
  configuration file such as `chrony.conf` or `Dockerfile`

`python3 eval/run_eval.py --model-call module:function` runs every case live.
The callable signature is `call_model(system_prompt, mode, case_text) -> str`.
The runner joins `TIME.md` and `SYNC.md` as the system prompt.

`ci.call_model:call_model` provides the repository adapter. Set `MODEL_API_KEY`
outside the repository before a live run.

`--model-call` imports and executes code. Treat the value as trusted input.
Supply it only from a local invocation or CI configuration under repository
control. Never derive it from pull request content.

## Case format

```
eval/cases/<slug>/
  diff.patch | input.<ext> | <config file>   the review unit
  context.md                                 optional PR text or selection note
  expected.json                              required
```

| Field | Meaning |
|---|---|
| `mode` | `PR`, `File`, `Piece`, `Wholesale`, or `Contract` |
| `expected_verdict` | Substring of the final line, such as `BLOCK` or `RISK: HIGH` |
| `expected_checks` | Check IDs the report must list in findings or escalations |
| `expected_prescan` | Check IDs the scanners must report for the fixture. Empty for PR cases |
| `expect_json` | `true` requires a parseable `VERDICT_JSON` line |
| `notes` | Why the verdict holds, for human reviewers |

## Coverage

- Classes C1 to C26 each have one positive case (`cNN-...`) and one clean case.
- Every C27 check has a positive and a clean case (`c27-NN-positive`, `c27-NN-clean`).
- C27.7 has a dedicated set (`c27-07-pos-*`, `c27-07-neg-*`).
- Contract mode has `contract-*` cases.
