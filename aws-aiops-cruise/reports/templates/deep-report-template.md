# Deep Patrol Report — {{customer}}

## Executive summary

- **Overall**: {{overall_grade}}
- **Critical**: {{critical_count}}
- **Warning**: {{warning_count}}

## Chain inference

{{chain_inference_markdown}}

## Incidents

{{incident_table}}

## Trace

- Account: {{account_id}}
- First command: `aws sts get-caller-identity`
- Output: {{json_path}}
