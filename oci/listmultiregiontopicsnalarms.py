#!/usr/bin/env python3
import oci
from oci.pagination import list_call_get_all_results
from datetime import datetime


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
# Get alarms mapped to a topic
# ---------------------------------------------------------
def get_alarms_for_topic(monitoring, topic_id, compartments):
    alarms = []
    
    for comp_id in compartments:
        try:
            alarm_list = list_call_get_all_results(
                monitoring.list_alarms,
                comp_id
            ).data
            
            for alarm in alarm_list:
                if alarm.lifecycle_state == "ACTIVE":
                    # Check if this alarm uses the topic
                    destinations = alarm.destinations if alarm.destinations else []
                    if topic_id in destinations:
                        alarms.append(alarm.display_name)
        except:
            continue
    
    return alarms


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
# Region processing
# ---------------------------------------------------------
def process_region(region, config):
    print(f"\n=== REGION: {region} ===")

    reg_cfg = dict(config)
    reg_cfg["region"] = region

    identity = oci.identity.IdentityClient(reg_cfg)
    ons_control = oci.ons.NotificationControlPlaneClient(reg_cfg)
    ons_data = oci.ons.NotificationDataPlaneClient(reg_cfg)
    monitoring = oci.monitoring.MonitoringClient(reg_cfg)

    tenancy_id = reg_cfg["tenancy"]
    comp_paths = build_compartment_paths(identity, tenancy_id)
    
    # Get all compartment IDs for alarm lookup
    all_comp_ids = list(comp_paths.keys())

    rows = []

    for comp_id, comp_path in comp_paths.items():
        if not comp_path:
            continue

        try:
            topics = list_call_get_all_results(
                ons_control.list_topics,
                comp_id
            ).data
        except:
            continue

        for topic in topics:
            if topic.lifecycle_state != "ACTIVE":
                continue

            topic_name = topic.name
            topic_id = topic.topic_id
            topic_created = format_datetime(topic.time_created)
            topic_desc = topic.description if topic.description else ""

            # Get subscriptions for this topic
            subscriptions = []
            try:
                subs = list_call_get_all_results(
                    ons_data.list_subscriptions,
                    comp_id,
                    topic_id=topic_id
                ).data
                subscriptions = [s for s in subs if s.lifecycle_state in ["ACTIVE", "PENDING"]]
            except:
                pass

            # Get alarms mapped to this topic
            alarms = get_alarms_for_topic(monitoring, topic_id, all_comp_ids)
            alarm_names = ",".join(alarms) if alarms else "NONE"

            # If no subscriptions, still show topic with empty subscription fields
            if not subscriptions:
                rows.append([
                    region,
                    comp_path,
                    topic_name,
                    topic_id,
                    topic_created,
                    topic_desc,
                    "",  # subscription_endpoint
                    "",  # protocol
                    "",  # subscription_state
                    "",  # subscription_created
                    alarm_names
                ])
            else:
                # One row per subscription
                for sub in subscriptions:
                    endpoint = sub.endpoint if sub.endpoint else ""
                    protocol = sub.protocol if sub.protocol else ""
                    sub_state = sub.lifecycle_state if sub.lifecycle_state else ""
                    sub_created = format_datetime(sub.created_time)

                    rows.append([
                        region,
                        comp_path,
                        topic_name,
                        topic_id,
                        topic_created,
                        topic_desc,
                        endpoint,
                        protocol,
                        sub_state,
                        sub_created,
                        alarm_names
                    ])

    return rows


# ---------------------------------------------------------
# Table print
# ---------------------------------------------------------
def print_table(rows):
    headers = [
        "region",
        "compartment_path",
        "topic_name",
        "topic_id",
        "topic_created",
        "description",
        "subscription_endpoint",
        "protocol",
        "subscription_state",
        "subscription_created",
        "mapped_alarms"
    ]

    print("\n" + " | ".join(headers))
    print("-" * 250)

    for r in rows:
        print(" | ".join(str(x) for x in r))


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

    final = []
    for region in regions:
        final.extend(process_region(region, config))

    print_table(final)
    print(f"\n=== TOTAL RECORDS: {len(final)} ===")


if __name__ == "__main__":
    main()
