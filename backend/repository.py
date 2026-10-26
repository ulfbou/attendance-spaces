import json
from .domain import DomainError, opaque, now_iso

class DynamoRepository:
    def __init__(self, table): self.table=table
    @staticmethod
    def _key(pk, sk): return {"PK": pk, "SK": sk}
    def get(self, pk, sk): return self.table.get_item(Key=self._key(pk, sk), ConsistentRead=True).get("Item")
    def query(self, pk, begins=None):
        from boto3.dynamodb.conditions import Key
        expr=Key("PK").eq(pk)
        if begins: expr=expr & Key("SK").begins_with(begins)
        return self.table.query(KeyConditionExpression=expr, ConsistentRead=True).get("Items", [])
    def create_space(self, user_id, name, request_id, idem_key):
        idem_pk=f"USER#{user_id}"; idem_sk=f"IDEMPOTENCY#{idem_key}"
        existing=self.get(idem_pk, idem_sk)
        if existing:
            if existing.get("requestId") != request_id: raise DomainError("IDEMPOTENCY_CONFLICT", "Idempotency key was used by another request", 409)
            result=json.loads(existing["result"]); result["idempotency"]["replayed"]=True; return result
        space_id=opaque("spc_"); event_id=opaque("evt_"); created=now_iso()
        result={"space":{"spaceId":space_id,"name":name},"ownerMembership":{"spaceId":space_id,"userId":user_id,"role":"OWNER"},"ownershipClaim":{"userId":user_id,"spaceId":space_id,"unique":True},"auditEvent":{"eventId":event_id,"kind":"ATTENDANCE_SPACE_CREATED"},"idempotency":{"key":idem_key,"replayed":False}}
        tx=[
          {"Put":{"Item":{"PK":f"SPACE#{space_id}","SK":"META","entity":"AttendanceSpace","spaceId":space_id,"name":name,"createdAt":created},"ConditionExpression":"attribute_not_exists(PK)"}},
          {"Put":{"Item":{"PK":f"SPACE#{space_id}","SK":f"MEMBER#{user_id}","entity":"Membership","userId":user_id,"role":"OWNER"},"ConditionExpression":"attribute_not_exists(PK)"}},
          {"Put":{"Item":{"PK":f"USER#{user_id}","SK":"OWNERSHIP","entity":"OwnershipClaim","spaceId":space_id},"ConditionExpression":"attribute_not_exists(PK)"}},
          {"Put":{"Item":{"PK":f"SPACE#{space_id}","SK":f"AUDIT#{created}#{event_id}","entity":"AuditEvent","eventId":event_id,"kind":"ATTENDANCE_SPACE_CREATED","actorUserId":user_id,"occurredAt":created},"ConditionExpression":"attribute_not_exists(PK)"}},
          {"Put":{"Item":{"PK":idem_pk,"SK":idem_sk,"entity":"Idempotency","requestId":request_id,"result":json.dumps(result,separators=(",",":")),"createdAt":created},"ConditionExpression":"attribute_not_exists(PK)"}},]
        try: self.table.meta.client.transact_write_items(TransactItems=[self._serialize(x) for x in tx], ClientRequestToken=request_id[-36:])
        except Exception as exc:
            if "TransactionCanceled" in type(exc).__name__:
                claim=self.get(f"USER#{user_id}", "OWNERSHIP")
                if claim: raise DomainError("OWNERSHIP_EXISTS", "User already owns an attendance space", 409)
                replay=self.get(idem_pk, idem_sk)
                if replay: return self.create_space(user_id,name,request_id,idem_key)
            raise
        return result
    def _serialize(self, action):
        from boto3.dynamodb.types import TypeSerializer
        ser=TypeSerializer(); kind,spec=next(iter(action.items())); spec=dict(spec); spec["TableName"]=self.table.name
        for field in ("Item","Key","ExpressionAttributeValues"):
            if field in spec: spec[field]={k:ser.serialize(v) for k,v in spec[field].items()}
        return {kind:spec}
    def create_checkpoint(self, space_id, actor_id, kind, lifecycle, title):
        checkpoint_id=opaque("cp_"); created=now_iso()
        item={"PK":f"SPACE#{space_id}","SK":f"CHECKPOINT#{checkpoint_id}","entity":"Checkpoint","checkpointId":checkpoint_id,"kind":kind,"lifecycle":lifecycle,"title":title,"createdAt":created,"createdBy":actor_id}
        self.table.put_item(Item=item,ConditionExpression="attribute_not_exists(PK)")
        return item
    def record_fact(self, space_id, user_id, checkpoint_id, kind, comment=None):
        occurred=now_iso(); item={"PK":f"SPACE#{space_id}","SK":f"FACT#{user_id}#{checkpoint_id}","entity":"AttendanceFact","userId":user_id,"checkpointId":checkpoint_id,"kind":kind,"occurredAt":occurred}
        if comment: item["participantComment"]=comment
        self.table.put_item(Item=item,ConditionExpression="attribute_not_exists(PK)")
        return item
    def membership(self, space_id, user_id): return self.get(f"SPACE#{space_id}", f"MEMBER#{user_id}")
    def owner_view(self, space_id):
        items=self.query(f"SPACE#{space_id}")
        return {"space":next((x for x in items if x["SK"]=="META"),None),"members":[x for x in items if x["SK"].startswith("MEMBER#")],"checkpoints":[x for x in items if x["SK"].startswith("CHECKPOINT#")],"facts":[x for x in items if x["SK"].startswith("FACT#")]}
    def participant_view(self, space_id, user_id):
        checkpoints=self.query(f"SPACE#{space_id}","CHECKPOINT#")
        facts=self.query(f"SPACE#{space_id}",f"FACT#{user_id}#")
        return {"spaceId":space_id,"userId":user_id,"checkpoints":checkpoints,"facts":facts}
