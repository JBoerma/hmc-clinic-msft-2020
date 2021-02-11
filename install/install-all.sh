# Install servers
./caddy.sh
./nginx-quic.sh
./nginx-quiche.sh
./lsws.sh
# Install playwright
sudo apt install -y python3-pip iproute2 libdbus-glib-1-2
pip3 install -r requirements.txt
python3 -m playwright install
# Configure firefox
./firefox.sh
# Download and install Edge
./edge.sh
