curl -L https://www.python.org/ftp/python/3.9.1/Python-3.9.1.tgz --output python.tgz
tar -xf python.tgz
cd python
./configure --enable-optimizations
make -j 8
sudo make install
