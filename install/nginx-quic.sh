#!/bin/bash
# This script is based on a previous script found here:
# https://gist.github.com/neilstuartcraig/4b8f06a4d4374c379bc0f44923a11fa4
INSTALLDIR="$PWD"
BUILDROOT="/tmp/nginx-quic"
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
  libnss3-tools \
  mercurial
  
# make build root dir
mkdir -p $BUILDROOT
cd $BUILDROOT

# Get stuff
echo '-----Downloading source-----'

mkdir go
wget https://golang.org/dl/go1.15.3.linux-amd64.tar.gz -P $BUILDROOT/go
sudo tar -C /usr/local -xzf go/go1.15.3.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin

if ! command -v cargo &> /dev/null
then
	echo '----Installing Rust-----'
	curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
	source $HOME/.cargo/env
fi

# Build BoringSSL
git clone https://boringssl.googlesource.com/boringssl 
cd boringssl
mkdir build 
cd $BUILDROOT/boringssl/build
cmake ..
make

# Make an .openssl directory for nginx and then symlink BoringSSL's include directory tree
mkdir -p "$BUILDROOT/boringssl/.openssl/lib"
cd "$BUILDROOT/boringssl/.openssl"
ln -s ../include include

# Copy the BoringSSL crypto libraries to .openssl/lib so nginx can find them
cd "$BUILDROOT/boringssl"
cp "build/crypto/libcrypto.a" ".openssl/lib"
cp "build/ssl/libssl.a" ".openssl/lib"

# Prep nginx
mkdir -p "$BUILDROOT/nginx"
cd $BUILDROOT/nginx
hg clone -b quic https://hg.nginx.org/nginx-quic
cd "$BUILDROOT/nginx/nginx-quic"

# Run the config with default options and append any additional options specified by the above section
./auto/configure --with-http_ssl_module              	\
                    --with-http_v2_module               \
                    --with-http_v3_module               \
                    --with-ipv6                         \
                    --with-cc-opt="-I $BUILDROOT/boringssl/include"   \
                    --with-ld-opt="-L $BUILDROOT/boringssl/build/ssl  \
                                  -L $BUILDROOT/boringssl/build/crypto" \
                    --with-openssl="$BUILDROOT/boringssl"
# Fix "Error 127" during build
touch "$BUILDROOT/boringssl/.openssl/include/openssl/ssl.h"
make
sudo make install

# Install server certificate
cd "$BUILDROOT"
git clone https://github.com/FiloSottile/mkcert && cd mkcert
go build -ldflags "-X main.Version=$(git describe --tags)"
chmod +x mkcert
./mkcert -install localhost
./mkcert -key-file /usr/local/nginx/conf/localhost-key.pem \
    -cert-file /usr/local/nginx/conf/localhost.pem \
    localhost 127.0.0.1 example.com ::1

# Configure server
echo '---------Configuring Server--------'
sudo rm /usr/local/nginx/conf/nginx.conf
cp "$INSTALLDIR/nginx-quic.conf" /usr/local/nginx/conf/nginx.conf

# Add systemd service
echo '------Adding Service---------'

sudo bash -c 'cat >/lib/systemd/system/nginx.service' <<EOL
[Unit]
Description=NGINX with Quic Support
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
sudo chown -R $USERNAME /usr/local/nginx
exit
