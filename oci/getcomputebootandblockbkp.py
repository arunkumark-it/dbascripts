import oci
from prettytable import PrettyTable


# -------------------------------------------
# Build Full Compartment Path (Hierarchy)
# -------------------------------------------
def build_compartment_path(comp_id, comp_map):
    path = []
    while comp_id:
        comp = comp_map.get(comp_id)
        if not comp:
            break
        path.append(comp.name)
        comp_id = comp.compartment_id
    return " / ".join(reversed(path))


# -------------------------------------------
# Get Latest Backup
# -------------------------------------------
def get_latest_backup(backups):
    if not backups:
        return "No Backup"
    latest = max(backups, key=lambda b: b.time_created)
    return latest.time_created.strftime("%Y-%m-%d %H:%M")


# -------------------------------------------
# Boot Volume Backup Info
# -------------------------------------------
def get_boot_volume_backup(block, boot_volume_id, compartment_id):
    try:
        backups = block.list_boot_volume_backups(
            compartment_id=compartment_id,
            boot_volume_id=boot_volume_id
        ).data
        return "Yes", get_latest_backup(backups)
    except:
        return "Yes", "No Permission"


# -------------------------------------------
# Block Volume Backup Info
# -------------------------------------------
def get_block_volume_backup(block, volume_id, compartment_id):
    try:
        backups = block.list_volume_backups(
            compartment_id=compartment_id,
            volume_id=volume_id
        ).data
        return "Yes", get_latest_backup(backups)
    except:
        return "Yes", "No Permission"


# -------------------------------------------
# Get All Compartments Recursively
# -------------------------------------------
def get_all_compartments(identity, tenancy_id):
    all_compartments = []
    result = oci.pagination.list_call_get_all_results(
        identity.list_compartments,
        tenancy_id,
        compartment_id_in_subtree=True
    )
    all_compartments.extend(result.data)
    return all_compartments


# -------------------------------------------
# Process Region
# -------------------------------------------
def process_region(region, config):
    print(f"\n===== REGION: {region} =====")

    config["region"] = region
    compute = oci.core.ComputeClient(config)
    network = oci.core.VirtualNetworkClient(config)
    block = oci.core.BlockstorageClient(config)
    identity = oci.identity.IdentityClient(config)

    tenancy_id = config["tenancy"]

    # Get all compartments
    compartments = get_all_compartments(identity, tenancy_id)
    comp_map = {c.id: c for c in compartments}

    # Add tenancy (root)
    #comp_map[tenancy_id] = identity.get_tenancy(tenancy_id).data
    comp_map[tenancy_id] = None

    # Build table
    table = PrettyTable()
    table.field_names = [
        "Instance",
        "Compartment Path",
        "BootVol Attached",
        "Boot Backup",
        "BlockVol Attached",
        "Block Backup"
    ]

    # Collect instances from ALL compartments
    all_instances = []

    for comp in compartments + [comp_map[tenancy_id]]:
        try:
            insts = compute.list_instances(
                compartment_id=comp.id
            ).data
            all_instances.extend(insts)
        except:
            continue

    # Process each instance
    for inst in all_instances:

        comp_path = build_compartment_path(inst.compartment_id, comp_map)

        # --- Boot Volume ---
        bvas = compute.list_boot_volume_attachments(
            availability_domain=inst.availability_domain,
            compartment_id=inst.compartment_id,
            instance_id=inst.id
        ).data

        if bvas:
            boot_attached = "Yes"
            bv = bvas[0]
            boot_backup_yesno, boot_backup_time = get_boot_volume_backup(
                block, bv.boot_volume_id, inst.compartment_id
            )
        else:
            boot_attached = "No"
            boot_backup_time = "N/A"

        # --- Block Volumes ---
        vas = compute.list_volume_attachments(
            availability_domain=inst.availability_domain,
            compartment_id=inst.compartment_id,
            instance_id=inst.id
        ).data

        if vas:
            block_attached = "Yes"
            va = vas[0]
            block_backup_yesno, block_backup_time = get_block_volume_backup(
                block, va.volume_id, inst.compartment_id
            )
        else:
            block_attached = "No"
            block_backup_time = "N/A"

        # Add row
        table.add_row([
            inst.display_name,
            comp_path,
            boot_attached,
            boot_backup_time,
            block_attached,
            block_backup_time
        ])

    print(table)


# -------------------------------------------
# Main
# -------------------------------------------
def main():
    config = oci.config.from_file("~/.oci/config", "DEFAULT")

    regions = ["us-ashburn-1", "us-phoenix-1"]

    for region in regions:
        process_region(region, config)


if __name__ == "__main__":
    main()
