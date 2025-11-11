#!/bin/bash

# Get current time and 1 hour ago in RFC3339 format
end_time=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
start_time=$(date -u -d '24 hour ago' +"%Y-%m-%dT%H:%M:%S.000Z")

printf "\n\033[1;96m%-45s %-20s\033[0m\n" "Instance" "Avg CPU % (Last 24hrs)"
printf "\033[1;96m%-45s %-20s\033[0m\n" "---------------------------------------------" "--------------------"

# Get all instances
oci search resource structured-search \
  --query-text "query instance resources" \
  --output json | \
jq -r '.data.items[] | [."display-name", .identifier, ."compartment-id"] | @tsv' | \
while IFS=$'\t' read -r instance_name instance_id compartment_id; do

  # Query CPU utilization metrics
  avg_cpu=$(oci monitoring metric-data summarize-metrics-data \
    --compartment-id "$compartment_id" \
    --namespace "oci_computeagent" \
    --query-text "CpuUtilization[1m]{resourceId = \"$instance_id\"}.mean()" \
    --start-time "$start_time" \
    --end-time "$end_time" \
    --output json 2>/dev/null | \
    jq -r 'if .data and (.data | length > 0) and .data[0]["aggregated-datapoints"] and (.data[0]["aggregated-datapoints"] | length > 0) then [.data[0]["aggregated-datapoints"][].value] | add / length else null end')

  # Handle no data case
  if [ -z "$avg_cpu" ] || [ "$avg_cpu" = "null" ]; then
    avg_cpu="N/A"
  else
    avg_cpu=$(printf "%.2f%%" "$avg_cpu")
  fi

  printf "%-45s %-20s\n" "$instance_name" "$avg_cpu"
done

echo ""
