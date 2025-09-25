# Samba “tailshare” — minimal share (two easy paths)

Tiny Samba setup that shares one folder and, by default, binds SMB to Tailscale only. 
Which instruction to choose?
- Pick A for a clean fresh setup. <-- **I think you were better and didn't purge so i'd recommend this one!**
- Pick B if you purged Samba or your configs are missing.

Not using tailscale? No problem, see below **Optional: Not using Tailscale?**

----

## A) Fresh start (clean machine) - much easier and preffered

### Nice to have: set your Linux user and share path, easier to reference furhter in the commands (NOT WHEN YOU EDIT FILE WITH NANO STEP3!). You can just write username and share path instead
```bash
 USERNAME=${SUDO_USER:-$USER}
 SHARE=/srv/tailshare
```

### 1) Install packages
```bash
 sudo apt update
 sudo apt install -y samba smbclient
```
smbclient is used for testing so its not 100% critical to downloand.

### 2) Create the shared directory
```bash
 sudo mkdir -p "$SHARE"
 sudo chown "$USERNAME:$USERNAME" "$SHARE"
```

### 3) Minimal config (binds to Tailscale)
Go to /etc/samba/smb.conf and open it in text editor (f.e nano), at the end of a file add this additional configuration

```text
[global]
   workgroup = WORKGROUP
   server role = standalone server
   map to guest = never
   disable netbios = yes
   smb ports = 445
   server min protocol = SMB2
```
optional configuration for tailscale only:
```text
[tailshare]
   path = $SHARE
   browseable = yes
   read only = no
   writable = yes
   force user = EDIT_USERNAME
   valid users = EDIT_USERNAME
   create mask = 0644
   directory mask = 0755
   interfaces = lo tailscale0
   bind interfaces only = yes
```

That makes smbd bind only to lo and tailscale0, so it won’t even listen on your WAN NIC. No listener ⇒ nothing to reach on WAN.

### 4) Start & enable Samba
```bash
 sudo systemctl enable --now smbd
```
### 5) Set a Samba password for your Linux user
```bash
 sudo smbpasswd -a "$USERNAME"
```

---

## B) After purge / configs missing

### Nice to have: set your Linux user and share path, easier to reference furhter in the commands (NOT WHEN YOU EDIT FILE WITH NANO STEP3!). You can just write username and share path instead
```bash
 USERNAME=${SUDO_USER:-$USER}
 SHARE=/srv/tailshare
```

### 1) Install/restore Samba packages (after purge)
```bash
 sudo apt update
 sudo apt --reinstall install -y samba smbclient samba-common samba-common-bin
```

### 2) Create the shared directory
```bash
 sudo mkdir -p "$SHARE"
 sudo chown "$USERNAME:$USERNAME" "$SHARE"
```
### 3) Minimal config (binds to Tailscale)
Go to /etc/samba/smb.conf and open it in text editor (f.e nano), at the end of a file add this additional configuration

```text
[global]
   workgroup = WORKGROUP
   server role = standalone server
   map to guest = never
   disable netbios = yes
   smb ports = 445
   server min protocol = SMB2
```
optional configuration for tailscale only:
```text
[tailshare]
   path = $SHARE
   browseable = yes
   read only = no
   writable = yes
   force user = EDIT_USERNAME
   valid users = EDIT_USERNAME
   create mask = 0644
   directory mask = 0755
   interfaces = lo tailscale0
   bind interfaces only = yes
```

### 4) Start & enable Samba (recreates secrets after purge)
```bash
 sudo systemctl enable --now smbd
```
#### If the next step complains about secrets.tdb, run once:
#### sudo install -d -m0700 -o root -g root /var/lib/samba/private && sudo systemctl restart smbd

### 5) Set a Samba password for your Linux user
```bash
 sudo smbpasswd -a "$USERNAME"
```
---

## Validate config
```bash
testparm -s
```

## Optional: Tailscale-only firewall (UFW)

**Allow SMB on Tailscale, deny on default WAN interface**
```bash
 sudo ufw allow in on tailscale0 to any port 445 proto tcp
 WAN_IF=$(ip -o -4 route show to default | awk '{print $5; exit}')
 [ -n "$WAN_IF" ] && sudo ufw deny in on "$WAN_IF" to any port 445 proto tcp
```

- Allow on tailscale0 – if UFW is enabled with “deny incoming” (the usual), this opens SMB only on the Tailscale interface, so clients can actually connect.
- Detect WAN_IF & deny – adds a hard block for TCP/445 on your default WAN interface (e.g., eth0/enp*s0). This is belt-and-suspenders protection in case your config changes later.

## Optional: Not using Tailscale?

**Replace 'tailscale0' with your LAN interface (e.g., eth0)**
```bash
 sudo sed -i 's/tailscale0/eth0/g' /etc/samba/smb.conf
 sudo systemctl restart smbd
```

---

Connect from clients
- macOS (Finder → Go → Connect to Server): smb://<SERVER_IP/tailshare [For mac it should be this](https://support.apple.com/lt-lt/guide/mac-help/mchlp1140/mac)
- Windows (Explorer → Map network drive): \\<SERVER_IP\tailshare [Windows docs](https://support.microsoft.com/en-us/windows/file-sharing-over-a-network-in-windows-b58704b2-f53a-4b82-7bc1-80f9994725bf)
- Login: your Linux username (smbpasswd -a above) — on Windows you can use WORKGROUP\<user
