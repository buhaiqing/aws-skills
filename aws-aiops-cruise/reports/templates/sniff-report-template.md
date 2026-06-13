# Sniff Report — {{customer}} / {{region}}

**Run ID**: {{run_id}}  
**Grade**: {{overall_grade}}  
**Scope**: {{scope_type}} = {{scope_value}}

## Resources discovered

| Layer | Count |
|-------|-------|
| ALB | {{alb_count}} |
| EC2 | {{ec2_count}} |
| RDS | {{rds_count}} |
| ElastiCache | {{cache_count}} |
| NAT | {{nat_count}} |

## Top findings (preview)

{{finding_list}}

> Full JSON: `audit-results/cruise-{{run_id_short}}.json`
