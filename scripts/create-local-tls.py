"""Create an owner-local CA and LAN certificate; never replace existing keys."""
import argparse
import datetime as dt
import ipaddress
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

parser=argparse.ArgumentParser()
parser.add_argument('--address',default='192.168.1.2')
args=parser.parse_args()
address=ipaddress.IPv4Address(args.address)
root=Path(__file__).resolve().parents[1]/'data/tls'
if not root.is_dir():
    raise SystemExit('Create and protect data/tls before generating keys')
files=[root/n for n in ('ca.key','ca.crt','server.key','server.crt')]
if any(p.exists() for p in files):
    if all(p.exists() for p in files):
        print('Existing TLS credentials preserved');raise SystemExit(0)
    raise SystemExit('Partial TLS credentials preserved; inspect before retrying')
now=dt.datetime.now(dt.timezone.utc)
ca_key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Larpus Home Local CA')])
ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-dt.timedelta(minutes=5)).not_valid_after(now+dt.timedelta(days=3650)).add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True).add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),critical=True).sign(ca_key,hashes.SHA256()))
key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Larpus LAN')])).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-dt.timedelta(minutes=5)).not_valid_after(now+dt.timedelta(days=365)).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True).add_extension(x509.SubjectAlternativeName([x509.IPAddress(address)]),critical=False).add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False).sign(ca_key,hashes.SHA256()))
for path,value in ((files[0],ca_key),(files[2],key)):
    with path.open('xb') as output: output.write(value.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
for path,value in ((files[1],ca),(files[3],cert)):
    with path.open('xb') as output: output.write(value.public_bytes(serialization.Encoding.PEM))
print('Created local CA and one-year LAN certificate. Share only ca.crt, never keys.')
