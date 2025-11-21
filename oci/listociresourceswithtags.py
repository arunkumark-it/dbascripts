import oci

def build_compartment_path(comp_id, comp_map):
    path = []
    while comp_id:
        comp = comp_map.get(comp_id)
        if not comp:
            break
        path.append(comp.name)
        comp_id = comp.compartment_id
    return " / ".join(reversed(path))


def print_table(headers, rows):
    col_widths = [len(h) for h in headers]

    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def format_row(row):
        return " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers)))

    print(format_row(headers))
    print("-" * (sum(col_widths) + 3 * (len(headers) - 1)))

    for row in rows:
        print(format_row(row))


def get_all_compartments(identity, tenancy_id):
    result = oci.pagination.list_call_get_all_results(
        identity.list_compartments,
        tenancy_id,
        compartment_id_in_subtree=True
    )
    return result.data


def process_region(region, config):
    print(f"\n===== REGION: {region} =====")

    config["region"] = region
    identity = oci.identity.IdentityClient(config)
    search_client = oci.resource_search.ResourceSearchClient(config)

    tenancy_id = config["tenancy"]

    compartments = get_all_compartments(identity, tenancy_id)
    comp_map = {c.id: c for c in compartments}
    comp_map[tenancy_id] = None

    search_details = oci.resource_search.models.StructuredSearchDetails(
        query="query all resources",
        type="Structured",
        matching_context_type="NONE"
    )

    try:
        response = oci.pagination.list_call_get_all_results(
            search_client.search_resources,
            search_details
        )
    except Exception as e:
        print(f"ERROR in region {region}: {e}")
        return

    rows = []

    for item in response.data:

        comp_path = build_compartment_path(item.compartment_id, comp_map)

        defined_tags = item.defined_tags or {}
        defined_list = []
        for ns, keys in defined_tags.items():
            for k, v in keys.items():
                defined_list.append(f"{ns}:{k}={v}")

        free_tags = item.freeform_tags or {}
        free_list = [f"{k}={v}" for k, v in free_tags.items()]

        rows.append([
            region,
            item.resource_type,
            item.display_name,
            comp_path,
            ", ".join(defined_list),
            ", ".join(free_list)
        ])

    print_table(
        ["Region", "Resource Type", "Name", "Compartment Path", "Defined Tags", "Freeform Tags"],
        rows
    )


def main():
    config = oci.config.from_file("~/.oci/config", "DEFAULT")

    regions = [
        "us-ashburn-1",
        "us-phoenix-1"
    ]

    for region in regions:
        process_region(region, config)


if __name__ == "__main__":
    main()
