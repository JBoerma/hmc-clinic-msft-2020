echo "What network device do you want to use?"
ip link list | grep -o " .*:"
echo ""
read device
echo $device

# Create new namespace netns0
# This will be a virtual set of network
# interfaces separated from the systems
sudo ip netns add netns0

# Create Virtual Ethernet Pair
# This is a virtual ethernet where
# data can go into veth-default and
# then out of veth-netns0 or vice-versa
sudo ip link add veth-default type veth peer name veth-netns0

# Move Endpoint to netns0
# This moves one end of the virtual ethernet
# cable into the new network namespace
sudo ip link set veth-netns0 netns netns0

# Setup Virtual Devices
# This sets up the virtual ethernet
# devices to run, along with setting
# up the loopback device in the new namespace
sudo ip link set veth-default up
sudo ip netns exec netns0 ip link set veth-netns0 up
sudo ip netns exec netns0 ip link set lo up

# Assign IP's to devices
# This allows traffic to be sent
# to the devices using their IP addresses
sudo ip addr add 10.0.3.1/24 dev veth-default
sudo ip netns exec netns0 ip addr add 10.0.3.2/24 dev veth-netns0

# Enable IP Forwarding
# Allows network traffic to be forwarded
# from one IP on the system to another (?)
sudo sysctl -w net.ipv4.ip_forward=1

# Setup IP Tables for forwarding
# This tells the system to forward packets
# from the specified device to the virtual
# ethernet cable
sudo iptables -A FORWARD -o $device -i veth-default -j ACCEPT
sudo iptables -A FORWARD -i $device -o veth-default -j ACCEPT
sudo iptables -t nat -A POSTROUTING -s 10.0.3.2/24 -o $device -j MASQUERADE

# Add default gateway to network namespace
# This sets the virtual ethernet cable as the default
# gateway for network traffic in the new namespace.
sudo ip netns exec netns0 ip route add default via 10.0.3.1
