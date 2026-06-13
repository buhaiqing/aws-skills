#!/usr/bin/env python3
"""Topology renderer — ASCII tree, Mermaid diagram, Markdown report (AWS version).

Reads JSON data from TOPO_TMP_DIR (env) or /tmp/.
Supports lazy loading: brief mode skips EC2/EKS/RDS/Lambda files entirely.

Large-scale Mermaid (>50 resources per Subnet) auto-collapses to avoid OOM.

Usage:
  python3 topo-render.py <output_dir> <mode:brief|detailed> <timestamp> <region> [--format ascii|mermaid|both] [--health-json path]
"""

import json, sys, os, argparse

MERMAID_MAX_NODES = 50

parser = argparse.ArgumentParser()
parser.add_argument('output_dir')
parser.add_argument('report_mode', choices=('brief', 'detailed'))
parser.add_argument('timestamp')
parser.add_argument('region_id')
parser.add_argument('--format', choices=('ascii', 'mermaid', 'both'), default='both')
parser.add_argument('--health-json', default=None)
args = parser.parse_args()

output_dir = args.output_dir
report_mode = 'detailed' if args.report_mode == 'detailed' else 'brief'
timestamp = args.timestamp
region_id = args.region_id
output_format = args.format

DATA_DIR = os.environ.get('TOPO_TMP_DIR', '/tmp')

_cache = {}

def load_json(name):
    if name in _cache:
        return _cache[name]
    path = os.path.join(DATA_DIR, f'{name}.json')
    if not os.path.exists(path):
        _cache[name] = {}
        return _cache[name]
    try:
        with open(path) as f:
            _cache[name] = json.load(f)
        return _cache[name]
    except Exception:
        _cache[name] = {}
        return _cache[name]

BRIEF_FILES = ['vpcs', 'subnets', 'elbs', 'nats', 'eips', 'sgs']
DETAILED_FILES = ['ec2', 'eks', 'rds', 'lambda']

for name in BRIEF_FILES:
    load_json(name)
load_json('cloudfront')
load_json('cloudfront_origins')
load_json('apigateway')
load_json('apigatewayv2')
load_json('lambda')
if report_mode == 'detailed':
    for name in DETAILED_FILES:
        load_json(name)

def _get(name, *keys):
    d = _cache.get(name, {})
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, [])
            if isinstance(d, dict):
                continue
        elif isinstance(d, list):
            return d
        else:
            return []
    if isinstance(d, list):
        return d
    return []

def _get_name_tag(tags, default=''):
    if not tags:
        return default
    for t in tags:
        if isinstance(t, dict) and t.get('Key') == 'Name':
            return t.get('Value', default)
    return default

vpcs = _get('vpcs', 'Vpcs')
subnets = _get('subnets', 'Subnets')
elbs = _get('elbs', 'LoadBalancers')
nats = _get('nats', 'NatGateways')
eips = _get('eips', 'Addresses')
sgs = _get('sgs', 'SecurityGroups')

# EC2: nested in Reservations[].Instances[]
ec2_raw = _cache.get('ec2', {})
ec2 = []
for res in ec2_raw.get('Reservations', []):
    ec2.extend(res.get('Instances', []))

rds = _get('rds', 'DBInstances')
eks = _get('eks', 'clusters')  # just names
lambdas = _get('lambda', 'Functions')
apigw_apis = _cache.get('apigateway', {}).get('items', [])
apigw_v2_apis = _cache.get('apigatewayv2', {}).get('Items', [])

cf_raw = _cache.get('cloudfront', {})
cf_dists = cf_raw.get('DistributionList', {}).get('Items', [])
cf_origin_links = _cache.get('cloudfront_origins', {}).get('distributions', [])

# Health overlay
health_data = {}
if args.health_json and os.path.exists(args.health_json):
    try:
        with open(args.health_json) as f:
            health_data = json.load(f)
    except Exception:
        pass

def get_health(resource_id, default='OK'):
    """Lookup health by full id, suffix, or substring match (ALB name, etc.)."""
    candidates = [resource_id]
    if resource_id and '/' in resource_id:
        candidates.append(resource_id.split('/')[-1])
        parts = resource_id.split('/')
        if len(parts) >= 2:
            candidates.append(parts[1])
    for key in candidates:
        if not key:
            continue
        h = health_data.get(key, {})
        if h:
            level = h.get('level', '')
            if level == 'CRITICAL': return 'CRITICAL'
            if level == 'WARNING': return 'WARNING'
            if h.get('z_score', 0) > 2.0: return 'WARNING'
    # Fuzzy: overlay key contained in resource id or vice versa
    for k, h in health_data.items():
        if len(k) < 4:
            continue
        if k in resource_id or resource_id in k:
            level = h.get('level', '')
            if level == 'CRITICAL': return 'CRITICAL'
            if level == 'WARNING': return 'WARNING'
    return default

def mermaid_node_id(prefix, raw):
    safe = (raw or 'x').replace('-', '_').replace('.', '_').replace(':', '_')[:24]
    return f"{prefix}_{safe}"

# Build Subnet -> resources mapping
sub_map = {}
for s in subnets:
    sid = s.get('SubnetId', '')
    sub_map[sid] = {
        'name': _get_name_tag(s.get('Tags'), sid),
        'cidr': s.get('CidrBlock', ''),
        'az': s.get('AvailabilityZone', ''),
        'ec2': [], 'elb': [], 'rds': []
    }

for i in ec2:
    sid = i.get('SubnetId', '')
    sub_map.get(sid, {}).setdefault('ec2', []).append({
        'name': _get_name_tag(i.get('Tags'), i.get('InstanceId', '')),
        'id': i.get('InstanceId', ''),
        'ip': i.get('PrivateIpAddress', ''),
        'type': i.get('InstanceType', ''),
        'status': i.get('State', {}).get('Name', '')
    })

for l in elbs:
    for az_info in l.get('AvailabilityZones', []):
        sid = az_info.get('SubnetId', '')
        sub_map.get(sid, {}).setdefault('elb', []).append({
            'name': l.get('LoadBalancerName', ''),
            'id': l.get('LoadBalancerArn', ''),
            'dns': l.get('DNSName', ''),
            'type': l.get('Type', '')
        })

for d in rds:
    subnet_group = d.get('DBSubnetGroup', {})
    for sub in subnet_group.get('Subnets', []):
        sid = sub.get('SubnetIdentifier', '')
        sub_map.get(sid, {}).setdefault('rds', []).append({
            'name': d.get('DBInstanceIdentifier', ''),
            'id': d.get('DBInstanceIdentifier', ''),
            'engine': f"{d.get('Engine', '')} {d.get('EngineVersion', '')}",
            'endpoint': d.get('Endpoint', {}).get('Address', '')
        })
    break  # RDS appears once per subnet group

total_resources = sum(len(vs.get('ec2',[])) + len(vs.get('elb',[])) + len(vs.get('rds',[])) for vs in sub_map.values())
large_scale = total_resources > MERMAID_MAX_NODES

primary_vpc = vpcs[0] if vpcs else {}
vpc_id = primary_vpc.get('VpcId', '')
vpc_name = _get_name_tag(primary_vpc.get('Tags'), vpc_id)
project_name = os.getenv('TOPO_PROJECT_NAME', vpc_name)

def resource_line(it, indent='   '):
    h = get_health(it.get('id', ''))
    marker = {'CRITICAL': '[!!]', 'WARNING': '[!]', 'OK': '[ok]'}[h]
    if 'ip' in it and it['ip']:
        return f"{indent}{marker} {it['name']}: {it['ip']} ({it.get('type', '')})"
    elif 'dns' in it:
        return f"{indent}{marker} {it['name']}: {it['dns']} ({it.get('type', '')})"
    elif 'endpoint' in it:
        return f"{indent}{marker} {it['name']}: {it['endpoint']} ({it.get('engine', '')})"
    return f"{indent}{marker} {it['name']}"

def render_ascii():
    lines = []
    lines.append(f"# {project_name} - AWS Network Topology & Resource Inventory")
    lines.append(f"> Generated: {timestamp} | Region: {region_id} | Mode: {'detailed' if report_mode == 'detailed' else 'brief'}")
    lines.append("---")
    lines.append("## VPC Network Topology")
    lines.append("")
    lines.append(f"**VPC**: {vpc_name} ({vpc_id})  **CIDR**: {primary_vpc.get('CidrBlock', '')}")
    lines.append("```")

    for sid, vs in sub_map.items():
        lines.append(f"|- Subnet: {vs['name']} ({vs['cidr']}) ~ {vs['az']}")
        items = vs.get('ec2', []) + vs.get('elb', []) + vs.get('rds', [])
        if not items:
            lines.append("|  \\- (empty)")
        else:
            for idx, it in enumerate(items[:MERMAID_MAX_NODES]):
                last = idx == len(items) - 1 or idx == MERMAID_MAX_NODES - 1
                pfx = "|  \\- " if last else "|  |- "
                lines.append(resource_line(it, f"   {pfx}"))
            if len(items) > MERMAID_MAX_NODES:
                lines.append(f"   |  \\- ... ({len(items) - MERMAID_MAX_NODES} more)")
    lines.append("```")
    lines.append("")
    if len(vpcs) > 1:
        lines.append(f"> Detected {len(vpcs)} VPCs, showing primary ({vpc_id}). Others: {', '.join(v.get('VpcId','') for v in vpcs[1:])}")
        lines.append("")
    lines.append("---")
    lines.append("")

    if health_data:
        lines.append("## Health Summary")
        lines.append("")
        lines.append("| Resource | Type | Health | Z-Score |")
        lines.append("|---|---|---|---|")
        for rid, h in health_data.items():
            hl = h.get('level', '')
            z = h.get('z_score', 0)
            emoji = 'CRITICAL' if hl == 'CRITICAL' else ('WARNING' if hl == 'WARNING' else 'OK')
            lines.append(f"| {rid} | {h.get('type','')} | {emoji} | {z} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Resource Statistics")
    lines.append("| Resource Type | Count | Notes |")
    lines.append("|---|---|---|")
    lines.append(f"| VPC | {len(vpcs)} | {vpc_name}" + (f" + {len(vpcs)-1} more" if len(vpcs) > 1 else "") + " |")
    lines.append(f"| Subnet | {len(subnets)} | {primary_vpc.get('CidrBlock', '')} |")
    lines.append(f"| EC2 | {len(ec2)} | {sum(1 for i in ec2 if i.get('State',{}).get('Name')=='running')} running |")
    lines.append(f"| ELB (ALB/NLB) | {len(elbs)} | {len(elbs)} active |")
    lines.append(f"| Elastic IP | {len(eips)} | {sum(1 for e in eips if e.get('InstanceId'))} associated |")
    lines.append(f"| NAT Gateway | {len(nats)} | {sum(1 for n in nats if n.get('State')=='available')} available |")
    lines.append(f"| Security Group | {len(sgs)} | - |")
    lines.append(f"| CloudFront | {len(cf_dists)} | edge distributions |")
    lines.append(f"| API Gateway (REST) | {len(apigw_apis)} | CF origin linking |")
    lines.append(f"| API Gateway (HTTP v2) | {len(apigw_v2_apis)} | CF origin linking |")

    if cf_dists:
        lines.append("")
        lines.append("### CloudFront Edge")
        lines.append("| Distribution | Domain | Health |")
        lines.append("|---|---|---|")
        for dist in cf_dists:
            did = dist.get('Id', '')
            domain = dist.get('DomainName', did)
            hl = get_health(did)
            lines.append(f"| {did} | {domain} | {hl} |")
        if cf_origin_links:
            lines.append("")
            lines.append("### CloudFront → Origin Links")
            lines.append("| Distribution | Origin | Domain | Kind | Default | Path rules |")
            lines.append("|---|---|---|---|---|---|")
            for entry in cf_origin_links:
                did = entry.get('distributionId', '')
                for origin in entry.get('origins', []):
                    paths = origin.get('usedByPaths') or []
                    path_txt = ", ".join(paths[:3]) + ("…" if len(paths) > 3 else "")
                    if origin.get('isDefault') and not paths:
                        path_txt = path_txt or "(default behavior)"
                    lines.append(
                        f"| {did} | {origin.get('id', '')} | {origin.get('domain', '')} "
                        f"| {origin.get('kind', 'custom')} "
                        f"| {'yes' if origin.get('isDefault') else 'no'} | {path_txt or '-'} |"
                    )
            multi = [e for e in cf_origin_links if len(e.get('cacheBehaviors', [])) > 0]
            if multi:
                lines.append("")
                lines.append("### CloudFront Cache Behaviors (non-default)")
                lines.append("| Distribution | Path pattern | Target origin |")
                lines.append("|---|---|---|")
                for entry in multi:
                    did = entry.get('distributionId', '')
                    for cb in entry.get('cacheBehaviors', []):
                        lines.append(
                            f"| {did} | {cb.get('pathPattern', '')} | {cb.get('targetOriginId', '')} |"
                        )
            og_entries = [e for e in cf_origin_links if e.get('originGroups')]
            if og_entries:
                lines.append("")
                lines.append("### CloudFront Origin Groups (failover)")
                lines.append("| Distribution | Group | Members (order) | Failover HTTP codes |")
                lines.append("|---|---|---|---|")
                for entry in og_entries:
                    did = entry.get('distributionId', '')
                    for og in entry.get('originGroups', []):
                        members = " → ".join(og.get('members', []))
                        codes = ", ".join(str(c) for c in og.get('failoverStatusCodes', []))
                        lines.append(f"| {did} | {og.get('id', '')} | {members} | {codes or '-'} |")

    if report_mode == 'detailed':
        lines.append("")
        lines.append("### Detailed Inventory")
        lines.append("| Type | Name/ID | Spec/Engine | IP/Endpoint | AZ |")
        lines.append("|---|---|---|---|---|")
        for i in ec2:
            name = _get_name_tag(i.get('Tags'), i.get('InstanceId', ''))
            lines.append(f"| EC2 | {name} | {i.get('InstanceType','')} | {i.get('PrivateIpAddress','')} | {i.get('Placement',{}).get('AvailabilityZone','')} |")
        for d in rds:
            lines.append(f"| RDS | {d.get('DBInstanceIdentifier','')} | {d.get('Engine','')} {d.get('EngineVersion','')} ({d.get('DBInstanceClass','')}) | {d.get('Endpoint',{}).get('Address','')} | {d.get('AvailabilityZone','')} |")
        for c in eks:
            lines.append(f"| EKS | {c} | - | - | - |")
        for fn in lambdas:
            lines.append(f"| Lambda | {fn.get('FunctionName','')} | {fn.get('Runtime','')} | {fn.get('MemorySize','')}MB / {fn.get('Timeout','')}s | - |")

    lines.append("")
    lines.append("---")
    lines.append("> Generated by aws-topo-discovery | Safety Mode: READ-ONLY")
    return '\n'.join(lines)

def render_mermaid():
    lines = []
    mermaid_classes = []
    lines.append("```mermaid")
    lines.append("graph TB")
    lines.append("    classDef healthCritical fill:#fee2e2,stroke:#dc2626,color:#991b1b")
    lines.append("    classDef healthWarning fill:#fef3c7,stroke:#d97706,color:#92400e")
    lines.append("    classDef healthOk fill:#ecfdf5,stroke:#059669,color:#065f46")

    def apply_health(node_id, resource_id):
        h = get_health(resource_id)
        if h == 'CRITICAL':
            mermaid_classes.append(f"    class {node_id} healthCritical")
        elif h == 'WARNING':
            mermaid_classes.append(f"    class {node_id} healthWarning")

    def edge_label(origin: dict) -> str:
        paths = origin.get('usedByPaths') or []
        if paths:
            p = paths[0].replace('"', "'")
            return p[:24] + ('…' if len(p) > 24 else '')
        if origin.get('isDefault'):
            return 'default'
        return 'origin'

    apigw_id_to_node = {}
    for api in apigw_apis:
        api_id = str(api.get('id', ''))
        name = api.get('name', api_id)
        node = mermaid_node_id('apigw', api_id)
        apigw_id_to_node[api_id] = (node, name)

    apigw_v2_id_to_node = {}
    for api in apigw_v2_apis:
        api_id = api.get('ApiId', '')
        name = api.get('Name', api_id)
        node = mermaid_node_id('apigwv2', api_id)
        apigw_v2_id_to_node[api_id] = (node, name)

    lambda_url_to_node = {}
    lambda_name_to_node = {}
    for fn in lambdas:
        fname = fn.get('FunctionName', '')
        node = mermaid_node_id('fn', fname)
        lambda_name_to_node[fname] = node
        furl = fn.get('FunctionUrlConfig') or {}
        url = furl.get('FunctionUrl', '')
        if url:
            host = url.split('//', 1)[-1].split('/')[0]
            lambda_url_to_node[host] = node

    serverless_nodes = set()

    edge_node_ids = set()
    if cf_dists or any(h.get('type') in ('CloudFront', 'S3') for h in health_data.values()):
        lines.append("    subgraph EDGE[CloudFront / S3 Edge]")
        for dist in cf_dists:
            did = dist.get('Id', '')
            domain = dist.get('DomainName', did)
            node = mermaid_node_id('cf', did)
            edge_node_ids.add(node)
            lines.append(f"        {node}[\"CF: {domain}\\n{did}\"]")
            apply_health(node, did)
        for rid, h in health_data.items():
            if h.get('type') != 'S3':
                continue
            node = mermaid_node_id('s3', rid)
            if node in edge_node_ids:
                continue
            edge_node_ids.add(node)
            lines.append(f"        {node}[\"S3: {rid}\"]")
            apply_health(node, rid)
        if not edge_node_ids:
            lines.append("        edge_empty[(\"(empty)\")]")
        lines.append("    end")

    # Pre-collect serverless targets referenced by CloudFront
    for entry in cf_origin_links:
        for origin in entry.get('origins', []):
            kind = origin.get('kind', 'custom')
            domain = origin.get('domain', '')
            if kind in ('apigw', 'apigw_v2'):
                api_id = domain.split('.')[0]
                if kind == 'apigw_v2' and api_id in apigw_v2_id_to_node:
                    serverless_nodes.add(apigw_v2_id_to_node[api_id][0])
                elif api_id in apigw_id_to_node:
                    serverless_nodes.add(apigw_id_to_node[api_id][0])
            elif kind == 'lambda_url':
                node = lambda_url_to_node.get(domain)
                if node:
                    serverless_nodes.add(node)

    if serverless_nodes:
        lines.append("    subgraph SERVERLESS[API Gateway / Lambda URL]")
        for api in apigw_apis:
            api_id = str(api.get('id', ''))
            node, name = apigw_id_to_node.get(api_id, ('', ''))
            if node and node in serverless_nodes:
                lines.append(f"        {node}[\"REST API: {name}\\n{api_id}\"]")
                apply_health(node, api_id)
        for api in apigw_v2_apis:
            api_id = api.get('ApiId', '')
            node, name = apigw_v2_id_to_node.get(api_id, ('', ''))
            if node and node in serverless_nodes:
                lines.append(f"        {node}[\"HTTP API: {name}\\n{api_id}\"]")
                apply_health(node, api_id)
        for fn in lambdas:
            fname = fn.get('FunctionName', '')
            node = lambda_name_to_node.get(fname, '')
            if node and node in serverless_nodes:
                lines.append(f"        {node}[\"Lambda URL: {fname}\"]")
                apply_health(node, fname)
        lines.append("    end")

    lines.append(f"    subgraph VPC[{vpc_name} ({vpc_id})]")

    for sid, vs in sub_map.items():
        safe_sub = f"sub_{sid.replace('-','_')[:20]}"
        lines.append(f"    subgraph {safe_sub}[{vs['name']} | {vs['cidr']} ~ {vs['az']}]")
        items = vs.get('ec2', []) + vs.get('elb', []) + vs.get('rds', [])

        if large_scale and len(items) > MERMAID_MAX_NODES:
            ec2_count = len(vs.get('ec2', []))
            elb_count = len(vs.get('elb', []))
            rds_count = len(vs.get('rds', []))
            parts = []
            if ec2_count: parts.append(f"EC2 x{ec2_count}")
            if elb_count: parts.append(f"ELB x{elb_count}")
            if rds_count: parts.append(f"RDS x{rds_count}")
            label = " | ".join(parts) if parts else "(empty)"
            safe_id = f"agg_{sid.replace('-','_')[:20]}"
            lines.append(f"        {safe_id}[\"{label}\"]")
        else:
            for it in items:
                rid = it.get('id', '') or it.get('name', '')
                safe_id = mermaid_node_id('res', rid)
                label = it['name']
                if 'ip' in it and it['ip']:
                    label += f"\\n{it['ip']}"
                elif 'dns' in it:
                    label += f"\\n{it['dns']}"
                lines.append(f"        {safe_id}[\"{label}\"]")
                apply_health(safe_id, rid)
            if not items:
                lines.append("        empty_spot[(\"(empty)\")]")
        lines.append("    end")

    for l in elbs:
        lb_name = l.get('LoadBalancerName', '')
        lb_arn = l.get('LoadBalancerArn', '')
        safe_lb = mermaid_node_id('lb', lb_arn or lb_name)
        lines.append(f"    {safe_lb}[\"{lb_name}\\n{l.get('Type','')}\"]")
        apply_health(safe_lb, lb_arn or lb_name)

    lines.append("    end")

    # CF → ALB / S3 origin edges (from get-distribution-config)
    cf_id_to_node = {}
    for dist in cf_dists:
        did = dist.get('Id', '')
        if did:
            cf_id_to_node[did] = mermaid_node_id('cf', did)
    lb_dns_to_node = {}
    for l in elbs:
        dns = l.get('DNSName', '')
        if dns:
            lb_dns_to_node[dns] = mermaid_node_id('lb', l.get('LoadBalancerArn') or l.get('LoadBalancerName', ''))
    def target_for_origin(origin: dict) -> tuple[str | None, str]:
        """Return (mermaid_node_id, inline_suffix) for an origin dict."""
        domain = origin.get('domain', '')
        kind = origin.get('kind', 'custom')
        if kind == 'alb':
            return lb_dns_to_node.get(domain), ''
        if kind == 's3':
            bucket = domain.split('.s3.')[0] if '.s3.' in domain else domain
            return mermaid_node_id('s3', bucket), ''
        if kind == 'apigw_v2':
            api_id = domain.split('.')[0]
            pair = apigw_v2_id_to_node.get(api_id)
            return (pair[0], '') if pair else (None, '')
        if kind == 'apigw':
            api_id = domain.split('.')[0]
            pair = apigw_id_to_node.get(api_id)
            return (pair[0], '') if pair else (None, '')
        if kind == 'lambda_url':
            return lambda_url_to_node.get(domain), ''
        if kind == 'custom' and domain:
            return mermaid_node_id('custom', domain), f"[\"{domain[:40]}\"]"
        return None, ''

    mermaid_edges = []
    origin_id_to_origin = {}
    for entry in cf_origin_links:
        for origin in entry.get('origins', []):
            origin_id_to_origin[origin.get('id', '')] = origin

    for entry in cf_origin_links:
        cf_node = cf_id_to_node.get(entry.get('distributionId', ''))
        if not cf_node:
            continue

        # Origin group failover (primary -.-> failover)
        for og in entry.get('originGroups', []):
            members = og.get('members', [])
            codes = og.get('failoverStatusCodes', [])
            code_label = ",".join(str(c) for c in codes[:4]) if codes else "5xx"
            for i in range(len(members) - 1):
                o1 = origin_id_to_origin.get(members[i], {})
                o2 = origin_id_to_origin.get(members[i + 1], {})
                n1, _ = target_for_origin(o1) if o1 else (None, '')
                n2, sfx2 = target_for_origin(o2) if o2 else (None, '')
                if n1 and n2:
                    if sfx2 and '[' not in n2:
                        mermaid_edges.append(f"    {n1} -.->|failover {code_label}| {n2}{sfx2}")
                    else:
                        mermaid_edges.append(f"    {n1} -.->|failover {code_label}| {n2}")

        default_gid = entry.get('defaultOriginId', '')
        group_ids = {g.get('id') for g in entry.get('originGroups', [])}

        for origin in entry.get('origins', []):
            og = origin.get('originGroup') or {}
            if entry.get('defaultTargetsOriginGroup') and default_gid in group_ids:
                if og.get('groupId') == default_gid and og.get('role') != 'primary':
                    if not origin.get('usedByPaths'):
                        continue
            elabel = edge_label(origin)
            if og.get('groupId') and og.get('role') == 'primary' and (
                entry.get('defaultTargetsOriginGroup') and default_gid == og.get('groupId')
            ):
                elabel = f"group:{og.get('groupId', '')[:16]}"
            target, suffix = target_for_origin(origin)
            if target:
                mermaid_edges.append(f"    {cf_node} -->|{elabel}| {target}{suffix}")
            elif origin.get('kind') == 'custom' and origin.get('domain'):
                custom_node = mermaid_node_id('custom', origin.get('domain', ''))
                mermaid_edges.append(
                    f"    {cf_node} -->|{elabel}| {custom_node}[\"{origin.get('domain', '')[:40]}\"]"
                )
    lines.extend(mermaid_edges)
    lines.extend(mermaid_classes)
    lines.append("```")
    return '\n'.join(lines)

# Render and write output
os.makedirs(output_dir, exist_ok=True)
ascii_content = render_ascii()
mermaid_content = render_mermaid()

if output_format in ('ascii', 'both'):
    path = os.path.join(output_dir, "report.md")
    if output_format == 'both':
        parts = ascii_content.split("---\n")
        if len(parts) >= 2:
            first_part = parts[0]
            rest = "---\n".join(parts[1:])
            combined = first_part + "---\n\n## Topology Diagram\n\n" + mermaid_content + "\n\n---\n" + rest
        else:
            combined = ascii_content + "\n\n## Topology Diagram\n\n" + mermaid_content
    else:
        combined = ascii_content
    with open(path, 'w') as f:
        f.write(combined)
    print(f"Report: {path} ({os.path.getsize(path)} bytes)")

if output_format in ('mermaid',):
    path = os.path.join(output_dir, "topology.mermaid.md")
    with open(path, 'w') as f:
        f.write(mermaid_content)
    print(f"Mermaid: {path} ({os.path.getsize(path)} bytes)")
