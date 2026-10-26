import base64
import hashlib
import json
import os
import time
from urllib.request import urlopen

class TokenError(ValueError): pass
_CACHE={"at":0,"keys":{}}
def _decode(value):
    value += "="*((4-len(value)%4)%4)
    return base64.urlsafe_b64decode(value)
def _keys():
    now=time.time()
    if _CACHE["keys"] and now-_CACHE["at"]<3600: return _CACHE["keys"]
    region=os.environ["AWS_REGION"]; pool=os.environ["USER_POOL_ID"]
    url=f"https://cognito-idp.{region}.amazonaws.com/{pool}/.well-known/jwks.json"
    with urlopen(url,timeout=3) as response: data=json.load(response)
    _CACHE.update(at=now,keys={key["kid"]:key for key in data["keys"]})
    return _CACHE["keys"]
def verify(token, now=None):
    try:
        encoded_header,encoded_payload,encoded_signature=token.split(".")
        header=json.loads(_decode(encoded_header)); payload=json.loads(_decode(encoded_payload))
        if header.get("alg")!="RS256": raise TokenError("Unexpected token algorithm")
        key=_keys().get(header.get("kid"))
        if not key: _CACHE["at"]=0; key=_keys().get(header.get("kid"))
        if not key: raise TokenError("Unknown signing key")
        n=int.from_bytes(_decode(key["n"]),"big"); e=int.from_bytes(_decode(key["e"]),"big")
        signature=_decode(encoded_signature); recovered=pow(int.from_bytes(signature,"big"),e,n).to_bytes((n.bit_length()+7)//8,"big")
        digest=hashlib.sha256(f"{encoded_header}.{encoded_payload}".encode()).digest()
        prefix=bytes.fromhex("3031300d060960864801650304020105000420")
        padding_length=len(recovered)-len(prefix)-len(digest)-3
        expected=b"\x00\x01"+b"\xff"*padding_length+b"\x00"+prefix+digest
        if padding_length<8 or recovered!=expected: raise TokenError("Invalid signature")
        timestamp=int(now if now is not None else time.time())
        issuer=f"https://cognito-idp.{os.environ['AWS_REGION']}.amazonaws.com/{os.environ['USER_POOL_ID']}"
        if payload.get("iss")!=issuer or payload.get("client_id")!=os.environ["CLIENT_ID"] or payload.get("token_use")!="access" or int(payload.get("exp",0))<=timestamp:
            raise TokenError("Invalid token claims")
        if not payload.get("sub"): raise TokenError("Token subject missing")
        return payload
    except TokenError: raise
    except Exception as exc: raise TokenError("Malformed token") from exc
