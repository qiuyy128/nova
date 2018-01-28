# -*- coding:utf-8 -*-
from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
import base64
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rsa_pub = os.path.join(BASE_DIR, 'script', 'rsa.pub')
rsa_key = os.path.join(BASE_DIR, 'script', 'rsa.key')


# 数据加密
def _enc_(data=''):
    with open(rsa_pub, 'r') as f:
        public_key = f.read()
        rsa_key_obj = RSA.importKey(public_key)
        cipher_obj = Cipher_PKCS1_v1_5.new(rsa_key_obj)
        cipher_text = base64.b64encode(cipher_obj.encrypt(data))
        print 'cipher_text is:', cipher_text
        return cipher_text


# 数据解密
def _dec_(data=''):
    with open(rsa_key, 'r') as f:
        private_key = f.read()
        rsa_key_obj = RSA.importKey(private_key)
        cipher_obj = Cipher_PKCS1_v1_5.new(rsa_key_obj)
        random_generator = Random.new().read
        plain_text = cipher_obj.decrypt(base64.b64decode(data), random_generator)
        print 'plain_text is:', plain_text
        return plain_text


if __name__ == '__main__':
    _enc_('data')
    # _dec_('')
