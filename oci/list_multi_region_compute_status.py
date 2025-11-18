#!/usr/bin/env python3
import oci

# ---------------------------------------------------------
# Build compartment hierarchy map
# ---------------------------------------------------------
def get_compartment_hierarchy(identity, root_compartment_id):

    compartments = identity.list_compartments(
        root_compartment_id,
        compartment_id_in_subtree=True,
        access_level="ANY"
    ).data

    compartments = [c for c in compartments if c.lifecycle_state == "ACTIVE"]

    names = {c.id: c.name for c in compartments}
    parents = {c.id: c.compartment_id for c in compartments}

    names[root_compartment_id] = "root"

    hierarchy = {}

    for cid in names.keys():
        path = [names[cid]]
        parent = parents.get(cid)

        while parent and parent in names:
            path.append(names[parent])
            parent = parents.get(parent)

        hierarchy[cid] = " → ".join(reversed(path))

    return hierarchy


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():

    # Load config
    config = oci.config.from_file()
    tenancy_id = config["tenancy"]

    # Determine regions
    if "regions" in config:
        regions = [r.strip() for r in config["regions"].split(",")]
    else:
        regions = [config["region"]]

    print("\nRegions to scan:", regions, "\n")

    # Global identity client (region does not matter for compartments)
    identity = oci.identity.IdentityClient(config)

    print("Collecting compartment hierarchy...")
    hierarchy = get_compartment_hierarchy(identity, tenancy_id)

    # ---------------------------------------------------------
    # Print table header
    # ---------------------------------------------------------
    print("\nListing Compute Instances...\n")
    print(f"{'Compartment Path':40} | {'Instance Name':30} | {'Shape':25} | {'OCPUs':5} | {'Memory(GB)':10} | {'State':10} | Region")
    print("-" * 160)

    # ---------------------------------------------------------
    # Loop over regions
    # ---------------------------------------------------------
    for region in regions:
        print(f"\n--- Collecting region: {region} ---")

        # Clone config & update region
        region_cfg = dict(config)
        region_cfg["region"] = region

        compute = oci.core.ComputeClient(region_cfg)

        for comp_id, comp_path in hierarchy.items():

            try:
                instances = compute.list_instances(comp_id).data
            except Exception:
                continue

            for inst in instances:

                # Shape details
                ocpus = inst.shape_config.ocpus if inst.shape_config else ""
                memory = inst.shape_config.memory_in_gbs if inst.shape_config else ""

                print(f"{comp_path:40} | "
                      f"{inst.display_name:30} | "
                      f"{inst.shape:25} | "
                      f"{str(ocpus):5} | "
                      f"{str(memory):10} | "
                      f"{inst.lifecycle_state:10} | "
                      f"{region}")

    print("\nCompleted.\n")


if __name__ == "__main__":
    main()
