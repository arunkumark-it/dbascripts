import oci
import sys
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================
REGIONS = [
    "ap-hyderabad-1",
    "ap-mumbai-1",
    "ap-singapore-1",
    "me-abudhabi-1",
    "me-dubai-1",
    "us-ashburn-1",
    "us-phoenix-1",
]

# (header_label, column_width)
COL_DEFS = [
    ("Region",            18),
    ("Instance",          28),
    ("Compartment Path",  48),
    ("Boot Att",           9),
    ("Boot Created",      17),
    ("Boot Backup",       17),
    ("Block Att",         10),
    ("Block Created",     17),
    ("Block Backup",      17),
]


# ============================================================
# TABLE RENDERING  (zero external deps)
# ============================================================
def _sep(col_defs, char="-"):
    return "+" + "+".join(char * (w + 2) for _, w in col_defs) + "+"


def _row(values, col_defs):
    cells = []
    for val, (_, w) in zip(values, col_defs):
        s = str(val) if val is not None else ""
        s = s[:w]                          # hard truncate
        cells.append(f" {s:<{w}} ")
    return "|" + "|".join(cells) + "|"


def print_table(rows, col_defs):
    """Print header + all rows — separators ONLY at top, under header, and at bottom."""
    top = _sep(col_defs, "-")
    mid = _sep(col_defs, "=")   # thick line under header
    bot = _sep(col_defs, "-")
    hdr = _row([h for h, _ in col_defs], col_defs)

    print(top)
    print(hdr)
    print(mid)

    prev_region = None
    for r in rows:
        # Thin separator ONLY when region changes (visual grouping)
        if r[0] != prev_region and prev_region is not None:
            print(_sep(col_defs, "-"))
        prev_region = r[0]
        print(_row(r, col_defs))

    print(bot)


# ============================================================
# COMPARTMENT HELPERS
# ============================================================
def get_all_compartments(identity, tenancy_id):
    return oci.pagination.list_call_get_all_results(
        identity.list_compartments,
        tenancy_id,
        compartment_id_in_subtree=True,
        lifecycle_state="ACTIVE",
    ).data


def build_compartment_path(comp_id, comp_map, tenancy_name="root"):
    path, visited, cid = [], set(), comp_id
    while cid:
        if cid in visited:
            break
        visited.add(cid)
        comp = comp_map.get(cid)
        if comp is None:          # sentinel = tenancy root
            path.append(tenancy_name)
            break
        path.append(comp.name)
        cid = getattr(comp, "compartment_id", None)
        if cid not in comp_map:
            path.append(tenancy_name)
            break
    return " / ".join(reversed(path))


# ============================================================
# DATE HELPERS
# ============================================================
def fmt_dt(dt_obj):
    if not dt_obj:
        return "N/A"
    if hasattr(dt_obj, "strftime"):
        return dt_obj.strftime("%Y-%m-%d %H:%M")
    return str(dt_obj)[:16]


def latest_backup(backups):
    if not backups:
        return "No Backup"
    return fmt_dt(max(backups, key=lambda b: b.time_created).time_created)


# ============================================================
# OCI FETCH HELPERS  (all swallow exceptions gracefully)
# ============================================================
def boot_vol_created(block, bvid):
    try:
        return fmt_dt(block.get_boot_volume(bvid).data.time_created)
    except Exception:
        return "N/A"


def block_vol_created(block, vid):
    try:
        return fmt_dt(block.get_volume(vid).data.time_created)
    except Exception:
        return "N/A"


def boot_backup_time(block, bvid, cid):
    try:
        bkps = oci.pagination.list_call_get_all_results(
            block.list_boot_volume_backups,
            compartment_id=cid,
            boot_volume_id=bvid,
        ).data
        return latest_backup(bkps)
    except oci.exceptions.ServiceError as e:
        return "No Perms" if e.status in (401, 404) else "API Err"
    except Exception:
        return "Error"


def block_backup_time(block, vid, cid):
    try:
        bkps = oci.pagination.list_call_get_all_results(
            block.list_volume_backups,
            compartment_id=cid,
            volume_id=vid,
        ).data
        return latest_backup(bkps)
    except oci.exceptions.ServiceError as e:
        return "No Perms" if e.status in (401, 404) else "API Err"
    except Exception:
        return "Error"


def list_instances(compute, compartments, tenancy_id):
    all_inst, skip = [], {"TERMINATED", "TERMINATING"}
    for cid in [tenancy_id] + [c.id for c in compartments]:
        try:
            page = oci.pagination.list_call_get_all_results(
                compute.list_instances, compartment_id=cid
            ).data
            all_inst.extend(i for i in page if i.lifecycle_state not in skip)
        except Exception:
            continue
    return all_inst


# ============================================================
# COLLECT ROWS FOR ONE REGION  (no printing — pure data)
# ============================================================
def collect_region(region, config):
    cfg = dict(config)
    cfg["region"] = region

    compute    = oci.core.ComputeClient(cfg)
    block      = oci.core.BlockstorageClient(cfg)
    identity   = oci.identity.IdentityClient(cfg)
    tenancy_id = cfg["tenancy"]

    print(f"  Scanning {region} ...", flush=True)

    try:
        compartments = get_all_compartments(identity, tenancy_id)
    except Exception as e:
        print(f"    [WARN] compartment list failed: {e}")
        return [[region, "ERR: compartment list failed", "", "", "", "", "", "", ""]]

    comp_map = {c.id: c for c in compartments}
    comp_map[tenancy_id] = None   # root sentinel

    instances = list_instances(compute, compartments, tenancy_id)
    if not instances:
        return [[region, "(no active instances)", "", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]]

    rows = []
    for inst in instances:
        comp_path = build_compartment_path(inst.compartment_id, comp_map)

        # ---- Boot volume ----
        try:
            bvas = compute.list_boot_volume_attachments(
                availability_domain=inst.availability_domain,
                compartment_id=inst.compartment_id,
                instance_id=inst.id,
            ).data
        except Exception:
            bvas = []

        if bvas:
            bvid         = bvas[0].boot_volume_id
            boot_att     = "Yes"
            boot_created = boot_vol_created(block, bvid)
            boot_bkp     = boot_backup_time(block, bvid, inst.compartment_id)
        else:
            boot_att     = "No"
            boot_created = "N/A"
            boot_bkp     = "N/A"

        # ---- Block volumes (first ATTACHED only) ----
        try:
            vas = [
                v for v in compute.list_volume_attachments(
                    compartment_id=inst.compartment_id,
                    instance_id=inst.id,
                ).data
                if v.lifecycle_state == "ATTACHED"
            ]
        except Exception:
            vas = []

        if vas:
            vid         = vas[0].volume_id
            block_att   = "Yes"
            blk_created = block_vol_created(block, vid)
            block_bkp   = block_backup_time(block, vid, inst.compartment_id)
        else:
            block_att   = "No"
            blk_created = "N/A"
            block_bkp   = "N/A"

        rows.append([
            region,
            inst.display_name,
            comp_path,
            boot_att,
            boot_created,
            boot_bkp,
            block_att,
            blk_created,
            block_bkp,
        ])

    print(f"    -> {len(rows)} instance(s) found", flush=True)
    return rows


# ============================================================
# MAIN
# ============================================================
def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 80)
    print("  OCI BOOT & BLOCK VOLUME AUDIT — ALL REGIONS")
    print(f"  Run time : {ts} UTC")
    print("=" * 80)

    try:
        config = oci.config.from_file("~/.oci/config", "DEFAULT")
    except Exception as e:
        print(f"[ERROR] Cannot load OCI config: {e}")
        sys.exit(1)

    # ── Phase 1: scan ALL regions, accumulate into memory ───────
    print("\nPhase 1 — collecting data from all regions...\n")
    all_rows = []
    for region in REGIONS:
        all_rows.extend(collect_region(region, config))

    # ── Phase 2: render ONE consolidated table ───────────────────
    print(f"\nPhase 2 — printing consolidated table ({len(all_rows)} rows)\n")
    print_table(all_rows, COL_DEFS)

    real = sum(
        1 for r in all_rows
        if r[1] not in ("(no active instances)",) and not r[1].startswith("ERR")
    )
    print(f"\n  Total instances audited : {real}")
    print(f"  Regions scanned        : {len(REGIONS)}")
    print(f"  Report generated at    : {ts} UTC\n")


if __name__ == "__main__":
    main()
