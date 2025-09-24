# Samba "tailshare" — minimal restore (works even after `apt purge samba`) XDD
# Context:
# - I had previously PURGED Samba (to show you on tutorial :p), so this script RESTORES missing bits (packages, config, secrets).
# - If you did NOT purge, you can simplify Step 1 (use plain `install` instead of `--reinstall`).
# - The share is bound to Tailscale only; adjust/remove those lines if you don’t use Tailscale.

# === REQUIRED: set your Linux username (used for SMB auth) and share path
USERNAME=${SUDO_USER:-$USER}
SHARE=/srv/tailshare

# --- 1) REQUIRED: install/restore Samba packages
sudo apt update
# If you did NOT purge: `sudo apt install -y samba smbclient` is enough.
sudo apt --reinstall install -y samba smbclient samba-common samba-common-bin

# --- 2) REQUIRED: create the directory to share
sudo mkdir -p "$SHARE"
sudo chown "$USERNAME:$USERNAME" "$SHARE"

# --- 3) REQUIRED: write a minimal /etc/samba/smb.conf
# Notes:
# - The share is restricted to Tailscale (`interfaces = lo tailscale0` + `bind interfaces only = yes`).
#   If you DON’T use Tailscale, either:
#     a) replace 'tailscale0' with your LAN interface (e.g. 'eth0'), or
#     b) delete both 'interfaces' and 'bind interfaces only' lines.
sudo tee /etc/samba/smb.conf >/dev/null <<EOF
[global]
   workgroup = WORKGROUP
   server role = standalone server
   map to guest = never
   disable netbios = yes
   smb ports = 445
   server min protocol = SMB2

[tailshare]
   path = $SHARE
   browseable = yes
   read only = no
   writable = yes
   force user = $USERNAME
   valid users = $USERNAME
   create mask = 0644
   directory mask = 0755
   interfaces = lo tailscale0
   bind interfaces only = yes
EOF

# --- 4) REQUIRED: start + enable smbd
# This also recreates /var/lib/samba/private/secrets.tdb after a purge.
sudo systemctl enable --now smbd

# --- 4.1) OPTIONAL fallback (only if the next step complains about 'secrets.tdb'):
# sudo install -d -m 0755 -o root -g root /var/lib/samba
# sudo install -d -m 0700 -o root -g root /var/lib/samba/private

# --- 5) REQUIRED: set a Samba password for your Linux user
# Use this same username when connecting from macOS/Windows.
sudo smbpasswd -a "$USERNAME"

# --- 6) OPTIONAL but recommended: lock SMB to Tailscale with UFW
# Skip if you don’t use UFW or don’t want firewall rules here.
# sudo ufw allow in on tailscale0 to any port 445 proto tcp
# WAN_IF=$(ip -o -4 route show to default | awk '{print $5; exit}')
# [ -n "$WAN_IF" ] && sudo ufw deny in on "$WAN_IF" to any port 445 proto tcp

# --- 7) OPTIONAL: quick sanity checks
testparm -s
echo "Shares on localhost:"
smbclient -L //localhost -U "$USERNAME" || true

echo
echo "Done. Connect from clients using:"
echo "macOS Finder: smb://<SERVER_IP>/tailshare"
echo "Windows Explorer: \\\\<SERVER_IP>\\tailshare"
echo "Login user: $USERNAME"