import oci

def main():
    config = oci.config.from_file()
    network = oci.core.VirtualNetworkClient(config)

    compartment_id = "<tenancy OCID"

    vcns = network.list_vcns(compartment_id).data

    for vcn in vcns:
        print(f"\nVCN: {vcn.display_name}  ({vcn.id})")

        # list subnets: vcn_id must be passed as a keyword
        subnets = network.list_subnets(
            compartment_id=compartment_id,
            vcn_id=vcn.id
        ).data

        if not subnets:
            print("  No subnets found.")
            continue

        for subnet in subnets:
            print(f"  Subnet: {subnet.display_name}")
            print(f"    Subnet OCID : {subnet.id}")
            print(f"    CIDR Block  : {subnet.cidr_block}")
            print(f"    AD / Subnet : {subnet.availability_domain}")
            print("")

if __name__ == "__main__":
    main()
