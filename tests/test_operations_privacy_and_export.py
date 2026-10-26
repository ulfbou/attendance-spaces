import base64, io, json, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
from backend import app
from backend.repository import DynamoRepository
from backend.xlsx_export import CONTENT_TYPE, build_attendance_workbook
ROOT=Path(__file__).resolve().parents[1]
class FakeRepository:
    def __init__(self,role='OWNER'): self.member={'role':role}; self.corrected=[]
    def membership(self,*args): return self.member
    def space(self,*args): return {'spaceId':args[0],'name':'Course'}
    def export_rows(self,*args): return [{'checkpointId':'cp_abcdefghijklmnop','userId':'usr_abcdefghijklmnop','factKind':'CHECKED_IN','participantComment':'present','managerNote':'verified'}]
    def correct_fact(self,*args): self.corrected.append(args); return {'fact':{'kind':args[4]},'auditEvent':{'kind':'ATTENDANCE_FACT_CORRECTED','reason':args[5],'original':{'kind':'PRESENCE_CONFIRMED'}}}
def event(method,path,body=None): return {'headers':{'authorization':'Bearer token'},'requestContext':{'http':{'method':method,'path':path}},'body':json.dumps(body) if body else None}

class QueryRepository(DynamoRepository):
    def __init__(self, items):
        self.items = items

    def query(self, pk, begins=None):
        return [
            item
            for item in self.items
            if not begins or item["SK"].startswith(begins)
        ]

class Issue5Tests(unittest.TestCase):
    def setUp(self): self.repo=FakeRepository(); app.REPOSITORY=self.repo; self.verify=patch('backend.verifier.verify',return_value={'sub':'subject'}); self.verify.start()
    def tearDown(self): self.verify.stop(); app.REPOSITORY=None
    def test_owner_export_is_direct_xlsx(self):
        result=app.handler(event('GET','/spaces/spc_abcdefghijklmnop/export.xlsx'),None)
        self.assertEqual(result['statusCode'],200); self.assertEqual(result['headers']['content-type'],CONTENT_TYPE); self.assertTrue(result['isBase64Encoded'])
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(result['body']))) as book: self.assertIn('xl/worksheets/sheet1.xml',book.namelist())
    def test_participant_cannot_export_aggregate(self):
        self.repo.member={'role':'PARTICIPANT'}; self.assertEqual(app.handler(event('GET','/spaces/spc_abcdefghijklmnop/export.xlsx'),None)['statusCode'],403)
    def test_non_member_is_denied(self):
        self.repo.member=None; self.assertEqual(app.handler(event('GET','/spaces/spc_abcdefghijklmnop/export.xlsx'),None)['statusCode'],403)
    def test_owner_correction_is_audited_and_inputs_are_separate(self):
        path='/spaces/spc_abcdefghijklmnop/attendance/usr_abcdefghijklmnop/cp_abcdefghijklmnop/corrections'
        result=app.handler(event('POST',path,{'replacementKind':'CHECKED_OUT','reason':'verified','managerNote':'owner only'}),None)
        self.assertEqual(result['statusCode'],200); self.assertEqual(json.loads(result['body'])['auditEvent']['kind'],'ATTENDANCE_FACT_CORRECTED')
        denied=app.handler(event('POST',path,{'replacementKind':'CHECKED_OUT','reason':'x','participantComment':'forbidden'}),None); self.assertEqual(denied['statusCode'],400)
    def test_participant_cannot_correct(self):
        self.repo.member={'role':'PARTICIPANT'}; path='/spaces/spc_abcdefghijklmnop/attendance/usr_abcdefghijklmnop/cp_abcdefghijklmnop/corrections'
        self.assertEqual(app.handler(event('POST',path,{'replacementKind':'CHECKED_OUT','reason':'x'}),None)['statusCode'],403)
    def test_workbook_is_deterministic(self):
        rows=self.repo.export_rows('x'); self.assertEqual(build_attendance_workbook({},rows),build_attendance_workbook({},rows))
    def test_template_has_budget_retention_real_package_and_no_export_storage(self):
        source=(ROOT/'infrastructure/backend.yaml').read_text()
        for marker in ('AWS::Budgets::Budget','RetentionInDays: 7','S3Bucket: !Ref PackageBucket','BudgetEmail:'): self.assertIn(marker,source)
        self.assertNotIn('ZipFile:',source); self.assertNotIn('AWS::S3::Bucket',source)

    def test_participant_projection_excludes_owner_correction_metadata(self):
        fact = {
            "PK": "SPACE#s",
            "SK": (
                "FACT#usr_abcdefghijklmnop#"
                "cp_abcdefghijklmnop"
            ),
            "entity": "AttendanceFact",
            "userId": "usr_abcdefghijklmnop",
            "checkpointId": "cp_abcdefghijklmnop",
            "kind": "CHECKED_OUT",
            "occurredAt": "2026-01-01T00:00:00Z",
            "participantComment": "present",
            "correctedAt": "2026-01-02T00:00:00Z",
            "correctedBy": "usr_ownerprivateid",
            "correctionEventId": "evt_privateidentifier",
            "managerNote": "private",
        }

        view = QueryRepository([fact]).participant_view(
            "s",
            "usr_abcdefghijklmnop",
        )
        visible = view["facts"][0]

        self.assertEqual(visible["kind"], "CHECKED_OUT")
        self.assertEqual(
            visible["participantComment"],
            "present",
        )

        for key in (
            "managerNote",
            "correctedBy",
            "correctionEventId",
            "PK",
            "SK",
        ):
            self.assertNotIn(key, visible)

    def test_export_uses_owner_only_audit_note_after_correction(self):
        items = [
            {
                "PK": "SPACE#s",
                "SK": "CHECKPOINT#cp_abcdefghijklmnop",
                "checkpointId": "cp_abcdefghijklmnop",
                "kind": "CHECK_OUT",
                "lifecycle": "CLOSED",
            },
            {
                "PK": "SPACE#s",
                "SK": (
                    "FACT#usr_abcdefghijklmnop#"
                    "cp_abcdefghijklmnop"
                ),
                "userId": "usr_abcdefghijklmnop",
                "checkpointId": "cp_abcdefghijklmnop",
                "kind": "CHECKED_OUT",
                "occurredAt": "2026-01-01T00:00:00Z",
                "participantComment": "present",
            },
            {
                "PK": "SPACE#s",
                "SK": "AUDIT#2",
                "kind": "ATTENDANCE_FACT_CORRECTED",
                "affectedFact": {
                    "userId": "usr_abcdefghijklmnop",
                    "checkpointId": "cp_abcdefghijklmnop",
                },
                "replacement": {
                    "kind": "CHECKED_OUT",
                    "managerNote": "owner only",
                },
            },
        ]

        row = QueryRepository(items).export_rows("s")[0]

        self.assertEqual(
            row["managerNote"],
            "owner only",
        )
        self.assertEqual(
            row["participantComment"],
            "present",
        )

if __name__=='__main__': unittest.main()
