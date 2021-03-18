echo "What network device do you want to use?"
ip link list | grep -o " .*:"
echo ""
read device
echo $device

# Create new namespace netns0
sudo ip netns add netns0

# Create Virtual Ethernet Pair
sudo ip link add veth-default type veth peer name veth-netns0

# Move Endpoint to netns0
sudo ip link set veth-netns0 netns netns0

# Setup Virtual Devices
sudo ip link set veth-default up
sudo ip netns exec netns0 ip link set veth-netns0 up
sudo ip netns exec netns0 ip link set lo up

# Assign IP's to devices
sudo ip addr add 10.0.3.1/24 dev veth-default
sudo ip netns exec netns0 ip addr add 10.0.3.2/24 dev veth-netns0

# Enable IP Forwarding
sudo sysctl -w net.ipv4.ip_forward=1

# Setup IP Tables for forwarding
sudo iptables -A FORWARD -o $device -i veth-default -j ACCEPT
sudo iptables -A FORWARD -i $device -o veth-default -j ACCEPT
sudo iptables -t nat -A POSTROUTING -s 10.0.3.2/24 -o $device -j MASQUERADE

# Add default gateway to network namespace
sudo ip netns exec netns0 ip route add default via 10.0.3.1
