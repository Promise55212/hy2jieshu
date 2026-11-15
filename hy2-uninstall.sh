#!/usr/bin/env bash
# Remove this HY2 manager only. Shared WireGuard, portbw and ACME are preserved.
set -Eeuo pipefail
umask 077
HY2_UNINSTALL_OVERRIDES=()

refuse() { echo "REFUSED: $*" >&2; return 1; }

check_command_owner() {
  local file="$1"
  [[ -e "$file" || -L "$file" ]] || return 0
  [[ ! -L "$file" && -f "$file" ]] \
    && grep -q '/usr/local/lib/hy2/' "$file" \
    || refuse "shared command has another or unknown owner: $file"
}

stop_unit() {
  local unit="$1" load state
  load="$(systemctl show "$unit" -p LoadState --value)" \
    || { refuse "cannot inspect unit: $unit"; return 1; }
  [[ "$load" != not-found ]] || return 0
  systemctl disable "$unit" >/dev/null 2>&1 || true
  # A synchronous successful stop is required before any protection is removed.
  systemctl stop "$unit" || { refuse "unit could not stop: $unit"; return 1; }
  state="$(systemctl show "$unit" -p ActiveState --value)" \
    || { refuse "cannot inspect stopped unit: $unit"; return 1; }
  [[ "$state" == inactive || "$state" == failed ]] \
    || refuse "unit is still running/stopping: $unit ($state)"
}

prepare_stop_override() {
  local unit="$1" root="${2:-/run/systemd/system}" path
  [[ "$unit" =~ ^hy2-temp-[A-Za-z0-9._-]+[.]service$ ]] \
    || { refuse "invalid temporary unit: $unit"; return 1; }
  path="$root/$unit.d/90-hy2-uninstall.conf"
  [[ ! -e "$path" && ! -L "$path" ]] \
    || { refuse "uninstall drop-in already exists: $path"; return 1; }
  install -d -m 755 "$root/$unit.d"
  # Bypass the entire stop hook, even for expired nodes, preserving all data.
  printf '[Service]\nExecStopPost=\n' >"$path"
  chmod 644 "$path"
}

cleanup_uninstall_overrides() {
  local path
  for path in "${HY2_UNINSTALL_OVERRIDES[@]}"; do
    rm -f -- "$path"
    rmdir "${path%/*}" 2>/dev/null || true
  done
  systemctl daemon-reload >/dev/null 2>&1 || true
}

remove_owned_tables() {
  local tables table
  tables="$(nft list tables)" || { refuse 'cannot inspect nftables'; return 1; }
  for table in hy2_pq hy2_iplimit hy2_daily_traffic hy2_manual_guard; do
    if grep -Fxq "table inet $table" <<<"$tables"; then
      nft delete table inet "$table" || return 1
    fi
  done
}

remove_node_bandwidth() {
  local port="$1" state_dir="${2:-/var/lib/portbw/ports}" cli="${3:-/usr/local/sbin/portbw}"
  [[ "$port" =~ ^[0-9]{1,5}$ ]] && (( 10#$port >= 1 && 10#$port <= 65535 )) \
    || { refuse "invalid managed bandwidth port: $port"; return 1; }
  [[ -e "$state_dir/$port.json" || -L "$state_dir/$port.json" ]] || return 0
  [[ -x "$cli" ]] && "$cli" del "$port" \
    || { refuse "cannot remove bandwidth policy for HY2 port $port; metadata retained"; return 1; }
}

backup_temp_unit() {
  local source="$1" store="${2:-/var/lib/hy2/uninstalled-units}" name tmp
  name="${source##*/}"
  [[ "$name" =~ ^hy2-temp-[A-Za-z0-9._-]+[.]service$ && ${#name} -le 104 ]] \
    || { refuse "invalid temporary unit backup: $name"; return 1; }
  [[ -f "$source" && ! -L "$source" && ! -L "$store" ]] \
    || { refuse "unsafe temporary unit backup path: $source"; return 1; }
  install -d -m 700 "$store" && chown root:root "$store" \
    || { refuse 'cannot secure temporary unit backup directory'; return 1; }
  tmp="$(mktemp "$store/.${name}.XXXXXX")" || return 1
  if ! install -m 600 "$source" "$tmp" || ! chown root:root "$tmp" \
    || ! mv -fT -- "$tmp" "$store/$name"; then
    rm -f -- "$tmp"
    refuse "temporary unit backup failed; unit retained: $name"
    return 1
  fi
}

retain_restore_tool() {
  [[ "$2" == 0 ]] || return 1
  case "$1" in
    /usr/local/sbin/hy2-guard|/etc/systemd/system/hy2-manual-guard.service|/usr/local/sbin/hy2_nat_preflight.sh)
      return 0 ;;
    *) return 1 ;;
  esac
}

main() {
  local apply=0 purge=0 core=0 arg file path name unit port key domain='' core_path=''
  local -a units=()
  for arg in "$@"; do
    case "$arg" in
      --yes) apply=1 ;;
      --purge) purge=1 ;;
      --remove-core) core=1 ;;
      -h|--help)
        echo 'Usage: bash hy2-uninstall.sh [--yes] [--purge] [--remove-core]'
        echo 'Default: preview. --yes removes services/tools, retains HY2 data, certificates and private temporary unit backups.'
        echo 'Retained guard CLI/disabled service restore saved firewall policies on reinstall.'
        echo 'Retained HY2 NAT preflight helper verifies WG protections before restored NAT nodes start.'
        echo '--purge deletes HY2 data/config/credentials; ACME account and ACME certificate copies remain.'
        echo '--remove-core deletes the known Hysteria binary used by hy2.service.'
        echo 'Preserves SSH, WireGuard/NAT, portbw, ACME accounts, packages and system tuning.'
        return 0 ;;
      *) echo "Unknown option: $arg" >&2; return 2 ;;
    esac
  done
  [[ $EUID -eq 0 ]] || { echo 'root required' >&2; return 1; }
  [[ -f /usr/local/lib/hy2/common.sh || -f /etc/default/hy2-main ]] || {
    echo 'No installed HY2 manager found; nothing removed.'; return 0;
  }
  shopt -s nullglob
  # Both projects historically use pq_* paths. Never touch another owner.
  for file in /usr/local/sbin/pq_*.sh /usr/local/sbin/ip_set.sh /usr/local/sbin/ip_del.sh /usr/local/sbin/iplimit_restore_all.sh; do
    check_command_owner "$file" || return 1
  done
  if [[ -f /var/lib/hy2/main/main.env ]]; then
    domain="$(sed -n 's/^HY_DOMAIN=//p' /var/lib/hy2/main/main.env | head -n1)"
  fi
  if (( core )); then
    core_path="$(sed -n 's|^ExecStart=\(/[^ ]*/hysteria\) server .*|\1|p' /etc/systemd/system/hy2.service 2>/dev/null | head -n1 || true)"
    case "$core_path" in
      /usr/local/bin/hysteria|/usr/bin/hysteria) ;;
      *) refuse 'cannot safely identify the installed HY2 core path'; return 1 ;;
    esac
    # A default upstream service is installed by get.hy2.sh but disabled by
    # this manager. Refuse core removal while any other service uses it.
    for path in /etc/systemd/system/*.service /usr/lib/systemd/system/*.service; do
      [[ "$path" == /etc/systemd/system/hy2.service || "${path##*/}" == hy2-temp-*.service ]] && continue
      if grep -qF "$core_path" "$path" 2>/dev/null; then
        if systemctl is-active --quiet "${path##*/}"; then
          refuse "core is used by active service: ${path##*/}"; return 1
        fi
      fi
    done
  fi
  echo "UNINSTALL_PLAN services/tools=remove data_purge=$purge core_remove=$core"
  echo 'Preserve: SSH, WireGuard/NAT, portbw, ACME accounts, packages and system tuning.'
  if (( ! apply )); then echo 'PREVIEW_ONLY: add --yes to execute'; return 0; fi
  install -d -m 755 /run/hy2
  exec 6>/run/hy2/bundle-install.lock
  flock -w 120 6 || { refuse 'HY2 install is running'; return 1; }
  exec 5>/run/hy2/main-install.lock
  flock -w 120 5 || { refuse 'HY2 main install is running'; return 1; }
  exec 4>/run/hy2/traffic-install.lock
  flock -w 120 4 || { refuse 'HY2 traffic install is running'; return 1; }
  # Stop producers first; shutdown collectors save while listeners still exist.
  for unit in hy2-managed-watchdog.timer hy2-gc.timer pq-save.timer pq-reset.timer hy2-traffic.timer \
              hy2-managed-watchdog.service hy2-gc.service pq-save.service pq-reset.service hy2-traffic.service \
              hy2-traffic-shutdown.service hy2-managed-shutdown-save.service; do
    stop_unit "$unit" || return 1
  done
  exec 7>/run/hy2/temp.lock
  flock -w 120 7 || { refuse 'HY2 node mutation is running'; return 1; }
  if [[ -f /var/lib/hy2/main/main.env ]]; then
    domain="$(sed -n 's/^HY_DOMAIN=//p' /var/lib/hy2/main/main.env | head -n1)"
  fi
  units=(/etc/systemd/system/hy2.service /etc/systemd/system/hy2-temp-*.service
         /etc/systemd/system/hy2-managed-*.service /etc/systemd/system/hy2-managed-*.timer
         /etc/systemd/system/hy2-gc.service /etc/systemd/system/hy2-gc.timer
         /etc/systemd/system/hy2-traffic*.service /etc/systemd/system/hy2-traffic.timer
         /etc/systemd/system/hy2-manual-guard.service
         /etc/systemd/system/pq-save.service /etc/systemd/system/pq-save.timer
         /etc/systemd/system/pq-reset.service /etc/systemd/system/pq-reset.timer)
  # EXIT removes only our exact temporary drop-ins, including on a stop error.
  trap cleanup_uninstall_overrides EXIT
  for path in "${units[@]}"; do
    [[ -f "$path" ]] || continue
    name="${path##*/}"
    if [[ "$name" == hy2-temp-*.service ]]; then
      prepare_stop_override "$name" || return 1
      HY2_UNINSTALL_OVERRIDES+=("/run/systemd/system/$name.d/90-hy2-uninstall.conf")
    fi
  done
  systemctl daemon-reload
  for path in "${units[@]}"; do
    [[ -f "$path" ]] || continue
    stop_unit "${path##*/}" || return 1
  done
  if (( ! purge )); then
    # Persist an explicit reinstall marker before removing unit definitions.
    # Metadata alone would otherwise look like a broken node to normal GC.
    for path in "${units[@]}"; do
      [[ -f "$path" && "${path##*/}" == hy2-temp-*.service ]] || continue
      backup_temp_unit "$path" || return 1
    done
  fi
  # Snapshot quota again with listeners stopped, closing the interval after
  # the shutdown-save unit's earlier collection.
  if [[ -x /usr/local/sbin/pq_save_state.sh ]]; then
    /usr/local/sbin/pq_save_state.sh || { refuse 'final quota save failed'; return 1; }
  fi
  # Serialize standalone quota/IP/guard/traffic commands before firewall teardown.
  exec 9>/run/hy2/quota.lock
  flock -w 30 9 || { refuse 'quota mutation is running'; return 1; }
  exec 8>/run/hy2/iplimit.lock
  flock -w 30 8 || { refuse 'IP-limit mutation is running'; return 1; }
  exec 10>/run/lock/hy2-manual-guard.lock
  flock -w 30 10 || { refuse 'manual guard mutation is running'; return 1; }
  exec 11>/run/hy2/traffic.lock
  flock -w 30 11 || { refuse 'traffic mutation is running'; return 1; }
  if (( purge )); then
    # Remove this project's port policies through the shared manager only;
    # preserve portbw software and every other port's policy. Non-purge keeps
    # these policies together with the node data for a later reinstall.
    for file in /var/lib/hy2/main/main.env /var/lib/hy2/temp/hy2-temp-*.env; do
      [[ -f "$file" ]] || continue
      key=PORT
      [[ "$file" == /var/lib/hy2/main/main.env ]] && key=MAIN_PORT
      port="$(sed -n "s/^${key}=//p" "$file" | head -n1)"
      remove_node_bandwidth "$port" || return 1
    done
  fi
  remove_owned_tables || return 1
  for path in "${units[@]}"; do
    if retain_restore_tool "$path" "$purge"; then continue; fi
    rm -f -- "$path"
  done
  for file in /usr/local/sbin/pq_*.sh /usr/local/sbin/ip_set.sh /usr/local/sbin/ip_del.sh /usr/local/sbin/iplimit_restore_all.sh; do
    [[ -f "$file" ]] || continue
    check_command_owner "$file" || return 1
    rm -f -- "$file"
  done
  for file in /usr/local/sbin/hy2_*.sh /usr/local/sbin/hy2_traffic /usr/local/sbin/hy2-guard /usr/local/sbin/hy2-abuse; do
    if retain_restore_tool "$file" "$purge"; then continue; fi
    [[ -f "$file" && ! -L "$file" ]] || continue
    grep -qi 'hy2' "$file" && rm -f -- "$file"
  done
  rm -f /root/onekey_hy2_main_tls.sh /root/hy2_temp_audit_all.sh /etc/tmpfiles.d/hy2.conf /etc/logrotate.d/hy2-managed
  rm -rf -- /usr/local/lib/hy2
  # acme.sh retains a reload command pointing here. Keep a harmless hook until
  # reinstall replaces it, so unrelated ACME renewals/accounts stay usable.
  install -d -m 755 /usr/local/lib/hy2
  printf '#!/usr/bin/env bash\n# HY2 manager uninstalled; certificate reload deferred until reinstall.\nexit 0\n' >/usr/local/lib/hy2/acme-reload.sh
  chmod 755 /usr/local/lib/hy2/acme-reload.sh
  if (( purge )); then
    rm -rf -- /var/lib/hy2 /var/log/hy2
    rm -f -- /etc/hysteria/temp/hy2-temp-*.yaml
    rmdir /etc/hysteria/temp 2>/dev/null || true
    # Certificate directory may hold certificates belonging to other tools.
    if [[ "$domain" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ && "$domain" != *..* ]]; then
      rm -f -- "/etc/hysteria/certs/$domain/privkey.pem" "/etc/hysteria/certs/$domain/fullchain.pem"
      rmdir -- "/etc/hysteria/certs/$domain" 2>/dev/null || true
    fi
    rm -f /etc/default/hy2-main /etc/hysteria/main.yaml /root/hy2_main_url.txt /root/hy2_main_subscription_base64.txt /root/hy2_temp_subscription.txt /root/hy2_temp_subscription_base64.txt
  fi
  if (( core )); then rm -f -- "$core_path"; fi
  systemctl daemon-reload
  echo 'UNINSTALL=PASS (WireGuard/NAT, portbw and ACME preserved)'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
