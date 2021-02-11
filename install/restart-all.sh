cd ..
sudo systemctl daemon-reload
sudo systemctl restart nginx
sudo systemctl restart nginx-quic
sudo caddy stop
sudo caddy start
sudo /usr/local/lsws/bin/lswsctrl restart
