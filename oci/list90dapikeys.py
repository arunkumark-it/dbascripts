import oci
from datetime import datetime, timedelta, timezone

def main():
    config = oci.config.from_file()
    identity = oci.identity.IdentityClient(config)

    cutoff_days = 90
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=cutoff_days)

    print("\nCollecting API keys older than 90 days...\n")
    header = f"{'USER_NAME':30} {'USER_OCID':60} {'FINGERPRINT':20} {'KEY_ID':35} {'TIME_CREATED'}"
    print(header)
    print("-" * len(header))

    # List all users
    users = oci.pagination.list_call_get_all_results(
        identity.list_users,
        config["tenancy"]
    ).data

    for user in users:
        user_name = user.name
        user_ocid = user.id

        # List API keys for each user
        try:
            api_keys = identity.list_api_keys(user_ocid).data
        except:
            continue  # Not authorized for this user

        for key in api_keys:
            time_created = key.time_created

            # Filter keys older than 90 days
            if time_created < cutoff_date:
                fingerprint = key.fingerprint
                key_id = key.key_id  # Always present

                print(f"{user_name:30} {user_ocid:60} {fingerprint:20} {key_id:35} {time_created}")

if __name__ == "__main__":
    main()
