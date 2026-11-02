# Cody: Syracuse Code Violations Explorer

This repository contains instructions and an OpenAPI action schema for the [Cody custom GPT](https://chatgpt.com/g/g-kM5rQpBYJ-syracuse-code-violations-explorer). Changes here do not update the live GPT automatically.

The schema discovers live field metadata before querying, describes JSON errors and numeric/null attributes, and supports bounded feature queries, counts, and ID batches. `owner_name` is not a current source field; the default uses verified fields. `issued_to` is not asserted to be ownership.

## Validate

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/check_live.py
```

Offline fixtures were retrieved November 1, 2026. The sample contains only object IDs, violation dates and status labels. The live check makes metadata, count and two-row read-only queries. It does not update the source or the GPT.

`tools/download_arcgis.py` is a reference retrieval implementation and optional CSV export for users who need more than an assistant can retrieve in a session. It is not called automatically by GPT Actions. It inventories IDs, bounds batches, detects missing/duplicate IDs and changing counts, and records whether its row limit truncated the output. An export can still span concurrent value updates.

## Manual GPT verification

An authorized GPT editor must import the schema and instructions into a test copy, validate both actions, and exercise these cases before updating the published GPT:

| Request / condition | Expected behavior |
| --- | --- |
| “How many violation records match this filter?” | Uses a count request; identifies rows versus properties or complaints. |
| “Show all results” with more than one page | Stable IDs/order, bounded pages, retrieved/expected count; incomplete results labeled. |
| “Who owns this property?” | Does not invent owner_name or equate issued_to with ownership. |
| “Was this vacant?” with null Vacant | Says unknown unless documented otherwise. |
| One day or calendar year | Clarifies date field and time zone, then uses half-open range. |
| HTTP 200 containing error | Reports failure; does not say zero matches. |
| Service rate limit | At most two retries; reports persistent failure. |
| Missing IDs, changed count, or unavailable year | Stops completeness claim; narrows the question or offers a download. |
| Map requested | Requests geometry explicitly and states missing-location limitations. |

Schema and reference-helper tests do not prove the hosted GPT will follow every instruction. That behavioral check requires the GPT editor. The city's original disclaimer, feedback form and reporting route remain intact.

## Follow-on work

After the schema change is verified, evaluate a small set of answerable and unanswerable prompts with recorded expected counts and filters. Add approved field definitions and date/time semantics from the source publisher. Consider a read-only query proxy only if observed GPT action limits justify the additional hosting and maintenance; this proposal requires none.
