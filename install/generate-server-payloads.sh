#!/bin/bash
# creating complex files
SERVERDIR="/usr/local/payloads"
sudo mkdir -p $SERVERDIR/assets
# Permissions will be reset below
sudo chmod 777 $SERVERDIR

# creating local image references for html files
for i in {400..499}
do
sudo wget https://via.placeholder.com/${i}/${i} -O $SERVERDIR/assets/placeholder_${i}.png
sudo wget https://placekitten.com/${i}/${i} -O $SERVERDIR/assets/cats_${i}.jpg
done

for i in {400..419}
do
echo "<img  src='https://placekitten.com/${i}/${i}' width='${i}' height='${i}' alt=''>"
done > $SERVERDIR/small.html

for i in {400..449}
do
echo "<img  src='https://placekitten.com/${i}/${i}' height='${i}' alt=''>"
done > $SERVERDIR/medium.html

for i in {400..499}
do
echo "<img  src='https://placekitten.com/${i}/${i}' height='${i}' alt=''>"
done > $SERVERDIR/large.html

for i in {400..499}
do
echo "<img  src='https://placekitten.com/${i}/${i}' width='${i}' height='${i}' alt=''>"
done > $SERVERDIR/cats_remote.html

for i in {400..499}
do
echo "<img  src='https://via.placeholder.com/${i}/${i}' width='${i}' height='${i}' alt=''>"
done > $SERVERDIR/placeholder_remote.html

for i in {400..499}
do
echo "<img  src='assets/placeholder_${i}.png' width='${i}' height='${i}' alt=''>"
done > $SERVERDIR/placeholder_local.html

# Add small/medium/large payloads
for i in {400..428}
do 
echo "<img src='assets/cats_${i}.jpg' width='${i}' height='${i}' alt=''>"
done > $SERVERDIR/small.html

for i in {400..453}
do 
echo "<img src='assets/cats_${i}.jpg' width='${i}' height='${i}' alt=''>"
done > $SERVERDIR/medium.html

for i in {430..499}
do 
echo "<img src='assets/cats_${i}.jpg' width='${i}' height='${i}' alt=''>"
done > $SERVERDIR/large.html

# creating files of random strings of certain size
< /dev/urandom tr -dc "[:alnum:]" | head -c1000 > $SERVERDIR/1kb.html
< /dev/urandom tr -dc "[:alnum:]" | head -c5000 > $SERVERDIR/5kb.html
< /dev/urandom tr -dc "[:alnum:]" | head -c10000 > $SERVERDIR/10kb.html
< /dev/urandom tr -dc "[:alnum:]" | head -c50000 > $SERVERDIR/50kb.html
< /dev/urandom tr -dc "[:alnum:]" | head -c100000 > $SERVERDIR/100kb.html
< /dev/urandom tr -dc "[:alnum:]" | head -c500000 > $SERVERDIR/500kb.html
< /dev/urandom tr -dc "[:alnum:]" | head -c1000000 > $SERVERDIR/1mb.html
< /dev/urandom tr -dc "[:alnum:]" | head -c5000000 > $SERVERDIR/5mb.html

# Reset permissions
sudo chmod 755 $SERVERDIR

exit
