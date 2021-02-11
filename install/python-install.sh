sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev curl libsqlite3-dev libreadline-dev libffi-dev wget libbz2-dev
curl -L https://www.python.org/ftp/python/3.9.1/Python-3.9.1.tgz --output python.tgz
tar -xf python.tgz
folder=$(ls | grep P)
cd $folder
./configure --enable-optimizations
make -j8
sudo make -j8 install
