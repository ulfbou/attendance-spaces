import base64, json, os
from .domain import DomainError, CheckpointKind, Lifecycle, FactKind, require_text, require_id, stable_user_id
REPOSITORY=None

def response(status, body, headers=None, base64_encoded=False):
    values={"content-type":"application/json","cache-control":"no-store"}; values.update(headers or {})
    payload=base64.b64encode(body).decode() if base64_encoded else (body if isinstance(body,str) else json.dumps(body,separators=(",",":")))
    result={"statusCode":status,"headers":values,"body":payload}
    if base64_encoded: result["isBase64Encoded"]=True
    return result

def body_of(event):
    raw=event.get("body") or "{}"
    if event.get("isBase64Encoded"): raw=base64.b64decode(raw).decode()
    try: value=json.loads(raw)
    except (ValueError,UnicodeError): raise DomainError("INVALID_JSON","Request body must be JSON")
    if not isinstance(value,dict): raise DomainError("INVALID_JSON","Request body must be an object")
    return value

def bearer(event):
    headers={k.lower():v for k,v in (event.get("headers") or {}).items()}; value=headers.get("authorization","")
    if not value.startswith("Bearer "): raise DomainError("UNAUTHENTICATED","Bearer token required",401)
    return value[7:]

def claims(event):
    from .verifier import TokenError, verify
    try: return verify(bearer(event))
    except TokenError as exc: raise DomainError("UNAUTHENTICATED",str(exc),401)

def repository():
    global REPOSITORY
    if REPOSITORY is None:
        import boto3
        from .repository import DynamoRepository
        REPOSITORY=DynamoRepository(boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"]))
    return REPOSITORY

def require_owner(member):
    if member["role"]!="OWNER": raise DomainError("FORBIDDEN","OWNER role required",403)

def handler(event, context):
    try:
        c=claims(event); user_id=stable_user_id(c["sub"]); http=event.get("requestContext",{}).get("http",{}); method=http.get("method",""); path=http.get("path","")
        if method=="POST" and path=="/spaces":
            data=body_of(event); result=repository().create_space(user_id,require_text(data.get("name"),"name"),require_id(data.get("requestId"),"req_"),require_text(data.get("idempotencyKey"),"idempotencyKey",128)); return response(200 if result["idempotency"]["replayed"] else 201,result)
        if path.startswith("/spaces/"):
            parts=path.strip("/").split("/"); space_id=require_id(parts[1],"spc_"); member=repository().membership(space_id,user_id)
            if not member: raise DomainError("FORBIDDEN","Current membership required",403)
            if method=="GET" and len(parts)==2:
                view=repository().owner_view(space_id) if member["role"]=="OWNER" else repository().participant_view(space_id,user_id); return response(200,view)
            if method=="GET" and parts[2:]==["export.xlsx"]:
                require_owner(member)
                from .xlsx_export import CONTENT_TYPE, build_attendance_workbook
                workbook=build_attendance_workbook(repository().space(space_id),repository().export_rows(space_id))
                return response(200,workbook,{"content-type":CONTENT_TYPE,"content-disposition":f'attachment; filename="attendance-{space_id}.xlsx"'},True)
            data=body_of(event)
            if method=="POST" and parts[2:]==["checkpoints"]:
                require_owner(member)
                try: kind=CheckpointKind(data.get("kind")); lifecycle=Lifecycle(data.get("lifecycle","DRAFT"))
                except ValueError: raise DomainError("INVALID_INPUT","Unknown checkpoint kind or lifecycle")
                return response(201,repository().create_checkpoint(space_id,user_id,kind.value,lifecycle.value,require_text(data.get("title"),"title")))
            if method=="POST" and len(parts)==4 and parts[2]=="checkpoints":
                checkpoint_id=require_id(parts[3],"cp_")
                try: kind=FactKind(data.get("kind"))
                except ValueError: raise DomainError("INVALID_INPUT","Unknown attendance fact kind")
                comment=data.get("participantComment")
                if comment is not None: comment=require_text(comment,"participantComment",500)
                if "managerNote" in data: raise DomainError("INVALID_INPUT","managerNote is not participant input")
                return response(201,repository().record_fact(space_id,user_id,checkpoint_id,kind.value,comment))
            if method=="POST" and len(parts)==6 and parts[2]=="attendance" and parts[5]=="corrections":
                require_owner(member); affected_user=require_id(parts[3],"usr_"); checkpoint_id=require_id(parts[4],"cp_")
                try: replacement=FactKind(data.get("replacementKind")).value
                except ValueError: raise DomainError("INVALID_INPUT","Unknown replacement attendance fact kind")
                reason=require_text(data.get("reason"),"reason",500); note=data.get("managerNote")
                if note is not None: note=require_text(note,"managerNote",1000)
                if "participantComment" in data: raise DomainError("INVALID_INPUT","participantComment is not owner correction input")
                return response(200,repository().correct_fact(space_id,user_id,affected_user,checkpoint_id,replacement,reason,note))
        raise DomainError("NOT_FOUND","Route not found",404)
    except DomainError as exc: return response(exc.status,{"error":{"code":exc.code,"message":str(exc)}})
    except Exception: return response(500,{"error":{"code":"INTERNAL_ERROR","message":"Request failed"}})
