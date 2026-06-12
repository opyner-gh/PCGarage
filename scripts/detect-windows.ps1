#requires -Version 5.0
<#
  PCGarage hardware detector (Windows).
  Prints a JSON object describing this machine to stdout, and writes a copy to
  pcgarage-detected.json next to this script. Progress/warnings go to stderr so
  stdout stays clean JSON you can paste straight into PCGarage's Detect page.

  Run from PowerShell:
    powershell -ExecutionPolicy Bypass -File .\detect-windows.ps1
#>
$ErrorActionPreference = 'SilentlyContinue'

function ConvertTo-GB([double]$bytes) { [int][math]::Round($bytes / 1GB) }

# ---- CPU ----
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cpuManufacturer = ''
if ($cpu.Manufacturer -match 'Intel')                  { $cpuManufacturer = 'Intel' }
elseif ($cpu.Manufacturer -match 'AMD|Advanced Micro') { $cpuManufacturer = 'AMD' }
$baseClockGhz = $null
if ($cpu.MaxClockSpeed) { $baseClockGhz = [math]::Round($cpu.MaxClockSpeed / 1000.0, 2) }

# ---- RAM ----
$mem = @(Get-CimInstance Win32_PhysicalMemory)
$capacityGb = $null; $speedMhz = $null; $ramType = ''; $ramConfig = ''
if ($mem.Count -gt 0) {
    $sum = ($mem | Measure-Object -Property Capacity -Sum).Sum
    if ($sum) { $capacityGb = ConvertTo-GB $sum }
    if ($mem[0].Speed) { $speedMhz = [int]$mem[0].Speed }
    # Only the DDR generations the RAM "type" select offers; anything else maps
    # to "" so the editor doesn't blank an out-of-vocabulary value on import.
    $ddr = @{ '20' = 'DDR3'; '21' = 'DDR3'; '24' = 'DDR3'; '26' = 'DDR4'; '34' = 'DDR5' }
    $ramType = [string]$ddr["$($mem[0].SMBIOSMemoryType)"]
    if ($mem.Count -gt 1) { $ramConfig = "$($mem.Count) modules" }
}

# ---- GPU (prefer a discrete adapter over an integrated one) ----
$gpus = @(Get-CimInstance Win32_VideoController)
$gpu = $gpus | Where-Object { $_.Name -match 'NVIDIA|GeForce|RTX|GTX|Quadro|Radeon|RX ' } | Select-Object -First 1
if (-not $gpu) { $gpu = $gpus | Select-Object -First 1 }
$gpuManufacturer = ''
if ($gpu.Name -match 'NVIDIA|GeForce|RTX|GTX|Quadro') { $gpuManufacturer = 'NVIDIA' }
elseif ($gpu.Name -match 'Radeon|AMD')                { $gpuManufacturer = 'AMD' }
elseif ($gpu.Name -match 'Intel')                     { $gpuManufacturer = 'Intel' }
# VRAM: AdapterRAM is a signed 32-bit value that lies for cards over 4 GB. Scan
# the display-class registry subkeys for the one whose DriverDesc matches the
# chosen GPU and read its 64-bit qwMemorySize; fall back to AdapterRAM.
$vramGb = $null
$classKey = 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}'
foreach ($sub in (Get-ChildItem -Path $classKey -ErrorAction SilentlyContinue)) {
    $props = Get-ItemProperty -Path $sub.PSPath -ErrorAction SilentlyContinue
    if ([string]$props.DriverDesc -eq [string]$gpu.Name) {
        $qw = $props.'HardwareInformation.qwMemorySize'
        if ($qw -gt 0) { $vramGb = ConvertTo-GB $qw }
        break
    }
}
if ($null -eq $vramGb -and $gpu.AdapterRAM -gt 0) { $vramGb = ConvertTo-GB $gpu.AdapterRAM }

# ---- Storage ----
$drives = @()
foreach ($disk in Get-CimInstance Win32_DiskDrive) {
    $type = ''
    if ($disk.MediaType -match 'Fixed hard disk') { $type = 'HDD' }
    if ($disk.Model -match 'NVMe' -or $disk.InterfaceType -match 'NVMe') { $type = 'NVMe SSD' }
    $capacity = ''
    if ($disk.Size) { $capacity = "$(ConvertTo-GB $disk.Size) GB" }
    $drives += [ordered]@{
        manufacturer = ''
        model        = [string]$disk.Model
        type         = $type
        capacity     = $capacity
        form_factor  = ''
    }
}

# ---- Motherboard / OS / host ----
$board  = Get-CimInstance Win32_BaseBoard | Select-Object -First 1
$os     = Get-CimInstance Win32_OperatingSystem
$osName = "$($os.Caption.Trim()) $($os.Version)".Trim()

$record = [ordered]@{
    computer_name = $env:COMPUTERNAME
    os            = $osName
    cpu = [ordered]@{
        manufacturer    = $cpuManufacturer
        model           = [string]$cpu.Name
        cores           = [int]$cpu.NumberOfCores
        threads         = [int]$cpu.NumberOfLogicalProcessors
        base_clock_ghz  = $baseClockGhz
        boost_clock_ghz = $null
        cooler          = ''
    }
    ram = [ordered]@{
        manufacturer  = ''
        capacity_gb   = $capacityGb
        speed_mhz     = $speedMhz
        type          = $ramType
        configuration = $ramConfig
    }
    gpu = [ordered]@{
        manufacturer = $gpuManufacturer
        model        = [string]$gpu.Name
        vram_gb      = $vramGb
        brand        = ''
    }
    storage = $drives
    motherboard = [ordered]@{ model = [string]$board.Product; form_factor = '' }
    psu         = [ordered]@{ model = ''; wattage = $null }
}

$json = $record | ConvertTo-Json -Depth 5
Write-Output $json

$dest = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'pcgarage-detected.json'
Set-Content -Path $dest -Value $json -Encoding UTF8
[Console]::Error.WriteLine("PCGarage: detected specs also written to $dest")
