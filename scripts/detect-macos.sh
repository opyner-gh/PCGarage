#!/bin/bash
# PCGarage hardware detector (macOS). Prints a JSON object to stdout and writes a
# copy to pcgarage-detected.json beside the script. Warnings go to stderr.
# Run:  bash detect-macos.sh
set -u
warn() { echo "PCGarage: $*" >&2; }
esc()  { printf '%s' "${1-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' \
         -e ':a;N;$!ba;s/\n/\\n/g;s/\t/\\t/g'; }
num()  { case "${1-}" in ''|*[!0-9]*) printf 'null';; *) printf '%s' "$1";; esac; }

host=$(scutil --get ComputerName 2>/dev/null || hostname)
os_name="macOS $(sw_vers -productVersion 2>/dev/null)"

cpu_model=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
if [ -z "${cpu_model:-}" ]; then
  # Apple Silicon has no machdep.cpu.brand_string; read the chip name instead.
  cpu_model=$(system_profiler SPHardwareDataType 2>/dev/null \
              | sed -n 's/^[[:space:]]*Chip:[[:space:]]*//p' | head -1)
fi
cpu_cores=$(sysctl -n hw.physicalcpu 2>/dev/null)
cpu_threads=$(sysctl -n hw.logicalcpu 2>/dev/null)

mem_bytes=$(sysctl -n hw.memsize 2>/dev/null)
ram_gb=""
if [ -n "${mem_bytes:-}" ]; then ram_gb=$(awk "BEGIN{printf \"%d\", ($mem_bytes/1073741824)+0.5}"); fi

# GPU via system_profiler text (Chipset Model line).
gpu_model=$(system_profiler SPDisplaysDataType 2>/dev/null \
            | sed -n 's/^[[:space:]]*Chipset Model:[[:space:]]*//p' | head -1)
gpu_vendor=""
case "$gpu_model" in
  *Apple*) gpu_vendor=Apple;; *AMD*|*Radeon*) gpu_vendor=AMD;;
  *NVIDIA*) gpu_vendor=NVIDIA;; *Intel*) gpu_vendor=Intel;;
esac

# Storage: physical NVMe/SATA media, name + size.
drives=""
sp_storage=$(system_profiler SPNVMeDataType SPSerialATADataType 2>/dev/null)
while IFS= read -r model; do
  [ -n "$model" ] || continue
  row=$(printf '{"manufacturer":"","model":"%s","type":"NVMe SSD","capacity":"","form_factor":""}' "$(esc "$model")")
  drives="${drives:+$drives,}$row"
done < <(printf '%s\n' "$sp_storage" | sed -n 's/^[[:space:]]*Model:[[:space:]]*//p')

json=$(cat <<EOF
{
  "computer_name": "$(esc "$host")",
  "os": "$(esc "$os_name")",
  "cpu": {"manufacturer": "", "model": "$(esc "$cpu_model")",
          "cores": $(num "$cpu_cores"), "threads": $(num "$cpu_threads"),
          "base_clock_ghz": null, "boost_clock_ghz": null, "cooler": ""},
  "ram": {"manufacturer": "", "capacity_gb": $(num "$ram_gb"),
          "speed_mhz": null, "type": "", "configuration": ""},
  "gpu": {"manufacturer": "$(esc "$gpu_vendor")", "model": "$(esc "$gpu_model")",
          "vram_gb": null, "brand": ""},
  "storage": [${drives}],
  "motherboard": {"model": "", "form_factor": ""},
  "psu": {"model": "", "wattage": null}
}
EOF
)
printf '%s\n' "$json"
dest="$(cd "$(dirname "$0")" && pwd)/pcgarage-detected.json"
printf '%s\n' "$json" > "$dest"
warn "detected specs also written to $dest"
