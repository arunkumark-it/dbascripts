#!/usr/bin/env python3
import oci

TENANCY_OCID = "<tenancy OCID"

def build_tree(compartments):
    """
    Build a parent-child tree from compartment list.
    """
    tree = {}
    for comp in compartments:
        parent = comp.compartment_id
        tree.setdefault(parent, []).append(comp)
    return tree


def print_tree(tree, parent_id, level=0):
    """
    Recursively print compartment hierarchy.
    """
    children = tree.get(parent_id, [])

    for comp in sorted(children, key=lambda x: x.name.lower()):
        indent = "    " * level
        print(f"{indent}- {comp.name} ({comp.id})")
        if comp.description:
            print(f"{indent}    Description: {comp.description}")
        print()

        # Recurse for sub-compartments
        print_tree(tree, comp.id, level + 1)


def main():
    config = oci.config.from_file()  # Default ~/.oci/config
    identity = oci.identity.IdentityClient(config)

    print("\nCollecting compartments... Please wait...\n")

    # Fetch all compartments including sub-compartments
    response = identity.list_compartments(
        TENANCY_OCID,
        compartment_id_in_subtree=True,
        lifecycle_state="ACTIVE"
    )

    compartments = response.data

    # Include the root compartment explicitly
    root_comp = identity.get_compartment(TENANCY_OCID).data
    compartments.append(root_comp)

    # Build tree structure
    tree = build_tree(compartments)

    print("COMPARTMENT HIERARCHY")
    print("======================\n")

    print(f"- root ({TENANCY_OCID})\n")
    print_tree(tree, TENANCY_OCID)


if __name__ == "__main__":
    main()
