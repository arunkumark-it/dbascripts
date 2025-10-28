#!/bin/bash
search_dir="/interfaces"
cutoff_days=365

find "$search_dir" -mindepth 1 -maxdepth 1 -type d | while read dir; do
  # Check if any files of the given type were modified in the last 365 days (recursively)
  recent_file=$(find "$dir" -type f -mtime -$cutoff_days | head -n 1)
  if [ -z "$recent_file" ]; then
    echo "$dir"
  fi
done
