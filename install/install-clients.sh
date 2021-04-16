# Install Deps 
sudo apt install -y iproute2 \
                    libdbus-glib-1-2 \
                    libnss3-tools \
                    golang \
		    libdbus-glib-1-2

# Need Python 3.9.1 for Playwright
echo '----Installing Python 3.9.1----'
./python-install.sh
source ~/.bashrc # want the right version of python

echo '----Installing Python Requirements----'
pip3 install -r requirements.txt
python3 -m playwright install

echo '----Configuring Playwright Browsers----'
# Configure firefox
./firefox.sh
# Download and install Edge
./edge.sh

echo '----Installing MKCert----'
# Setup Go
if ! command -v go1.15.8 &> /dev/null
then
    echo '----Installing Go 1.15.8-----'
    echo 'export GOPATH=$HOME/go' >> ~/.bashrc 
    echo 'export PATH=${PATH}:${GOPATH}/bin' >> ~/.bashrc 
    source ~/.bashrc
    go get golang.org/dl/go1.15.8
    source ~/.bashrc
    go get go1.15.8
fi
# Create Certificates
# Install server certificate
git clone https://github.com/FiloSottile/mkcert && cd mkcert
go1.15.8 build -ldflags "-X main.Version=$(git describe --tags)"
chmod +x mkcert
go1.15.8 install
mkcert -install
mkcert -key-file localhost-key.pem \
    -cert-file localhost.pem \
    localhost
echo "Create certificates for a different domain if not testing on localhost"
