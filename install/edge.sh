installer=$(curl https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-dev/ | grep -o \>m.*\.deb | grep -o m.* | sort -r | head -n 1)
curl -L https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-dev/$installer --output edge.deb
sudo dpkg --install edge.deb
