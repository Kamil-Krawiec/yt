# Samba “tailshare” — minimal share (two easy paths)

Tiny Samba setup that shares one folder and, by default, binds SMB to Tailscale only. 
Which instruction to choose?
- Pick A if you purged Samba or your configs are missing
- Pick B for a clean fresh setup. <-- **I think you were better and didn't purge so i'd recommend this one!**
  
Not using tailscale? No problem, see below **Optional: Not using Tailscale?**

----

## A) After purge / configs missing
```bash
# REQUIRED: set your Linux user and share path
> USERNAME=${SUDO_USER:-$USER}
> SHARE=/srv/tailshare

# 1) Install/restore Samba packages (after purge)
> sudo apt update
> sudo apt --reinstall install -y samba smbclient samba-common samba-common-bin

# 2) Create the shared directory
> sudo mkdir -p "$SHARE"
> sudo chown "$USERNAME:$USERNAME" "$SHARE"

# 3) Minimal config (binds to Tailscale)
> sudo tee /etc/samba/smb.conf >/dev/null <<EOF
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

# 4) Start & enable Samba (recreates secrets after purge)
> sudo systemctl enable --now smbd

# If the next step complains about secrets.tdb, run once:
# sudo install -d -m0700 -o root -g root /var/lib/samba/private && sudo systemctl restart smbd

# 5) Set a Samba password for your Linux user
> sudo smbpasswd -a "$USERNAME"
```
--- 

## B) Fresh start (clean machine) - much easier and preffered

```bash
> USERNAME=${SUDO_USER:-$USER}
> SHARE=/srv/tailshare

# 1) Install packages
> sudo apt update
> sudo apt install -y samba smbclient

# 2) Create the shared directory
> sudo mkdir -p "$SHARE"
> sudo chown "$USERNAME:$USERNAME" "$SHARE"

# 3) Minimal config (binds to Tailscale)
> sudo tee /etc/samba/smb.conf >/dev/null <<EOF
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

# 4) Start & enable Samba
> sudo systemctl enable --now smbd

# 5) Set a Samba password for your Linux user
> sudo smbpasswd -a "$USERNAME"
```
---

## Validate config
```bash
testparm -s
```

## Optional: Tailscale-only firewall (UFW)

**Allow SMB on Tailscale, deny on default WAN interface**
```bash
> sudo ufw allow in on tailscale0 to any port 445 proto tcp
> WAN_IF=$(ip -o -4 route show to default | awk '{print $5; exit}')
> [ -n "$WAN_IF" ] && sudo ufw deny in on "$WAN_IF" to any port 445 proto tcp
```
## Optional: Not using Tailscale?

**Replace 'tailscale0' with your LAN interface (e.g., eth0)**
```bash
> sudo sed -i 's/tailscale0/eth0/g' /etc/samba/smb.conf
> sudo systemctl restart smbd
```

---

Connect from clients
	•	macOS (Finder → Go → Connect to Server): smb://<SERVER_IP>/tailshare [For mac it should be this](https://support.apple.com/lt-lt/guide/mac-help/mchlp1140/mac)
	•	Windows (Explorer → Map network drive): \\<SERVER_IP>\tailshare [Windows docs](https://support.microsoft.com/en-us/windows/file-sharing-over-a-network-in-windows-b58704b2-f53a-4b82-7bc1-80f9994725bf)
	•	Login: your Linux username (smbpasswd -a above) — on Windows you can use WORKGROUP\<user>
