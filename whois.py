import socket

website=input("Enter website (e.g. google.com): ")
ip=socket.gethostbyname(website)

print(f'The IP address of {website}: {ip}')