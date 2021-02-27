sudo apt install -y curl
echo "-------Downloading Caddy----------"
curl -L https://github.com/caddyserver/caddy/releases/download/v2.2.1/caddy_2.2.1_linux_amd64.tar.gz --output caddy.tar.gz -#
tar -xzf caddy.tar.gz caddy
mv caddy ../caddy
