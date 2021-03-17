import time, sys
import paramiko

SERVER_KEY = "MSFT_Clinic_Key.pem"
SERVER_IP = "20.64.240.88"  

CMD_CD_ROOT = "cd ~/hmc-clinic-msft-2020"


def execute_cmd_blocking(ssh: "SSHClient", cmd: str): 
    print(f"\t>\t{cmd}")
    _, stdout, stderr = ssh.exec_command(cmd)
    dat = ""
    dat_err = ""
    while not stderr.channel.exit_status_ready() or not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            dat = dat + str(stdout.channel.recv(1024))
        if stderr.channel.recv_ready():
            dat_err = dat + str(stderr.channel.recv(1024))
    
    lines = dat.splitlines()
    lines_err = dat_err.splitlines()
    for line in lines:
        print(f"\t\t{line}")
    for line in lines_err:
        print(f"\t\t{line}")


def execute_cmd(ssh: "SSHClient", cmd: str):
    print(f"\t>\t{cmd}")
    _, stdout, stderr = ssh.exec_command(cmd)


# thanks to https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python/57439663#57439663
def start_server_monitoring(exp_id: str, out: str) -> "SSHClient":
    key = paramiko.RSAKey.from_private_key_file(SERVER_KEY)
    while True: 
        print("Trying to connect to server...")
        try: 
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SERVER_IP, username="clinic", pkey=key, banner_timeout=200)
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
    cmd_start_monitor = f"python3 system_monitoring.py {exp_id} server {out}"
    execute_cmd(ssh, " && ".join([CMD_CD_ROOT, cmd_start_monitor]))
    print("successfully ran systemUtil on server")
    return ssh


# hopefully closing connection is sufficient to end process
def end_server_monitoring(ssh: "SSHClient"): 
    ssh.close()
