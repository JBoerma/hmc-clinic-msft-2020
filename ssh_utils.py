import time, sys, json
import paramiko
from os import path
from paramiko import SSHClient

SERVER_KEY = "MSFT_Clinic_Key.pem"
SERVER_IPS_FILENAME = "ips.json"
SERVER_IPS_EXAMPLE_FILENAME = "ips.example.json"

CMD_CD_ROOT = "cd ~/hmc-clinic-msft-2020"


def execute_cmd_blocking(ssh: SSHClient, cmd: str): 
    print(f"\t>\t{cmd}")
    # ssh.exec_command will only run ONE command, and it gives us 
    # stdin, stdout, and stderr to work with. We have no further input, 
    # so we just want to read everything from stdout and stderr.
    _, stdout, stderr = ssh.exec_command(cmd)
    dat = ""
    dat_err = ""
    # until both channels are done transmitting...
    while not stderr.channel.exit_status_ready() or not stdout.channel.exit_status_ready():
        # check each channel to see if any bytes are ready to be received
        # and receive at most 1024 at a time.
        if stdout.channel.recv_ready():
            dat = dat + str(stdout.channel.recv(1024))
        if stderr.channel.recv_ready():
            dat_err = dat + str(stderr.channel.recv(1024))
    
    # split the received data by newlines, and print.
    lines = dat.splitlines()
    lines_err = dat_err.splitlines()
    for line in lines:
        print(f"\t\t{line}")
    for line in lines_err:
        print(f"\t\t{line}")


# This mutates ssh, so later down the line we can recover the 
# channels later if we want.
def execute_cmd(ssh: SSHClient, cmd: str):
    print(f"\t>\t{cmd}")
    # ignoring stdout, stderr from this. Polling every so often would 
    # perhaps be too complex. Maybe we can get all of stdout,stderr in 
    # end_server_monitoring?
    _, _, _ = ssh.exec_command(cmd)


# thanks to https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python/57439663#57439663
def start_server_monitoring(exp_id: str, out: str) -> SSHClient:
    key = paramiko.RSAKey.from_private_key_file(SERVER_KEY)
    while True:  # keep trying until things work or everything breaks
        print("Trying to connect to server...")
        try: 
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ip = get_server_ips_dict()["public_ip"]
            ssh.connect(ip, username="clinic", pkey=key, banner_timeout=200)
            break
        except paramiko.AuthenticationException as e:
            print("Auth failed when connecting to Server:")
            print(e)
            print("Trying again")
        except paramiko.ssh_exception.SSHException as e: 
            print("Encountered exception:")
            print(e) 
            print("Trying again...")
        except Exception as e: 
            print("Unexpected exception")
            print(e)
            sys.exit(1)
    
    print("Successful Connection: Running Commands")
    commands = [
        CMD_CD_ROOT,
        "cd install",
        "./restart-all.sh",
    ]
    execute_cmd_blocking(ssh, " && ".join(commands))

    ## TODO - Test
    cmd_start_monitor = f"python3 systemUtil.py {exp_id} server {out}"
    execute_cmd(ssh, " && ".join([CMD_CD_ROOT, cmd_start_monitor]))
    print("successfully ran systemUtil on server")
    return ssh


# hopefully closing connection is sufficient to end process
def end_server_monitoring(ssh: SSHClient): 
    ssh.close()


def get_server_ips_dict(): 
    name = SERVER_IPS_FILENAME
    if not path.exists(SERVER_IPS_FILENAME): 
        name = SERVER_IPS_EXAMPLE_FILENAME
    with open(name) as f: 
        return json.load(f)


def on_server(url: str) -> bool:
    server_ips = get_server_ips_dict()
    if url in [server_ips["public_ip"], server_ips["private_ip"]]:
        return True
    return False