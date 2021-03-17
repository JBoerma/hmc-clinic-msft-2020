import time, sys
import paramiko

SERVER_KEY = "MSFT_Clinic_Key.pem"
SERVER_IP = "20.64.240.88"  

CMD_CD_ROOT = "cd ~/hmc-clinic-msft-2020"


def execute_cmd_blocking(ssh: "SSHClient", cmd: str): 
    print(f"\t>\t{cmd}")
    _, stdout, stderr = ssh.exec_command(cmd)
    dat = ""
    while not stderr.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            dat = dat + stdout.channel.recv(1024)
    
    lines = dat.splitlines()
    for line in lines: 
        print(f"\t{line}")


# thanks to https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python/57439663#57439663
def start_server_monitoring(exp_id: str, out: str) -> "SSHClient":
    key = paramiko.RSAKey.from_private_key_file(SERVER_KEY)
    while True: 
        try: 
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SERVER_IP, username="clinic", pkey=key)
        except paramiko.AuthenticationException as e:
            print("Auth failed when connection to Server:")
            print(e)
            return # Default is to silently fail
        except Exception as e: 
            print("Unexpected exception")
            print(e)
            sys.exit(1)
                    
    execute_cmd_blocking(ssh, CMD_CD_ROOT)

    ## TODO - Test
    cmd_start_monitor = f"python3 system_monitoring.py {exp_id} server {out}"
    ssh.exec_command(cmd_start_monitor)

    return ssh


# hopefully closing connection is sufficient to end process
def end_server_monitoring(ssh: "SSHClient"): 
    ssh.close()
