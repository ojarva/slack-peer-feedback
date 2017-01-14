import hashlib
import django.conf

def gen_user_link_secret(user_id):
    return hashlib.sha256(user_id + settings.USER_LINK_SECRET).hexdigest()

def verify_user_link_secret(user_id, secret):
    return gen_user_link_secret(user_id) == secret
