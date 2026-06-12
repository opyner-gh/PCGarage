#!/usr/bin/env bash
# PCGarage hardware detector (Linux). Prints a JSON object to stdout and writes a
# copy to pcgarage-detected.json beside the script. Warnings go to stderr. RAM
# speed/type and the board model need root via dmidecode; without it those stay
# blank.  Run:  bash detect-linux.sh   (or: sudo bash detect-linux.sh)
set -u
warn() { echo "PCGarage: $*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }
# Minimal JSON string escaper (covers backslash, quote, newline, tab).
esc() { printf '%s' "${1-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' \
        -e ':a;N;$!ba;s/\n/\\n/g;s/\t/\\t/g'; }
# Emit a JSON value: a bare number when the arg is an integer, else null.
num() { case "${1-}" in ''|*[!0-9]*) printf 'null';; *) printf '%s' "$1";; esac; }

# ---- CPU ----
cpu_model=""; cpu_cores=""; cpu_threads=""; cpu_base="null"; cpu_vendor=""
if have lscpu; then
  lscpu_out=$(lscpu)
  cpu_model=$(printf '%s\n' "$lscpu_out" | sed -n 's/^Model name:[[:space:]]*//p' | head -1)
  cps=$(printf '%s\n' "$lscpu_out" | sed -n 's/^Core(s) per socket:[[:space:]]*//p' | head -1)
  sockets=$(printf '%s\n' "$lscpu_out" | sed -n 's/^Socket(s):[[:space:]]*//p' | head -1)
  if [ -n "${cps:-}" ] && [ -n "${sockets:-}" ]; then cpu_cores=$((cps * sockets)); fi
  cpu_threads=$(nproc 2>/dev/null)
  maxmhz=$(printf '%s\n' "$lscpu_out" | sed -n 's/^CPU max MHz:[[:space:]]*//p' | head -1)
  if [ -n "${maxmhz:-}" ]; then cpu_base=$(awk "BEGIN{printf \"%.2f\", $maxmhz/1000}"); fi
fi
case "$cpu_model" in *Intel*) cpu_vendor=Intel;; *AMD*) cpu_vendor=AMD;; esac

# ---- RAM ----
ram_gb=""; ram_speed=""; ram_type=""; ram_config=""
memkb=$(awk '/^MemTotal:/{print $2}' /proc/meminfo 2>/dev/null)
if [ -n "${memkb:-}" ]; then ram_gb=$(awk "BEGIN{printf \"%d\", ($memkb/1048576)+0.5}"); fi
if have dmidecode; then
  dmi=$(dmidecode -t memory 2>/dev/null)
  if [ -n "$dmi" ]; then
    ram_speed=$(printf '%s\n' "$dmi" | sed -n 's/^[[:space:]]*Speed:[[:space:]]*\([0-9]\{1,\}\).*/\1/p' | head -1)
    ram_type=$(printf '%s\n' "$dmi" | sed -n 's/^[[:space:]]*Type:[[:space:]]*\(DDR[0-9]\).*/\1/p' | head -1)
    mods=$(printf '%s\n' "$dmi" | grep -cE '^[[:space:]]*Size:[[:space:]]*[0-9]+ (M|G)B')
    if [ "${mods:-0}" -gt 1 ]; then ram_config="$mods modules"; fi
  else warn "dmidecode returned nothing; run with sudo for RAM speed/type"; fi
else warn "dmidecode not found; RAM speed/type left blank"; fi

# ---- GPU ----
gpu_model=""; gpu_vendor=""
if have lspci; then
  gpu_line=$(lspci 2>/dev/null | grep -iE 'vga compatible controller|3d controller' | head -1)
  # Strip the PCI address + class prefix up to the last ": " (greedy .* — a
  # leading "[^:]*" stops at the address colon and never matches).
  gpu_model=$(printf '%s' "$gpu_line" | sed 's/^.*: //')
  case "$gpu_line" in
    *NVIDIA*) gpu_vendor=NVIDIA;;
    *AMD*|*Radeon*|*"Advanced Micro"*) gpu_vendor=AMD;;
    *Intel*) gpu_vendor=Intel;;
  esac
else warn "lspci not found; GPU left blank"; fi

# ---- Storage (physical disks) ----
drives=""
if have lsblk; then
  while IFS= read -r line; do
    eval "$line"   # lsblk -P emits NAME="..." MODEL="..." SIZE="..." ROTA="..." TRAN="..."
    t="SATA SSD"; [ "${ROTA:-0}" = "1" ] && t="HDD"; [ "${TRAN:-}" = "nvme" ] && t="NVMe SSD"
    row=$(printf '{"manufacturer":"","model":"%s","type":"%s","capacity":"%s","form_factor":""}' \
          "$(esc "${MODEL:-}")" "$t" "$(esc "${SIZE:-}")")
    drives="${drives:+$drives,}$row"
  done < <(lsblk -dn -o NAME,MODEL,SIZE,ROTA,TRAN -P 2>/dev/null)
else warn "lsblk not found; storage left empty"; fi

# ---- Motherboard / OS / host ----
board=""
if have dmidecode; then board=$(dmidecode -s baseboard-product-name 2>/dev/null | head -1); fi
os_name=""
if [ -r /etc/os-release ]; then os_name=$(. /etc/os-release; printf '%s' "${PRETTY_NAME:-}"); fi
host=$(hostname 2>/dev/null)

json=$(cat <<EOF
{
  "computer_name": "$(esc "$host")",
  "os": "$(esc "$os_name")",
  "cpu": {"manufacturer": "$(esc "$cpu_vendor")", "model": "$(esc "$cpu_model")",
          "cores": $(num "$cpu_cores"), "threads": $(num "$cpu_threads"),
          "base_clock_ghz": ${cpu_base:-null}, "boost_clock_ghz": null, "cooler": ""},
  "ram": {"manufacturer": "", "capacity_gb": $(num "$ram_gb"),
          "speed_mhz": $(num "$ram_speed"), "type": "$(esc "$ram_type")",
          "configuration": "$(esc "$ram_config")"},
  "gpu": {"manufacturer": "$(esc "$gpu_vendor")", "model": "$(esc "$gpu_model")",
          "vram_gb": null, "brand": ""},
  "storage": [${drives}],
  "motherboard": {"model": "$(esc "$board")", "form_factor": ""},
  "psu": {"model": "", "wattage": null}
}
EOF
)
printf '%s\n' "$json"
dest="$(cd "$(dirname "$0")" && pwd)/pcgarage-detected.json"
printf '%s\n' "$json" > "$dest"
warn "detected specs also written to $dest"
