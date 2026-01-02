for pid in $(ls /proc | grep -E '^[0-9]+$'); do
  awk '/VmSwap/ {print $2 " KB\tPID=" pid}' pid=$pid /proc/$pid/status 2>/dev/null
done | sort -nr | head -20
