import base64, json, os
from .domain import DomainError, CheckpointKind, Lifecycle, FactKind, require_text, require_id, stable_user_id

REPOSITORY=None

def response(status, body):
    return {"statusCode":status,"headers":{"content-type":"application/json","cache-control":"no-store"},"body":json.dumps(body,separators=(",",":"))}
def body_of(event):
    raw=event.get("body") or "{}"
    if event.get("isBase64Encoded"): raw=base64.b64decode(raw).decode()
    try: value=json.loads(raw)
    except (ValueError,UnicodeError): raise DomainError("INVALID_JSON","Request body must be JSON")
    if not isinstance(value,dict): raise DomainError("INVALID_JSON","Request body must be an object")
    return value
def bearer(event):
    headers={k.lower():v for k,v in (event.get("headers") or {}).items()}
    value=headers.get("authorization","")
    if not value.startswith("Bearer "): raise DomainError("UNAUTHENTICATED","Bearer token required",401)
    return value[7:]
def claims(event):
    from .verifier import TokenError, verify
    try: return verify(bearer(event))
    except TokenError as exc: raise DomainError("UNAUTHENTICATED", str(exc), 401)
def repository():
    global REPOSITORY
    if REPOSITORY is None:
        import boto3
        from .repository import DynamoRepository
        REPOSITORY=DynamoRepository(boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"]))
    return REPOSITORY
def handler(event, context):
    try:
        c=claims(event); user_id=stable_user_id(c["sub"]); http=event.get("requestContext",{}).get("http",{}); method=http.get("method",""); path=http.get("path","")
        if method=="POST" and path=="/spaces":
            data=body_of(event); result=repository().create_space(user_id,require_text(data.get("name"),"name"),require_id(data.get("requestId"),"req_"),require_text(data.get("idempotencyKey"),"idempotencyKey",128)); return response(200 if result["idempotency"]["replayed"] else 201,result)
        if path.startswith("/spaces/"):
            parts=path.strip("/").split("/"); space_id=require_id(parts[1],"spc_"); member=repository().membership(space_id,user_id)
            if not member: raise DomainError("FORBIDDEN","Current membership required",403)
            if method=="GET" and len(parts)==2:
                view=repository().owner_view(space_id) if member["role"]=="OWNER" else repository().participant_view(space_id,user_id)
                return response(200,view)
            data=body_of(event)
            if method=="POST" and parts[2:]==["checkpoints"]:
                if member["role"]!="OWNER": raise DomainError("FORBIDDEN","OWNER role required",403)
                try: kind=CheckpointKind(data.get("kind")); lifecycle=Lifecycle(data.get("lifecycle","DRAFT"))
                except ValueError: raise DomainError("INVALID_INPUT","Unknown checkpoint kind or lifecycle")
                return response(201,repository().create_checkpoint(space_id,user_id,kind.value,lifecycle.value,require_text(data.get("title"),"title")))
            if method=="POST" and len(parts)==4 and parts[2]=="checkpoints" and parts[3].startswith("cp_"):
                checkpoint_id=require_id(parts[3],"cp_")
                try: kind=FactKind(data.get("kind"))
                except ValueError: raise DomainError("INVALID_INPUT","Unknown attendance fact kind")
                comment=data.get("participantComment")
                if comment is not None: comment=require_text(comment,"participantComment",500)
                if "managerNote" in data: raise DomainError("INVALID_INPUT","managerNote is not participant input")
                return response(201,repository().record_fact(space_id,user_id,checkpoint_id,kind.value,comment))
        raise DomainError("NOT_FOUND","Route not found",404)
    except DomainError as exc: return response(exc.status,{"error":{"code":exc.code,"message":str(exc)}})
    except Exception: return response(500,{"error":{"code":"INTERNAL_ERROR","message":"Request failed"}})
