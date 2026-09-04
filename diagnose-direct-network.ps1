[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outputPath = Join-Path $PSScriptRoot "direct-network-diagnostic-$stamp.txt"

if (Get-Process -Name 'v2rayN', 'xray', 'sing-box' -ErrorAction SilentlyContinue) {
    Write-Host 'v2rayN/core is still running. Exit it from the tray, then run this script again.' -ForegroundColor Yellow
    exit 2
}

Start-Transcript -LiteralPath $outputPath -Force | Out-Null
try {
    "Captured: $(Get-Date -Format o)"

    '=== Adapters ==='
    Get-NetAdapter -IncludeHidden |
        Where-Object { $_.Status -eq 'Up' -or $_.Name -match 'tun|xray|wintun' } |
        Select-Object Name, InterfaceDescription, Status, ifIndex |
        Format-Table -AutoSize

    '=== IP and DNS ==='
    Get-NetIPConfiguration |
        Where-Object { $_.NetAdapter.Status -eq 'Up' } |
        Select-Object InterfaceAlias, InterfaceIndex,
            @{n='IPv4';e={$_.IPv4Address.IPAddress -join ','}},
            @{n='Gateway';e={$_.IPv4DefaultGateway.NextHop -join ','}},
            @{n='DNS';e={$_.DNSServer.ServerAddresses -join ','}} |
        Format-Table -AutoSize

    '=== Default routes ==='
    Get-NetRoute -ErrorAction SilentlyContinue |
        Where-Object { $_.DestinationPrefix -in @('0.0.0.0/0', '::/0') } |
        Select-Object AddressFamily, InterfaceAlias, NextHop, RouteMetric, State |
        Format-Table -AutoSize

    '=== Proxy ==='
    Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' |
        Select-Object ProxyEnable, ProxyServer, AutoConfigURL |
        Format-List
    netsh winhttp show proxy

    '=== DNS tests ==='
    foreach ($server in @('192.168.5.1', '223.5.5.5', '1.1.1.1')) {
        try {
            $timer = [Diagnostics.Stopwatch]::StartNew()
            $answer = Resolve-DnsName 'www.baidu.com' -Server $server -Type A -DnsOnly -ErrorAction Stop |
                Where-Object IPAddress |
                Select-Object -First 1
            $timer.Stop()
            "DNS $server OK address=$($answer.IPAddress) time=$($timer.ElapsedMilliseconds)ms"
        }
        catch {
            "DNS $server FAILED: $($_.Exception.Message)"
        }
    }

    '=== Direct HTTP/HTTPS tests ==='
    foreach ($url in @(
        'http://connectivitycheck.gstatic.com/generate_204',
        'https://www.baidu.com',
        'https://www.bilibili.com',
        'https://www.qq.com',
        'https://www.microsoft.com'
    )) {
        $curlResult = & curl.exe --noproxy '*' -L --max-time 15 -sS -o NUL `
            -w "$url status=%{http_code} dns=%{time_namelookup}s connect=%{time_connect}s tls=%{time_appconnect}s remote=%{remote_ip} error=%{errormsg}`n" `
            $url 2>&1
        "CURL: $(($curlResult | Out-String).Trim())"
    }

    '=== Ping gateway ==='
    $pingResult = ping.exe -n 4 192.168.5.1 2>&1
    ($pingResult | Out-String).Trim()
}
finally {
    Stop-Transcript | Out-Null
}

Write-Host "Saved diagnostic report: $outputPath" -ForegroundColor Green
