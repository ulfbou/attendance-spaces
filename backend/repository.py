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
          {"Put":{"Item":{"PK":idem_pk,"SK":idem_sk,"entity":"Idempotency","requestId":request_id,"result":json.dumps(result,separators=(",",":")),"createdAt":created},"ConditionExpression":"attribute_not_exists(PK)"}}]
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
    def space(self, space_id): return self.get(f"SPACE#{space_id}", "META")
    def correct_fact(self, space_id, actor_id, user_id, checkpoint_id, replacement_kind, reason, manager_note=None):
        original=self.get(f"SPACE#{space_id}",f"FACT#{user_id}#{checkpoint_id}")
        if not original: raise DomainError("NOT_FOUND","Attendance fact not found",404)
        corrected=now_iso(); event_id=opaque("evt_")
        replacement=dict(original)
        for private_field in ("managerNote", "correctedBy", "correctionEventId"):
            replacement.pop(private_field, None)
        replacement.update(kind=replacement_kind,correctedAt=corrected)
        audit={"PK":f"SPACE#{space_id}","SK":f"AUDIT#{corrected}#{event_id}","entity":"AuditEvent","eventId":event_id,"kind":"ATTENDANCE_FACT_CORRECTED","actorUserId":actor_id,"occurredAt":corrected,"reason":reason,"affectedFact":{"userId":user_id,"checkpointId":checkpoint_id,"original":original},"replacement":{"kind":replacement_kind,"managerNote":manager_note}}
        tx=[{"Put":{"Item":replacement,"ConditionExpression":"#occurredAt = :occurredAt","ExpressionAttributeNames":{"#occurredAt":"occurredAt"},"ExpressionAttributeValues":{":occurredAt":original["occurredAt"]}}},{"Put":{"Item":audit,"ConditionExpression":"attribute_not_exists(PK)"}}]
        try: self.table.meta.client.transact_write_items(TransactItems=[self._serialize(x) for x in tx])
        except Exception as exc:
            if "TransactionCanceled" in type(exc).__name__: raise DomainError("CORRECTION_CONFLICT","Attendance fact changed before correction",409)
            raise
        return {"fact":replacement,"auditEvent":audit}
    @staticmethod
    def _participant_fact(fact):
        allowed=(
            "entity",
            "userId",
            "checkpointId",
            "kind",
            "occurredAt",
            "participantComment",
            "correctedAt",
        )
        return {key:fact[key] for key in allowed if key in fact}
    def export_rows(self, space_id):
        items=self.query(f"SPACE#{space_id}")
        checkpoints={
            x["checkpointId"]:x
            for x in items
            if x["SK"].startswith("CHECKPOINT#")
        }
        manager_notes={}
        for audit in (
            x
            for x in items
            if x["SK"].startswith("AUDIT#")
            and x.get("kind")=="ATTENDANCE_FACT_CORRECTED"
        ):
            affected=audit.get("affectedFact",{})
            key=(
                affected.get("userId"),
                affected.get("checkpointId"),
            )
            note=audit.get("replacement",{}).get("managerNote")
            if key[0] and key[1] and note is not None:
                manager_notes[key]=note
        rows=[]
        for fact in (
            x for x in items if x["SK"].startswith("FACT#")
        ):
            cp=checkpoints.get(fact["checkpointId"],{})
            key=(fact["userId"],fact["checkpointId"])
            rows.append({
                "checkpointId":fact["checkpointId"],
                "checkpointKind":cp.get("kind",""),
                "lifecycle":cp.get("lifecycle",""),
                "userId":fact["userId"],
                "factKind":fact["kind"],
                "occurredAt":fact["occurredAt"],
                "participantComment":fact.get(
                    "participantComment",
                    "",
                ),
                "managerNote":manager_notes.get(key,""),
            })
        return sorted(
            rows,
            key=lambda x:(x["checkpointId"],x["userId"]),
        )
    def owner_view(self, space_id):
        items=self.query(f"SPACE#{space_id}")
        return {"space":next((x for x in items if x["SK"]=="META"),None),"members":[x for x in items if x["SK"].startswith("MEMBER#")],"checkpoints":[x for x in items if x["SK"].startswith("CHECKPOINT#")],"facts":[x for x in items if x["SK"].startswith("FACT#")]}
    def participant_view(self, space_id, user_id):
        checkpoints=self.query(f"SPACE#{space_id}","CHECKPOINT#")
        facts=[
            self._participant_fact(fact)
            for fact in self.query(
                f"SPACE#{space_id}",
                f"FACT#{user_id}#",
            )
        ]
        return {
            "spaceId":space_id,
            "userId":user_id,
            "checkpoints":checkpoints,
            "facts":facts,
        }
