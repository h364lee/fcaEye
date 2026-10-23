import secrets

pid = []

for i in range(10):
    hash_token = secrets.token_hex(8)
    pid.append(hash_token)

print(pid)
