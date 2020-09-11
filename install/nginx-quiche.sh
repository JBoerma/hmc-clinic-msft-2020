#!/bin/bash

BUILDROOT="/tmp/nginx-quiche"
USERNAME=$USER

# Pre-req
sudo apt-get update
sudo apt-get upgrade -y

# Install deps
echo '----Installing dependencies----'
sudo apt-get install -y \
  build-essential \
  cmake \
  git \
  gnupg \
  golang \
  libpcre3-dev \
  curl \
  zlib1g-dev \
  libcurl4-openssl-dev

# make build root dir
mkdir -p $BUILDROOT
cd $BUILDROOT

# Get stuff
echo '-----Downloading source-----'

if ! command -v cargo &> /dev/null
then
	echo '----Installing Rust-----'
	curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
	source $HOME/.cargo/env
fi

curl -O https://nginx.org/download/nginx-1.16.1.tar.gz
tar xvzf nginx-1.16.1.tar.gz
git clone --recursive https://github.com/cloudflare/quiche
# Prep nginx
cd $BUILDROOT/nginx-1.16.1
patch -p01 < ../quiche/extras/nginx/nginx-1.16.patch

echo "----Configuring-------"

# Run the config with default options and append any additional options specified by the above section
./configure --with-debug \--with-http_ssl_module              	\
						--with-http_v2_module               	\
						--with-http_v3_module               	\
						--with-openssl=$BUILDROOT/quiche/deps/boringssl \
						--with-quiche=$BUILDROOT/quiche

# Build nginx
echo '-----Building and Installing------'
make
sudo make install


# Add systemd service
echo '------Adding Service---------'

sudo bash -c 'cat >/lib/systemd/system/nginx.service' <<EOL
[Unit]
Description=NGINX with BoringSSL
Documentation=http://nginx.org/en/docs/
After=network.target remote-fs.target nss-lookup.target
 
[Service]
Type=forking
PIDFile=/usr/local/nginx/logs/nginx.pid
ExecStartPre=/usr/local/nginx/sbin/nginx -t
ExecStart=/usr/local/nginx/sbin/nginx
ExecReload=/usr/local/nginx/sbin/nginx -s reload
ExecStop=/usr/local/nginx/sbin/nginx -s stop
PrivateTmp=true
 
[Install]
WantedBy=multi-user.target
EOL

exit
echo '------Starting server-------'
# NOTE: The below fails on Docker containers but i *think* will work elsewhere
# Enable & start service
sudo systemctl enable nginx.service
sudo systemctl start nginx.service

# Finish script
sudo systemctl reload nginx.service
sudo chown -R /usr/local/nginx
exit
