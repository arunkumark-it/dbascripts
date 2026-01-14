#!/usr/bin/env python3
import oci
from oci.pagination import list_call_get_all_results
from datetime import datetime
import json
import csv
import os


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
BACKUP_DIR = "/var/backups/oci_security_lists"
BACKUP_FORMAT = "csv"  # Options: csv, json, both


# ---------------------------------------------------------
# Build compartment path root/parent/child
# ---------------------------------------------------------
def build_compartment_paths(identity, tenancy_id):
    resp = list_call_get_all_results(
        identity.list_compartments,
        tenancy_id,
        compartment_id_in_subtree=True
    )

    comps = [c for c in resp.data if c.lifecycle_state == "ACTIVE"]

    tenancy = identity.get_tenancy(tenancy_id).data
    tenancy.name = "root"
    tenancy.compartment_id = None
    comps.append(tenancy)

    name_map = {c.id: c.name for c in comps}
    parent_map = {c.id: c.compartment_id for c in comps}
    full_paths = {}

    def get_path(cid):
        if cid in full_paths:
            return full_paths[cid]
        names = []
        cur = cid
        while cur:
            names.append(name_map[cur])
            cur = parent_map.get(cur)
        names = list(reversed(names))
        if names == ["root"]:
            full_paths[cid] = None
        else:
            full_paths[cid] = " / ".join(names)
        return full_paths[cid]

    for c in comps:
        get_path(c.id)

    return full_paths


# ---------------------------------------------------------
# Format datetime
# ---------------------------------------------------------
def format_datetime(dt):
    if not dt:
        return ""
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(dt)


# ---------------------------------------------------------
# Parse ICMP options
# ---------------------------------------------------------
def parse_icmp_options(icmp_options):
    if not icmp_options:
        return "", ""
    
    icmp_type = getattr(icmp_options, 'type', '')
    icmp_code = getattr(icmp_options, 'code', '')
    
    return str(icmp_type) if icmp_type is not None else "", str(icmp_code) if icmp_code is not None else ""


# ---------------------------------------------------------
# Parse TCP/UDP options
# ---------------------------------------------------------
def parse_port_range(port_range):
    if not port_range:
        return ""
    
    min_port = getattr(port_range, 'min', '')
    max_port = getattr(port_range, 'max', '')
    
    if min_port == max_port:
        return str(min_port)
    else:
        return f"{min_port}-{max_port}"


# ---------------------------------------------------------
# Parse TCP options
# ---------------------------------------------------------
def parse_tcp_options(tcp_options):
    source_port = ""
    dest_port = ""
    
    if not tcp_options:
        return source_port, dest_port
    
    source_port_range = getattr(tcp_options, 'source_port_range', None)
    dest_port_range = getattr(tcp_options, 'destination_port_range', None)
    
    if source_port_range:
        source_port = parse_port_range(source_port_range)
    
    if dest_port_range:
        dest_port = parse_port_range(dest_port_range)
    
    return source_port, dest_port


# ---------------------------------------------------------
# Parse UDP options
# ---------------------------------------------------------
def parse_udp_options(udp_options):
    source_port = ""
    dest_port = ""
    
    if not udp_options:
        return source_port, dest_port
    
    source_port_range = getattr(udp_options, 'source_port_range', None)
    dest_port_range = getattr(udp_options, 'destination_port_range', None)
    
    if source_port_range:
        source_port = parse_port_range(source_port_range)
    
    if dest_port_range:
        dest_port = parse_port_range(dest_port_range)
    
    return source_port, dest_port


# ---------------------------------------------------------
# Format protocol name
# ---------------------------------------------------------
def format_protocol(protocol):
    protocol_map = {
        '1': 'ICMP',
        '6': 'TCP',
        '17': 'UDP',
        'all': 'All Protocols'
    }
    
    return protocol_map.get(protocol, protocol)


# ---------------------------------------------------------
# Parse ingress rule
# ---------------------------------------------------------
def parse_ingress_rule(rule, rule_direction):
    source = getattr(rule, 'source', '')
    source_type = getattr(rule, 'source_type', 'CIDR_BLOCK')
    protocol = getattr(rule, 'protocol', 'all')
    is_stateless = getattr(rule, 'is_stateless', False)
    description = getattr(rule, 'description', '')
    
    # Protocol details
    protocol_name = format_protocol(protocol)
    
    # Port ranges
    source_port = ""
    dest_port = ""
    icmp_type = ""
    icmp_code = ""
    
    if protocol == '1':  # ICMP
        icmp_options = getattr(rule, 'icmp_options', None)
        icmp_type, icmp_code = parse_icmp_options(icmp_options)
    elif protocol == '6':  # TCP
        tcp_options = getattr(rule, 'tcp_options', None)
        source_port, dest_port = parse_tcp_options(tcp_options)
    elif protocol == '17':  # UDP
        udp_options = getattr(rule, 'udp_options', None)
        source_port, dest_port = parse_udp_options(udp_options)
    
    # Build allows description
    if protocol == '1':  # ICMP
        if icmp_type and icmp_code:
            allows = f"ICMP traffic for: {icmp_type}, {icmp_code} Destination Unreachable: Fragmentation Needed and D"
        elif icmp_type:
            allows = f"ICMP traffic for: {icmp_type}"
        else:
            allows = "ICMP traffic for all types and codes"
    elif protocol == 'all' or protocol == 'All Protocols':
        allows = "All traffic for all ports"
    else:
        if dest_port:
            allows = f"{protocol_name} traffic for ports: {dest_port}"
        else:
            allows = f"{protocol_name} traffic for all ports"
    
    # Add description if exists
    if description:
        allows = f"{allows} ({description})"
    
    return {
        'stateless': 'Yes' if is_stateless else 'No',
        'source': source,
        'ip_protocol': protocol_name,
        'source_port_range': source_port,
        'destination_port_range': dest_port,
        'type_and_code': f"{icmp_type}, {icmp_code}" if (icmp_type or icmp_code) else "",
        'allows': allows,
        'description': description
    }


# ---------------------------------------------------------
# Parse egress rule
# ---------------------------------------------------------
def parse_egress_rule(rule, rule_direction):
    destination = getattr(rule, 'destination', '')
    destination_type = getattr(rule, 'destination_type', 'CIDR_BLOCK')
    protocol = getattr(rule, 'protocol', 'all')
    is_stateless = getattr(rule, 'is_stateless', False)
    description = getattr(rule, 'description', '')
    
    # Protocol details
    protocol_name = format_protocol(protocol)
    
    # Port ranges
    source_port = ""
    dest_port = ""
    icmp_type = ""
    icmp_code = ""
    
    if protocol == '1':  # ICMP
        icmp_options = getattr(rule, 'icmp_options', None)
        icmp_type, icmp_code = parse_icmp_options(icmp_options)
    elif protocol == '6':  # TCP
        tcp_options = getattr(rule, 'tcp_options', None)
        source_port, dest_port = parse_tcp_options(tcp_options)
    elif protocol == '17':  # UDP
        udp_options = getattr(rule, 'udp_options', None)
        source_port, dest_port = parse_udp_options(udp_options)
    
    # Build allows description
    if protocol == '1':  # ICMP
        if icmp_type and icmp_code:
            allows = f"ICMP traffic for: {icmp_type}, {icmp_code}"
        elif icmp_type:
            allows = f"ICMP traffic for: {icmp_type}"
        else:
            allows = "ICMP traffic for all types and codes"
    elif protocol == 'all' or protocol == 'All Protocols':
        allows = "All traffic for all ports"
    else:
        if dest_port:
            allows = f"{protocol_name} traffic for ports: {dest_port}"
        else:
            allows = f"{protocol_name} traffic for all ports"
    
    # Add description if exists
    if description:
        allows = f"{allows} ({description})"
    
    return {
        'stateless': 'Yes' if is_stateless else 'No',
        'destination': destination,
        'ip_protocol': protocol_name,
        'source_port_range': source_port,
        'destination_port_range': dest_port,
        'type_and_code': f"{icmp_type}, {icmp_code}" if (icmp_type or icmp_code) else "",
        'allows': allows,
        'description': description
    }


# ---------------------------------------------------------
# Get security lists for region
# ---------------------------------------------------------
def get_security_lists(region, config):
    print(f"\n=== REGION: {region} ===")
    
    reg_cfg = dict(config)
    reg_cfg["region"] = region

    identity = oci.identity.IdentityClient(reg_cfg)
    network = oci.core.VirtualNetworkClient(reg_cfg)

    tenancy_id = reg_cfg["tenancy"]
    comp_paths = build_compartment_paths(identity, tenancy_id)

    security_lists_data = []

    for comp_id, comp_path in comp_paths.items():
        if not comp_path:
            continue

        try:
            vcns = network.list_vcns(comp_id).data
        except:
            continue

        for vcn in vcns:
            if vcn.lifecycle_state != "AVAILABLE":
                continue

            vcn_name = vcn.display_name
            vcn_id = vcn.id

            try:
                security_lists = network.list_security_lists(comp_id, vcn_id=vcn_id).data
            except:
                continue

            for sec_list in security_lists:
                if sec_list.lifecycle_state != "AVAILABLE":
                    continue

                sec_list_name = sec_list.display_name
                sec_list_id = sec_list.id
                time_created = format_datetime(sec_list.time_created)

                # Get subnets using this security list
                subnets_using = []
                try:
                    subnets = network.list_subnets(comp_id, vcn_id=vcn_id).data
                    for subnet in subnets:
                        if sec_list_id in getattr(subnet, 'security_list_ids', []):
                            subnets_using.append(subnet.display_name)
                except:
                    pass

                subnets_str = ", ".join(subnets_using) if subnets_using else "Not attached"

                # Process ingress rules
                ingress_rules = getattr(sec_list, 'ingress_security_rules', [])
                egress_rules = getattr(sec_list, 'egress_security_rules', [])

                print(f"  Processing: {sec_list_name} ({len(ingress_rules)} ingress, {len(egress_rules)} egress)")

                # Store security list metadata
                sec_list_info = {
                    'region': region,
                    'compartment_path': comp_path,
                    'vcn_name': vcn_name,
                    'vcn_id': vcn_id,
                    'security_list_name': sec_list_name,
                    'security_list_id': sec_list_id,
                    'attached_subnets': subnets_str,
                    'ingress_rule_count': len(ingress_rules),
                    'egress_rule_count': len(egress_rules),
                    'created_date': time_created,
                    'ingress_rules': [],
                    'egress_rules': []
                }

                # Parse ingress rules
                for rule in ingress_rules:
                    parsed_rule = parse_ingress_rule(rule, 'ingress')
                    sec_list_info['ingress_rules'].append(parsed_rule)

                # Parse egress rules
                for rule in egress_rules:
                    parsed_rule = parse_egress_rule(rule, 'egress')
                    sec_list_info['egress_rules'].append(parsed_rule)

                security_lists_data.append(sec_list_info)

    return security_lists_data


# ---------------------------------------------------------
# Save to CSV
# ---------------------------------------------------------
def save_to_csv(security_lists_data, timestamp):
    # Ingress rules CSV
    ingress_csv_file = os.path.join(BACKUP_DIR, f"security_lists_ingress_{timestamp}.csv")
    
    with open(ingress_csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Region', 'Compartment', 'VCN Name', 'Security List Name', 
            'Attached Subnets', 'Stateless', 'Source', 'IP Protocol', 
            'Source Port Range', 'Destination Port Range', 'Type and Code', 
            'Allows', 'Description'
        ])
        
        # Data
        for sec_list in security_lists_data:
            for rule in sec_list['ingress_rules']:
                writer.writerow([
                    sec_list['region'],
                    sec_list['compartment_path'],
                    sec_list['vcn_name'],
                    sec_list['security_list_name'],
                    sec_list['attached_subnets'],
                    rule['stateless'],
                    rule['source'],
                    rule['ip_protocol'],
                    rule['source_port_range'],
                    rule['destination_port_range'],
                    rule['type_and_code'],
                    rule['allows'],
                    rule['description']
                ])
    
    # Egress rules CSV
    egress_csv_file = os.path.join(BACKUP_DIR, f"security_lists_egress_{timestamp}.csv")
    
    with open(egress_csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Region', 'Compartment', 'VCN Name', 'Security List Name', 
            'Attached Subnets', 'Stateless', 'Destination', 'IP Protocol', 
            'Source Port Range', 'Destination Port Range', 'Type and Code', 
            'Allows', 'Description'
        ])
        
        # Data
        for sec_list in security_lists_data:
            for rule in sec_list['egress_rules']:
                writer.writerow([
                    sec_list['region'],
                    sec_list['compartment_path'],
                    sec_list['vcn_name'],
                    sec_list['security_list_name'],
                    sec_list['attached_subnets'],
                    rule['stateless'],
                    rule['destination'],
                    rule['ip_protocol'],
                    rule['source_port_range'],
                    rule['destination_port_range'],
                    rule['type_and_code'],
                    rule['allows'],
                    rule['description']
                ])
    
    print(f"\n✅ CSV backup saved:")
    print(f"   Ingress: {ingress_csv_file}")
    print(f"   Egress: {egress_csv_file}")
    
    return ingress_csv_file, egress_csv_file


# ---------------------------------------------------------
# Save to JSON
# ---------------------------------------------------------
def save_to_json(security_lists_data, timestamp):
    json_file = os.path.join(BACKUP_DIR, f"security_lists_full_{timestamp}.json")
    
    with open(json_file, 'w') as f:
        json.dump(security_lists_data, f, indent=2)
    
    print(f"\n✅ JSON backup saved: {json_file}")
    
    return json_file


# ---------------------------------------------------------
# Print summary
# ---------------------------------------------------------
def print_summary(security_lists_data):
    print("\n" + "="*80)
    print("BACKUP SUMMARY")
    print("="*80)
    
    total_sec_lists = len(security_lists_data)
    total_ingress = sum(sl['ingress_rule_count'] for sl in security_lists_data)
    total_egress = sum(sl['egress_rule_count'] for sl in security_lists_data)
    
    print(f"\nTotal Security Lists: {total_sec_lists}")
    print(f"Total Ingress Rules: {total_ingress}")
    print(f"Total Egress Rules: {total_egress}")
    
    # By region
    by_region = {}
    for sl in security_lists_data:
        region = sl['region']
        by_region[region] = by_region.get(region, 0) + 1
    
    print(f"\nSecurity Lists by Region:")
    for region, count in sorted(by_region.items()):
        print(f"  {region}: {count}")
    
    # By compartment
    by_compartment = {}
    for sl in security_lists_data:
        comp = sl['compartment_path']
        by_compartment[comp] = by_compartment.get(comp, 0) + 1
    
    print(f"\nSecurity Lists by Compartment:")
    for comp, count in sorted(by_compartment.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {comp}: {count}")
    
    # Unattached security lists
    unattached = [sl for sl in security_lists_data if sl['attached_subnets'] == "Not attached"]
    if unattached:
        print(f"\n⚠️  WARNING: {len(unattached)} security list(s) not attached to any subnet:")
        for sl in unattached[:5]:
            print(f"  - {sl['security_list_name']} in {sl['vcn_name']}")


# ---------------------------------------------------------
# Print sample rules
# ---------------------------------------------------------
def print_sample_rules(security_lists_data):
    print("\n" + "="*80)
    print("SAMPLE INGRESS RULES (First 5)")
    print("="*80)
    
    headers = ['Stateless', 'Source', 'IP Protocol', 'Source Port Range', 
               'Destination Port Range', 'Type and Code', 'Allows']
    
    print("\n" + " | ".join(headers))
    print("-" * 200)
    
    count = 0
    for sec_list in security_lists_data:
        if count >= 5:
            break
        for rule in sec_list['ingress_rules']:
            if count >= 5:
                break
            row = [
                rule['stateless'],
                rule['source'],
                rule['ip_protocol'],
                rule['source_port_range'],
                rule['destination_port_range'],
                rule['type_and_code'],
                rule['allows']
            ]
            print(" | ".join(str(x) for x in row))
            count += 1


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    config = oci.config.from_file()

    regions = (
        [r.strip() for r in config.get("regions", "").split(",")]
        if "regions" in config and config["regions"].strip()
        else [config["region"]]
    )

    print("="*80)
    print("OCI SECURITY LIST BACKUP SCRIPT")
    print("="*80)
    print(f"Backup Directory: {BACKUP_DIR}")
    print(f"Backup Format: {BACKUP_FORMAT}")
    print(f"Regions: {', '.join(regions)}")
    print("="*80)

    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Timestamp for backup files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Collect all security lists
    all_security_lists = []
    for region in regions:
        sec_lists = get_security_lists(region, config)
        all_security_lists.extend(sec_lists)

    if not all_security_lists:
        print("\n⚠️  No security lists found!")
        return

    # Save backups
    if BACKUP_FORMAT in ['csv', 'both']:
        save_to_csv(all_security_lists, timestamp)
    
    if BACKUP_FORMAT in ['json', 'both']:
        save_to_json(all_security_lists, timestamp)

    # Print summary
    print_summary(all_security_lists)
    print_sample_rules(all_security_lists)

    print(f"\n✅ Backup completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
