import dns.resolver
import os
import requests
import csv
from datetime import datetime

DNS_SERVERS = ['8.8.8.8', '8.8.4.4']
DOMAIN_FILE = 'tunnerlbear.txt'
OUTPUT_FILE = 'tunnelbear_subnet.txt'
OUTPUT_CSV_FILE = "tunnelbear_ips.csv"
IP_GUIDE_URL = "https://ip.guide/"

def configure_dns_resolver():
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = DNS_SERVERS
    return resolver

def read_domains_from_file(file_path):
    if not os.path.exists(file_path):
        print(f"The file '{file_path}' does not exist.")
        exit(1)
    with open(file_path) as f:
        return [line.strip() for line in f]

def fetch_subnet_for_ip(ip):
    try:
        response = requests.get(f"{IP_GUIDE_URL}{ip}", timeout=5)
        if response.status_code == 200:
            subnet = response.json().get('network', {}).get('cidr', None)
            if not subnet:
                raise ValueError("Invalid response format")
        else:
            raise ValueError(f"Received status code {response.status_code}")
    except Exception as e:
        print(f"Error fetching subnet for IP {ip}: {e}")
        ip_split = str(ip).split('.')
        subnet = f"{'.'.join(ip_split[:3])}.0/24"
    return subnet

def resolve_domains(domains, resolver, resolve_subnets=False):
    ip_hostnames = {}
    ip_subnet = set()
    for domain in domains:
        print(f"Resolving domain: {domain}")
        try:
            temp_ips = set()
            for _ in range(10):
                answers = resolver.resolve(domain, 'A')
                for ip in answers:
                    temp_ips.add(str(ip))
            ip_hostnames[domain] = temp_ips
            if resolve_subnets:
                for ip in temp_ips:
                    subnet = fetch_subnet_for_ip(ip)
                    print(f"Subnet: {subnet}")
                    ip_subnet.add(subnet)
        except Exception as e:
            print(f"Error resolving {domain}: {e}")
    return ip_hostnames, ip_subnet

def read_existing_ips(file_path):
    existing_ips = {}
    if os.path.exists(file_path):
        with open(file_path, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_ips[row['IP']] = {
                    'Hostname': row['Hostname'],
                    'First Seen': row['First Seen'],
                    'Last Seen': row['Last Seen']
                }
    return existing_ips

def write_to_file(data, file_path, mode='w'):
    with open(file_path, mode) as f:
        if isinstance(data, set):
            for item in data:
                f.write(f"{item}\n")
        elif isinstance(data, dict):
            fieldnames = ['Hostname', 'IP', 'First Seen', 'Last Seen']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for ip, details in data.items():
                writer.writerow({
                    'Hostname': details['Hostname'],
                    'IP': ip,
                    'First Seen': details['First Seen'],
                    'Last Seen': details['Last Seen']
                })

def main():
    resolver = configure_dns_resolver()
    domains = read_domains_from_file(DOMAIN_FILE)
    ip_hostnames, subnets = resolve_domains(domains, resolver, resolve_subnets=True)
    
    existing_ips = read_existing_ips(OUTPUT_CSV_FILE)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for domain, ips in ip_hostnames.items():
        for ip in ips:
            if ip in existing_ips:
                existing_ips[ip]['Last Seen'] = current_time
            else:
                existing_ips[ip] = {
                    'Hostname': domain,
                    'First Seen': current_time,
                    'Last Seen': current_time
                }
    
    write_to_file(existing_ips, OUTPUT_CSV_FILE)
    write_to_file(subnets, OUTPUT_FILE)

if __name__ == "__main__":
    main()
