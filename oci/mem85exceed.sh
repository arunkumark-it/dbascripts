#!/bin/bash

# Get current time and 24 hours ago in RFC3339 format
end_time=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
start_time=$(date -u -d '1 day ago' +"%Y-%m-%dT%H:%M:%S.000Z")

printf "\n\033[1;96m%-45s %-20s\033[0m\n" "Instance" "Avg Memory % (Last 24hr)"
printf "\033[1;96m%-45s %-20s\033[0m\n" "---------------------------------------------" "--------------------"

# Get all instances
oci search resource structured-search \
  --query-text "query instance resources" \
  --output json | \
jq -r '.data.items[] | [."display-name", .identifier, ."compartment-id"] | @tsv' | \
while IFS=$'\t' read -r instance_name instance_id compartment_id; do

  # Query Memory utilization metrics
  avg_memory=$(oci monitoring metric-data summarize-metrics-data \
    --compartment-id "$compartment_id" \
    --namespace "oci_computeagent" \
    --query-text "MemoryUtilization[1m]{resourceId = \"$instance_id\"}.mean()" \
    --start-time "$start_time" \
    --end-time "$end_time" \
    --output json 2>/dev/null | \
    jq -r 'if .data and (.data | length > 0) and .data[0]["aggregated-datapoints"] and (.data[0]["aggregated-datapoints"] | length > 0) then [.data[0]["aggregated-datapoints"][].value] | add / length else null end')

  # Handle no data case and filter for > 85%
  if [ -n "$avg_memory" ] && [ "$avg_memory" != "null" ]; then
    # Check if Memory is greater than 85
    if (( $(echo "$avg_memory > 85" | bc -l) )); then
      avg_memory_formatted=$(printf "%.2f%%" "$avg_memory")
      printf "%-45s %-20s\n" "$instance_name" "$avg_memory_formatted"
    fi
  fi
done

echo ""
