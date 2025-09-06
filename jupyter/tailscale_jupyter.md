# 1) Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 2) SSH only via Tailscale (recommended)
sudo ufw allow in on tailscale0 to any port 22 proto tcp
sudo ufw deny  in on enp1s0     to any port 22 proto tcp

# 3) Jupyter only via Tailscale (port 8888)
sudo ufw allow in on tailscale0 to any port 8888 proto tcp
sudo ufw deny  in on enp1s0     to any port 8888 proto tcp

# 4) (optional) AdGuard panel only via Tailscale (port 3000)
sudo ufw allow in on tailscale0 to any port 3000 proto tcp
sudo ufw deny  in on enp1s0     to any port 3000 proto tcp

# 5) Enable UFW and verify
sudo ufw enable
sudo ufw status numbered

# 6) Prevent Docker from bypassing UFW for Jupyter
sudo iptables -I DOCKER-USER -i enp1s0 -p tcp --dport 8888 -j DROP


1) Set strict defaults: block all inbound traffic, allow outbound.

2-3) Allow SSH (22) and Jupyter (8888) only via the Tailscale interface tailscale0, and deny them on Ethernet enp1s0.
   
4) (Optional) Do the same for the AdGuard web UI on port 3000.
5) Enable the firewall and list rules to verify order and matches.
6) Add a DOCKER-USER rule so Docker containers can’t expose 8888 over enp1s0 and bypass UFW.
