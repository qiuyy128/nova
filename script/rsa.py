# -*- coding:utf-8 -*-
from Crypto import Random
from Crypto.PublicKey import RSA

# 获取一个伪随机数生成器
random_generator = Random.new().read
# 获取一个rsa算法对应的密钥对生成器实例
rsa = RSA.generate(1024, random_generator)

# 生成私钥并保存
private_pem = rsa.exportKey()
with open('rsa.key', 'w') as f:
    f.write(private_pem)

# 生成公钥并保存
public_pem = rsa.publickey().exportKey()
with open('rsa.pub', 'w') as f:
    f.write(public_pem)
