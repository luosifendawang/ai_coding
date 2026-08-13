# Weekly Confidence

gitplus treats weekly reports as evidence-backed summaries, not performance reviews.

## Levels

- `high`: direct commit, confirmed CommitRecord, or Worklog source.
- `medium`: sourced but requiring user judgement, such as uncommitted work or model aggregation.
- `low`: missing or weak source.

## Rules

- Formal report items must have at least one source.
- Low confidence items cannot enter a formal report.
- Medium confidence items require user confirmation unless already confirmed.
- Quantified or evaluative claims must be supported by source data.
- Code volume is not used as a work quality score.

## Validation

`WeeklyFactValidator` checks:

- missing sources
- invalid source labels
- low confidence formal content
- medium confidence content requiring confirmation
- unsupported exaggerated phrases and unsupported metrics

Validation returns source coverage, blocked item IDs, and items requiring confirmation.
