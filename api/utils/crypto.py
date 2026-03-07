from cryptography.fernet import Fernet
import os

key = os.getenv("SECRET_KEY").encode()

fernet = Fernet(key)

def encrypt(data):
    return fernet.encrypt(data.encode()).decode()

def decrypt(data):
    return fernet.decrypt(data.encode()).decode()