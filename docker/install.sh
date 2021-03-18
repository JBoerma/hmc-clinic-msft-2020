sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo apt-key fingerprint 0EBFCD88

sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
   

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
docker pull webpagetest/server
docker pull webpagetest/agent
cd server
docker build -t local-wptserver .
cd ../agent
docker build -t local-wptagent .
