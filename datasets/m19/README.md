# M19 local evaluation dataset

This folder contains generic query definitions and a fabricated schema example. It must never contain real track IDs, private filenames, real judgments, or evaluation reports.

## Query set

The versioned query set is queries-v1.json. Facets and notes are judging context and coverage descriptors; they are not automatic relevance labels. Human judgments must be based on independent musical observations, not the retriever's own score, rank, mode, or match trace.

## Preparing local judgments

1. Run the existing retrieval modes for the chosen generic queries and record each mode's ordered top-10 results.
2. Build one frozen-pool manifest entry per query. The members must be the distinct union of those ordered lists. Record dataset version, modes compared, candidate limits, and each mode's ordered result list.
3. Blind and shuffle the pooled candidates, then manually assign grades 0 through 3 per query and track. An absent grade means unjudged, not grade zero.
4. Keep real data at data/eval/judgments.local.json. Do not put it here or in source control.

Before any judgment or report write, both commands must succeed and show an ignore rule:

    git check-ignore -v data/eval/judgments.local.json
    git check-ignore -v data/eval/reports/baseline-report.json

The implementation rechecks both paths and the selected input/output paths before report I/O. If either check fails, stop. Reports are local by default and contain track identifiers.

The file judgments.example.json is a worked schema fixture for q001 only. Its synthetic identifiers are fabricated; it is not a complete judgment dataset and cannot be used to evaluate the full 30-query set.

Dataset versions use MAJOR.MINOR.PATCH. Follow the versioning rules in the M19 evaluation dataset specification. Changing any frozen pool requires a MAJOR version change and re-judgment.
