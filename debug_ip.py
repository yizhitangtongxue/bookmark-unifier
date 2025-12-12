import socket
import ipaddress

domains = [
    "gitea.io",
    "cloud.tencent.com",
    "v2ex.com",
    "www.ventoy.net"
]

print(f"{'Domain':<25} | {'IP':<15} | {'is_private'}")
print("-" * 55)

for d in domains:
    try:
        ip = socket.gethostbyname(d)
        ip_obj = ipaddress.ip_address(ip)
        print(f"{d:<25} | {ip:<15} | {ip_obj.is_private}")
    except Exception as e:
        print(f"{d:<25} | {'ERROR':<15} | {e}")
