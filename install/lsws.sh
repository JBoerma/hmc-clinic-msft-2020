sudo wget -O - http://rpms.litespeedtech.com/debian/enable_lst_debian_repo.sh | sudo bash
sudo apt install -y openlitespeed
sudo chown -R $USER /usr/local/lsws/conf
\cp -r lsws /usr/local/
