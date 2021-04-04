shopt -s globstar
for pcap in results/**/*.pcap; do
    keys="${pcap%*.pcap}.keys"
    out="${pcap%*.pcap}.pcapng"
    echo $out;
    if !(test -f $out); then
        echo $out;
        editcap --inject-secrets tls,$keys $pcap $out
    fi
done
