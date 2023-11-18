import random
import time

def generate_table(pri_key, step):
    table = list(range(256))

    seed = pri_key * divmod(time.time(), step)[0]
    random.seed(seed)

    random.shuffle(table)

    return table

def encrypt(bytes, table):
    encrypted_bytes = []
    for byte in bytes:
        encrypted_bytes.append(table[byte])

    return bytearray(encrypted_bytes)

def decrypt(bytes, table):
    decrypted_bytes = []
    for byte in bytes:
        decrypted_bytes.append(table.index(byte))

    return bytearray(decrypted_bytes)