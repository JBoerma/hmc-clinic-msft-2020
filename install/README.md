# Install Guide

In this directory, an installer script is provided for both the official NGINX with QUIC support and the unofficial NGINX with QUICHE support for ease of use on Debian systems. Due to the use of `apt`, the scripts will not run on other distribution.

The installer scripts will automatically run the manual instructions listed below, and therefore are all that is needed to setup the server if no more configuration is required.

## Dependencies

Nginx and Quiche have a number of dependencies. These include:

- build-essential
- [cmake](https://cmake.org/)
- [git](https://git-scm.com/)
- [gnupg](https://gnupg.org/)
- [golang](https://golang.org/doc/install)
- [libpcre3-dev](https://www.pcre.org/)
- [curl](https://curl.haxx.se/)
- [zlib1g-dev](https://zlib.net/)
- [libcurl4-openssl-dev](https://curl.haxx.se/libcurl/)
- [autoconf](https://www.gnu.org/software/autoconf/)
- [libtool-bin](https://www.gnu.org/software/libtool/)
- [libnss3-tools](https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS)
- [Rust and Cargo](https://www.rust-lang.org/tools/install)
- [Mercurial](https://www.mercurial-scm.org/)

For non-Debian distributions, build-essential[^1] consists of:

- [libc6-dev (glibc)](https://www.gnu.org/software/libc/)
- [gcc](https://gcc.gnu.org/)
- [g++](https://gcc.gnu.org/)
- [make](https://www.gnu.org/software/make/)
- dpkg-dev
- hurd-dev

[^1]: We have only installed this using Ubuntu, so which aspects of build-essential are necessary are not known to us. It is likely that dpkg-dev is unnecessary for this installation.

To install these on a Debian system, you can use the command

```bash
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
```

Rust and Cargo can be installed with the following command:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

## NGINX Quic Preview

NGINX has a preview version ^[2] which includes HTTP/3 and QUIC support. 

First, clone the repository for BoringSSL:

```bash
git clone https://boringssl.googlesource.com/boringssl 
```

Make a build folder in the repository:

```bash
cd boringssl && mkdir build
```

From the build folder, run `cmake` and `make` to compile:

```bash
cd build && cmake .. && make
```

Then, setup a .openssl folder in the repository for NGINX to compile with:

```bash
# Exit build folder
cd ../..
mkdir -p "boringssl/.openssl/lib"
cd "boringssl/.openssl"
ln -s ../include include
# Create empty file to prevent build error
touch "include/openssl/ssl.h"
cd ..
cp "build/crypto/libcrypto.a" ".openssl/lib"
cp "build/ssl/libssl.a" ".openssl/lib"
```

Next, clone the repository for NGINX with QUIC support using mercurial:

```bash
hg clone -b quic https://hg.nginx.org/nginx-quic
```

Then configure Nginx:

```bash
cd nginx-quic
./auto/configure --with-debug --with-http_v3_module       \
                       --with-cc-opt="-I ../boringssl/include"   \
                       --with-ld-opt="-L ../boringssl/build/ssl  \
                                      -L ../boringssl/build/crypto" \
						--with-openssl="../boringssl"
```

From here, you can use `make` and `make install` to compile and install NGINX.

To enable HTTP/3 support, a basic configuration like this can be used:

```
events {
    worker_connections  1024;
}

http {
    server {
        # Enable QUIC and HTTP/3.
        listen 443 quic reuseport;

        # Enable HTTP/2 (optional).
        listen 443 ssl http2;

        ssl_certificate      localhost.pem;
        ssl_certificate_key  localhost-key.pem;

        # Enable all TLS versions (TLSv1.3 is required for QUIC).
        ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
        
        # Add Alt-Svc header to negotiate HTTP/3.
        add_header alt-svc 'h3-27=":443"; ma=86400, h3-28=":443"; ma=86400, h3-29=":443"; ma=86400';
    }
}
```

Note that the alt-svc may affect which clients will use HTTP/3, and supported `h3-x` versions may change along with the specification.

A local SSL certificate can be generated using [mkcert](https://github.com/FiloSottile/mkcert)

For ease of use, Nginx can be added as a service with the following command:

```bash
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
```



[^2]: https://quic.nginx.org/readme.html

## NGINX with Quiche Patch

Cloudflare provides a patch for NGINX^[3] which enables HTTP/3 support using their Quiche library. This patch only works with Nginx version 1.16.1 currently.

First, download and extract the source for Nginx 1.16.1:

```bash
curl -O https://nginx.org/download/nginx-1.16.1.tar.gz
tar xvzf nginx-1.16.1.tar.gz
```

Additionally, clone the repository for Quiche:

```bash
git clone --recursive https://github.com/cloudflare/quiche
```

Inside the Nginx directory, apply the patch for Quiche support:

```bash
patch -p01 < ../quiche/extras/nginx/nginx-1.16.patch
```

Then configure Nginx:

```bash
./configure --with-debug \
						--with-http_ssl_module              	\
						--with-http_v2_module               	\
						--with-http_v3_module               	\
						--with-openssl=../quiche/deps/boringssl \
						--with-quiche=../quiche
```

From here, you can use `make` and `make install` to compile and install Nginx.

To enable HTTP/3 support, a basic configuration like this can be used:

```
events {
    worker_connections  1024;
}

http {
    server {
        # Enable QUIC and HTTP/3.
        listen 443 quic reuseport;

        # Enable HTTP/2 (optional).
        listen 443 ssl http2;

        ssl_certificate      localhost.pem;
        ssl_certificate_key  localhost-key.pem;

        # Enable all TLS versions (TLSv1.3 is required for QUIC).
        ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
        
        # Add Alt-Svc header to negotiate HTTP/3.
        add_header alt-svc 'h3-27=":443"; ma=86400, h3-28=":443"; ma=86400, h3-29=":443"; ma=86400';
    }
}
```

Note that the alt-svc may affect which clients will use HTTP/3, and supported `h3-x` versions may change along with the specification.

A local SSL certificate can be generated using [mkcert](https://github.com/FiloSottile/mkcert)

For ease of use, Nginx can be added as a service with the following command:

```bash
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
```



[^3]: https://blog.cloudflare.com/experiment-with-http-3-using-nginx-and-quiche/



## Curl with Quiche HTTP/3 Support

Curl can be compiled with libquiche ^[4] to proved HTTP/3 support. In order to do this, clone the Quiche repository:

```bash
git clone --recursive https://github.com/cloudflare/quiche
```

Build a release version of Quiche:

```bash
cargo build --release --features pkg-config-meta,qlog
```

Add a link to libraries in BoringSSL(?):

```bash
mkdir deps/boringssl/src/lib
ln -vnf $(find target/release -name libcrypto.a -o -name libssl.a) deps/boringssl/src/lib/
```

Then, clone the Curl repository:

```bash
git clone https://github.com/curl/curl
```

Configure Curl:

```bash
./buildconf
./configure LDFLAGS="-Wl,-rpath,$PWD/../quiche/target/release" \
						--with-ssl=$PWD/../quiche/deps/boringssl/src \
						--with-quiche=$PWD/../quiche/target/release \
						--enable-alt-svc
```

Then, compile with `make`. The executable will be placed in the `src` folder.

[^4]: https://github.com/curl/curl/blob/master/docs/HTTP3.md

## Firefox

To use Firefox with HTTP/3 with the server, navigate to `about:config`, and then set

```
network.http.http3.enabled = false
```

## Chromium

To use Chromium with HTTP/3 with the server, download this script:

```
https://github.com/scheib/chromium-latest-linux/archive/master.zip
```

Then, run `update.sh` to download the latest version of Chromium. Navigate to the `latest` folder, and then run:

```
./chrome --enable-quic --origin-to-force-quic-on=localhost:443
```

