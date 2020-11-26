./caddy.sh
./nginx-quic.sh
./nginx-quiche.sh
sudo apt install python3-pip
pip3 install -r requirements.txt
folder=$(ls ~/.cache/ms-playwright/* -d | grep firefox | sort -r | head -n 1)
mkdir -p $folder/firefox/distribution
cp policies.json $folder/firefox/distribution/policies.json
