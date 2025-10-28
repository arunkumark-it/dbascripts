# Get all rule OCIDs first
rule_ids=$(oci events rule list --compartment-id ocid1.<> --output json | jq -r '.data[].id')

# Loop through and get details for each rule
for rule_id in $rule_ids; do
  # Get the full JSON once
  rule_json=$(oci events rule get --rule-id $rule_id --output json)

  # Extract display name
  rule_name=$(echo "$rule_json" | jq -r '.data."display-name"')

  printf "\033[95mProcessing rule ID: %s | Rule Name: %s\033[0m\n" "$rule_id" "$rule_name"
  printf "\033[93mEvent Types:\033[0m\n"

  # Extract event types
  echo "$rule_json" | jq -r '.data.condition | fromjson | .eventType[] | "  - " + .'

  echo "---"
done
