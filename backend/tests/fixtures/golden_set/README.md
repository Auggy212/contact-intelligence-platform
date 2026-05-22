# Golden Set Annotations

Place one `.json` file here for every `.docx` in `tests/fixtures/contracts/`.
The file stem must match (e.g. `nda_sample.docx` → `nda_sample.json`).

## Annotation format

```json
{
  "contract_name": "nda_sample.docx",
  "notes": "Standard 2-year NDA with Mumbai jurisdiction",
  "expected_findings": [
    {
      "flag_type": "missing_clause",
      "severity": "critical",
      "title_contains": "Indemnification"
    },
    {
      "flag_type": "law_violation",
      "severity": "high",
      "title_contains": "IT Act"
    },
    {
      "flag_type": "checklist_fail",
      "severity": "critical",
      "title_contains": "Agreement Duration"
    }
  ]
}
```

## Fields

| Field | Required | Description |
|---|---|---|
| `flag_type` | yes | Exact match: `missing_clause`, `weakened_clause`, `modified`, `deleted`, `added`, `law_violation`, `law_at_risk`, `checklist_fail`, `checklist_not_found` |
| `severity` | yes | Exact match: `critical`, `high`, `medium`, `low`, `info` |
| `title_contains` | no | Case-insensitive substring match on finding title |
| `description_contains` | no | Case-insensitive substring match on description |

The evaluator uses greedy matching — each expected finding is matched to at
most one actual finding. A finding counts as True Positive if ALL specified
fields match.
