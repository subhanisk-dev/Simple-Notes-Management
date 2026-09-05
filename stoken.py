from itsdangerous import URLSafeTimedSerializer
secret_key='Subhani@123'

def entoken(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.dumps(data)

def dntoken(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.loads(data)
