$IPs = @(
    "192.168.1.10",
    "192.168.1.11",
    "192.168.1.12",
    "192.168.1.13",
    "192.168.1.14",
    "192.168.1.15",
    "192.168.1.16",
    "192.168.1.17",
    "192.168.1.18",
    "192.168.1.19"
)

$Port = 22
$Timeout = 5000   # 5 seconds in milliseconds

foreach ($ip in $IPs) {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $asyncResult = $tcpClient.BeginConnect($ip, $Port, $null, $null)

    if ($asyncResult.AsyncWaitHandle.WaitOne($Timeout, $false)) {
        try {
            $tcpClient.EndConnect($asyncResult)
            Write-Host "$ip : Port 22 OPEN"
        } catch {
            Write-Host "$ip : Port 22 CLOSED"
        }
    } else {
        Write-Host "$ip : Port 22 TIMEOUT (No response in 5 seconds)"
    }

    $tcpClient.Close()
}
