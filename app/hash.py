import bcrypt
import mysql.connector

# Hash password with bcrypt
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')
# Connect to MySQL



# Example user data

plain_password = 'F%#DHgd67!@)'  # Password to be hashed

# Hash the password
hashed_password = hash_password(plain_password)


print("User added successfully with hashed password.",hashed_password);

def verify_password(comingPassword: str, hashed_password: str) -> bool:
    print('comingPassword',comingPassword)
    print('hashed_password',hashed_password)
    res= bcrypt.checkpw(comingPassword.encode('utf-8'), hashed_password.encode('utf-8'))
    print('result in verifing',res)
    return res


con=verify_password(plain_password,hashed_password)
print('con',con)
import secrets

SECRET_KEY = secrets.token_hex(32)  # Generates a secure 64-character hexadecimal string
print('SECRET_KEY',SECRET_KEY)

