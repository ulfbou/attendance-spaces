import base64, json, unittest
from backend import app
from backend.domain import display_state
from unittest.mock import patch

class FakeRepository:
    def __init__(self): self.created=[]; self.member={"role":"OWNER"}
    def create_space(self,*args): self.created.append(args); return {"idempotency":{"replayed":False},"space":{"spaceId":"spc_abcdefghijklmnop","name":args[1]},"ownerMembership":{},"ownershipClaim":{},"auditEvent":{}}
    def membership(self,*args): return self.member
    def owner_view(self,space): return {"space":{"spaceId":space},"members":[],"checkpoints":[],"facts":[]}
    def participant_view(self,space,user): return {"spaceId":space,"userId":user,"checkpoints":[],"facts":[]}
    def create_checkpoint(self,*args): return {"checkpointId":"cp_abcdefghijklmnop","kind":args[2],"lifecycle":args[3]}
    def record_fact(self,*args): return {"checkpointId":args[2],"kind":args[3],"userId":args[1]}

def token(sub="google-subject"):
    raw=json.dumps({"sub":sub}).encode(); payload=base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"e30.{payload}.signature"
def event(method,path,body=None):
    return {"headers":{"authorization":"Bearer "+token()},"requestContext":{"http":{"method":method,"path":path}},"body":json.dumps(body) if body else None}

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.repo=FakeRepository(); app.REPOSITORY=self.repo
        self.verify=patch("backend.verifier.verify", return_value={"sub":"google-subject"}); self.verify.start()
    def tearDown(self): self.verify.stop(); app.REPOSITORY=None
    def test_create_space_passes_complete_atomic_command(self):
        result=app.handler(event("POST","/spaces",{"name":"Kurs A","requestId":"req_abcdefghijklmnop","idempotencyKey":"abcdefghijklmnop"}),None)
        self.assertEqual(result["statusCode"],201); self.assertEqual(len(self.repo.created),1)
    def test_membership_controls_owner_view(self):
        result=app.handler(event("GET","/spaces/spc_abcdefghijklmnop"),None); self.assertEqual(result["statusCode"],200)
        self.repo.member=None; result=app.handler(event("GET","/spaces/spc_abcdefghijklmnop"),None); self.assertEqual(result["statusCode"],403)
    def test_url_without_bearer_is_not_authority(self):
        value=event("GET","/spaces/spc_abcdefghijklmnop"); value["headers"]={}
        self.assertEqual(app.handler(value,None)["statusCode"],401)
    def test_owner_creates_checkpoint_and_participant_records_fact(self):
        made=app.handler(event("POST","/spaces/spc_abcdefghijklmnop/checkpoints",{"kind":"CHECK_IN","title":"Start"}),None)
        self.assertEqual(made["statusCode"],201)
        fact=app.handler(event("POST","/spaces/spc_abcdefghijklmnop/checkpoints/cp_abcdefghijklmnop",{"kind":"CHECKED_IN","participantComment":"Här"}),None)
        self.assertEqual(fact["statusCode"],201)
    def test_manager_note_is_not_participant_input(self):
        result=app.handler(event("POST","/spaces/spc_abcdefghijklmnop/checkpoints/cp_abcdefghijklmnop",{"kind":"CHECKED_IN","managerNote":"forbidden"}),None)
        self.assertEqual(result["statusCode"],400)
    def test_facts_and_display_states_remain_separate(self):
        checkpoint={"lifecycle":"OPEN"}; self.assertEqual(display_state(checkpoint),"AVAILABLE"); self.assertEqual(display_state(checkpoint,{"kind":"CHECKED_IN"}),"COMPLETED")

if __name__ == "__main__": unittest.main()
