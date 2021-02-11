#!/bin/bash
# This script is based on a previous script found here:
# https://gist.github.com/neilstuartcraig/4b8f06a4d4374c379bc0f44923a11fa4
INSTALLDIR="$PWD"
BUILDROOT="/tmp/nginx-quiche"
USERNAME=$USER

if ! cat nginx.conf &> /dev/null
then
  echo "Install Failed: Please run from Install directory"
  exit
fi

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
  libpcre3-dev \
  curl \
  zlib1g-dev \
  libcurl4-openssl-dev \
  autoconf \
  libtool-bin \
  libnss3-tools
  
# make build root dir
mkdir -p $BUILDROOT
cd $BUILDROOT

# Get stuff
echo '-----Downloading source-----'

if ! command -v cargo &> /dev/null
then
	echo '----Installing Rust-----'
	curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -y
	source $HOME/.cargo/env
fi

if ! command -v go1.15.8 &> /dev/null
then
    echo '----Installing Go 1.15.8-----'
    echo 'export GOPATH=$HOME/go' >> ~/.bashrc 
    echo 'export PATH=${PATH}:${GOPATH}/bin' >> ~/.bashrc 
    source ~/.bashrc
    go get golang.org/dl/go1.15.8
    source ~/.bashrc
fi

curl -O https://nginx.org/download/nginx-1.16.1.tar.gz
tar xvzf nginx-1.16.1.tar.gz
git clone --recursive https://github.com/cloudflare/quiche
# Prep nginx
cd $BUILDROOT/nginx-1.16.1
patch -p01 < ../quiche/extras/nginx/nginx-1.16.patch

echo "----Configuring-------"

# Run the config with default options and append any additional options specified by the above section
./configure --with-debug \
            --with-http_ssl_module              	\
            --with-http_v2_module               	\
            --with-http_v3_module               	\
            --with-ipv6                             \
            --with-openssl=$BUILDROOT/quiche/deps/boringssl \
            --with-quiche=$BUILDROOT/quiche

# Build nginx
echo '-----Building and Installing------'
make
sudo make install

# Install libquiche
echo '-------Building and installing http3-curl'

cd $BUILDROOT/quiche
cargo build --release --features pkg-config-meta,qlog
mkdir deps/boringssl/src/lib
ln -vnf $(find target/release -name libcrypto.a -o -name libssl.a) deps/boringssl/src/lib/
cd $BUILDROOT
git clone https://github.com/curl/curl
cd $BUILDROOT/curl
./buildconf
./configure LDFLAGS="-Wl,-rpath,$PWD/../quiche/target/release" \
                        --with-ssl=$PWD/../quiche/deps/boringssl/src \
                        --with-quiche=$PWD/../quiche/target/release  \
                         --enable-alt-svc
make
sudo make install
sudo cp $BUILDROOT/quiche/target/release/libquiche.so /lib/

# Install server certificate
git clone https://github.com/FiloSottile/mkcert && cd mkcert
go1.15.8 build -ldflags "-X main.Version=$(git describe --tags)"
chmod +x mkcert
go1.15.8 install
./mkcert -install localhost
./mkcert -key-file /usr/local/nginx/conf/localhost-key.pem \
    -cert-file /usr/local/nginx/conf/localhost.pem \
    localhost

# Configure server
echo '---------Configuring Server--------'
sudo rm /usr/local/nginx/conf/nginx.conf
sudo cp "$INSTALLDIR/nginx.conf" /usr/local/nginx/conf/nginx.conf

# Add systemd service
echo '------Adding Service---------'

sudo bash -c 'cat >/lib/systemd/system/nginx.service' <<EOL
[Unit]
Description=NGINX with Quiche Support
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
sudo chown -R $USER /usr/local/nginx
exit
