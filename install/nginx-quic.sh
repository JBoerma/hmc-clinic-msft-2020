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
  golang \
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
                    --with-openssl="$BUILDROOT/boringssl" \
                    --prefix="/usr/local/nginx-quic"
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
./mkcert -key-file /usr/local/nginx-quic/conf/localhost-key.pem \
    -cert-file /usr/local/nginx-quic/conf/localhost.pem \
    localhost

# Configure server
echo '---------Configuring Server--------'

sudo cp "$INSTALLDIR/nginx.conf" /usr/local/nginx-quic/conf/nginx.conf

# add payloads
sudo cp -r "$INSTALLDIR/payloads/" /usr/local/nginx-quic/

# Add systemd service
echo '------Adding Service---------'

sudo bash -c 'cat >/lib/systemd/system/nginx-quic.service' <<EOL
[Unit]
Description=NGINX with Quic Support
Documentation=http://nginx.org/en/docs/
After=network.target remote-fs.target nss-lookup.target
 
[Service]
Type=forking
PIDFile=/usr/local/nginx-quic/logs/nginx.pid
ExecStartPre=/usr/local/nginx-quic/sbin/nginx -t
ExecStart=/usr/local/nginx-quic/sbin/nginx
ExecReload=/usr/local/nginx-quic/sbin/nginx -s reload
ExecStop=/usr/local/nginx-quic/sbin/nginx -s stop
PrivateTmp=true
 
[Install]
WantedBy=multi-user.target
EOL

exit
echo '------Starting server-------'
# NOTE: The below fails on Docker containers but i *think* will work elsewhere
# Enable & start service
sudo systemctl enable nginx-quic.service
sudo systemctl start nginx-quic.service

# Finish script
sudo systemctl reload nginx-quic.service
sudo chown -R $USERNAME /usr/local/nginx-quic
exit
