#!/usr/bin/env python3
import oci
from collections import defaultdict
from oci.pagination import list_call_get_all_results

# Optionally override regions here; if empty, script reads "regions" or "region" from ~/.oci/config
REGIONS_OVERRIDE = []  # e.g. ["ap-hyderabad-1", "us-ashburn-1"] ; leave empty to use config

# ------------------------------------------------------------------
# Helper: build compartment map and full path (root → a → b)
# ------------------------------------------------------------------
def build_compartment_paths(identity_client, tenancy_id):
    # List all compartments (active and in subtree)
    resp = list_call_get_all_results(
        identity_client.list_compartments,
        tenancy_id,
        compartment_id_in_subtree=True
    )
    comps = [c for c in resp.data if c.lifecycle_state == "ACTIVE"]

    # include root
    root = identity_client.get_compartment(tenancy_id).data
    comps.append(root)

    # maps
    name_map = {c.id: c.name for c in comps}
    parent_map = {c.id: c.compartment_id for c in comps}

    # ensure root name
    name_map[tenancy_id] = name_map.get(tenancy_id, "root")

    # build full path using DFS
    full_path = {}

    def compute_path(cid):
        if cid == tenancy_id:
            return "root"
        if cid in full_path:
            return full_path[cid]
        path_parts = []
        current = cid
        # climb until root or unknown
        while current and current in name_map and current != tenancy_id:
            path_parts.append(name_map.get(current, "unknown"))
            current = parent_map.get(current)
        path = "root"
        if path_parts:
            path += " → " + " → ".join(reversed(path_parts))
        full_path[cid] = path
        return path

    # compute for all compartments
    for c in comps:
        compute_path(c.id)

    return full_path


# ------------------------------------------------------------------
# Helper: load shapes for a region (cache)
# ------------------------------------------------------------------
def load_shapes_for_region(config, region, tenancy_id):
    cfg = dict(config)  # shallow copy
    cfg["region"] = region
    compute_client = oci.core.ComputeClient(cfg)
    # list_shapes requires a compartment_id param in many SDK versions (use tenancy)
    shapes = list_call_get_all_results(compute_client.list_shapes, compartment_id=tenancy_id).data
    return {s.shape: s for s in shapes}


# ------------------------------------------------------------------
# Helper: extract IPs and boot volume size for one instance
# ------------------------------------------------------------------
def get_network_and_boot_info(config, region, instance):
    cfg = dict(config)
    cfg["region"] = region
    compute_client = oci.core.ComputeClient(cfg)
    vn_client = oci.core.VirtualNetworkClient(cfg)
    block_client = oci.core.BlockstorageClient(cfg)

    private_ips = []
    public_ips = []
    boot_size_gb = ""

    # VNIC attachments (use compute.list_vnic_attachments)
    try:
        vnic_atts = list_call_get_all_results(
            compute_client.list_vnic_attachments,
            compartment_id=instance.compartment_id,
            instance_id=instance.id
        ).data

        for att in vnic_atts:
            try:
                vnic = vn_client.get_vnic(att.vnic_id).data
                if vnic.private_ip:
                    private_ips.append(vnic.private_ip)
                if vnic.public_ip:
                    public_ips.append(vnic.public_ip)
            except Exception:
                # skip vnic if cannot fetch
                continue
    except Exception:
        pass

    # Boot volume attachments (requires availability_domain & compartment_id & instance_id)
    try:
        bva = list_call_get_all_results(
            compute_client.list_boot_volume_attachments,
            availability_domain=instance.availability_domain,
            compartment_id=instance.compartment_id,
            instance_id=instance.id
        ).data
        if bva:
            # take first boot volume
            try:
                bv = block_client.get_boot_volume(bva[0].boot_volume_id).data
                boot_size_gb = str(bv.size_in_gbs)
            except Exception:
                boot_size_gb = ""
    except Exception:
        boot_size_gb = ""

    return (",".join(private_ips) if private_ips else "-",
            ",".join(public_ips) if public_ips else "-",
            boot_size_gb if boot_size_gb else "-")

# ------------------------------------------------------------------
# Main inventory collector
# ------------------------------------------------------------------
def main():
    # load default config
    config = oci.config.from_file()  # ~/.oci/config, DEFAULT profile
    tenancy_id = config["tenancy"]

    # determine regions
    if REGIONS_OVERRIDE:
        regions = REGIONS_OVERRIDE
    else:
        if "regions" in config and config["regions"].strip():
            regions = [r.strip() for r in config["regions"].split(",")]
        else:
            regions = [config.get("region")]

    # build compartment paths once (identity can be created with a valid region from config)
    identity_for_comp = oci.identity.IdentityClient(config)
    comp_paths = build_compartment_paths(identity_for_comp, tenancy_id)

    # Prepare output rows
    rows = []

    # cache shapes per region for OCPUs/memory
    shapes_cache = {}

    for region in regions:
        print(f"Collecting from region: {region} ...")
        # load shapes once per region
        try:
            shapes_cache[region] = load_shapes_for_region(config, region, tenancy_id)
        except Exception:
            shapes_cache[region] = {}

        # create compute client for listing instances (region-specific)
        cfg = dict(config)
        cfg["region"] = region
        compute_client = oci.core.ComputeClient(cfg)

        # iterate compartments (comp_paths keys)
        for comp_id, comp_path in comp_paths.items():
            # list instances in this compartment (all states)
            try:
                instances = list_call_get_all_results(compute_client.list_instances, comp_id).data
            except Exception:
                continue

            for inst in instances:
                # shape -> ocpus/memory: prefer instance.shape_config for flex shapes
                ocpus = ""
                memory = ""
                if inst.shape_config:
                    ocpus = getattr(inst.shape_config, "ocpus", "")
                    memory = getattr(inst.shape_config, "memory_in_gbs", "")
                else:
                    # fallback to shapes cache
                    s = shapes_cache.get(region, {}).get(inst.shape)
                    if s:
                        ocpus = getattr(s, "ocpus", "")
                        memory = getattr(s, "memory_in_gbs", "")

                # network and boot info
                private_ip, public_ip, boot_vol_gb = get_network_and_boot_info(config, region, inst)

                rows.append({
                    "region": region,
                    "compartment_path": comp_path.replace("/", "").strip() if comp_path else "root",  # remove leading slash
                    "name": inst.display_name or "-",
                    "shape": inst.shape or "-",
                    "ocpus": str(ocpus) if ocpus is not None else "-",
                    "memory": str(memory) if memory is not None else "-",
                    "private_ip": private_ip,
                    "public_ip": public_ip,
                    "boot_volume_gb": boot_vol_gb
                })

    # Print header + rows in a clean tabular format
    headers = ["region", "compartment_path", "name", "shape", "ocpus", "memory", "private_ip", "public_ip", "boot_volume_gb"]
    # compute column widths
    col_widths = {h: max(len(h), 12) for h in headers}
    for r in rows:
        for h in headers:
            col_widths[h] = max(col_widths[h], len(str(r[h])))

    # header line
    header_line = " | ".join(f"{h.upper():{col_widths[h]}}" for h in headers)
    sep_line = "-".join("-" * (col_widths[h] + 2) for h in headers)

    print("\n" + header_line)
    print(sep_line)

    for r in rows:
        line = " | ".join(f"{str(r[h]):{col_widths[h]}}" for h in headers)
        print(line)

    print(f"\nTotal instances: {len(rows)}")

if __name__ == "__main__":
    main()
