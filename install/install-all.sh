# Install servers
./caddy.sh
./nginx-quic.sh
./nginx-quiche.sh
sudo wget -O - http://rpms.litespeedtech.com/debian/enable_lst_debian_repo.sh | sudo bash
sudo apt install -y openlitespeed
sudo chown -R $USER /usr/local/lsws/conf
\cp -r lsws /usr/local/
# Install playwright
sudo apt install python3-pip iproute2
pip3 install -r requirements.txt
playwright install
# Configure firefox
folder=$(ls ~/.cache/ms-playwright/* -d | grep firefox | sort -r | head -n 1)
mkdir -p $folder/firefox/distribution
cp policies.json $folder/firefox/distribution/policies.json
# Download and install Edge
./edge.sh
