"""DynamoDB integration contract tests (issue #11, C2).

Skipped unless AWS_ENDPOINT_URL_DYNAMODB is set. The dev service in
compose.yaml provides it, pointing at the dynamodb service. The test owns
the table lifetime (setUpClass / tearDownClass) and starts every test from
an empty table (setUp) so asserts can be stated in absolute terms.

Run:
    docker compose --profile tools run --rm dev \
        python -m unittest tests.test_dynamo_integration -v

Mutation acceptance (issue #11, C2). After the suite is green:

    In backend/repository.py, inside DynamoRepository.create_space, replace
        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[self._serialize(x) for x in tx],
                ClientRequestToken=request_id[-36:],
            )
        except Exception as exc:
            ...
    with sequential writes of the same Put items:
        for action in tx:
            spec = action["Put"]
            self.table.put_item(
                Item=spec["Item"],
                ConditionExpression=spec.get("ConditionExpression"),
            )

    Run test_forced_rollback_leaves_no_partial_writes. It must fail: the
    third put_item raises ConditionalCheckFailedException, which does not
    match "TransactionCanceled" in create_space's handler, so the raw
    ClientError escapes the assertRaises(DomainError) block. Revert with:
        git checkout -- backend/repository.py

    Reordering TransactItems is NOT a valid mutation: DynamoDB condition
    evaluation is atomic across the whole transaction, so a reorder-only
    change preserves the atomicity property and the test correctly keeps
    passing.
"""
import os
import unittest
import uuid
from unittest.mock import patch

import boto3
from boto3.dynamodb.conditions import Attr, Key

from backend.domain import DomainError
from backend.repository import DynamoRepository


RUN = bool(os.environ.get("AWS_ENDPOINT_URL_DYNAMODB"))
TABLE_NAME = os.environ.get("LOCAL_DDB_TABLE", "attendance-spaces-integration")


def _endpoint():
    return os.environ["AWS_ENDPOINT_URL_DYNAMODB"]


@unittest.skipUnless(RUN, "AWS_ENDPOINT_URL_DYNAMODB not set")
class DynamoIntegrationTests(unittest.TestCase):
    """Integration contract for the real DynamoRepository against DynamoDB Local."""

    @classmethod
    def setUpClass(cls):
        cls.client = boto3.client("dynamodb", endpoint_url=_endpoint())
        cls.resource = boto3.resource("dynamodb", endpoint_url=_endpoint())
        cls._create_table()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.delete_table(TableName=TABLE_NAME)
        except cls.client.exceptions.ResourceNotFoundException:
            pass

    @classmethod
    def _create_table(cls):
        try:
            cls.client.create_table(
                TableName=TABLE_NAME,
                AttributeDefinitions=[
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                ],
                KeySchema=[
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
        except cls.client.exceptions.ResourceInUseException:
            pass

    def setUp(self):
        self.table = self.resource.Table(TABLE_NAME)
        self.repository = DynamoRepository(self.table)
        self._clear_table()

    def _clear_table(self):
        while True:
            items = self.table.scan().get("Items", [])
            if not items:
                return
            for item in items:
                self.table.delete_item(
                    Key={"PK": item["PK"], "SK": item["SK"]},
                )

    # -- fixtures ------------------------------------------------------
    def _new_user(self):
        return "usr_" + uuid.uuid4().hex[:24]

    def _new_space(self):
        return "spc_" + uuid.uuid4().hex[:24]

    def _new_checkpoint(self):
        return "cp_" + uuid.uuid4().hex[:24]

    def _new_request(self):
        return "req_" + uuid.uuid4().hex[:24]

    def _new_idem_key(self):
        return uuid.uuid4().hex  # 32 chars, within the app's 16..128 bound

    # -- DynamoDB helpers ---------------------------------------------
    def _query(self, pk, begins=None):
        cond = Key("PK").eq(pk)
        if begins:
            cond = cond & Key("SK").begins_with(begins)
        return self.table.query(KeyConditionExpression=cond).get("Items", [])

    def _scan_prefix(self, prefix):
        items = []
        kwargs = {"FilterExpression": Attr("PK").begins_with(prefix)}
        while True:
            response = self.table.scan(**kwargs)
            items.extend(response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                return items
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    # ==================================================================
    # 1. five-write transaction
    # ==================================================================
    def test_create_space_writes_all_five_items(self):
        user_id = self._new_user()
        request_id = self._new_request()
        idem_key = self._new_idem_key()

        result = self.repository.create_space(
            user_id, "Course A", request_id, idem_key,
        )
        space_id = result["space"]["spaceId"]

        space_items = self._query(f"SPACE#{space_id}")
        user_items = self._query(f"USER#{user_id}")

        # SPACE#: META, MEMBER#<user>, AUDIT#<created>#<eventId>.
        self.assertEqual(len(space_items), 3, space_items)
        # USER#: OWNERSHIP, IDEMPOTENCY#<idem_key>.
        self.assertEqual(len(user_items), 2, user_items)

        space_by_sk = {item["SK"]: item for item in space_items}

        meta = space_by_sk["META"]
        self.assertEqual(meta["entity"], "AttendanceSpace")
        self.assertEqual(meta["spaceId"], space_id)
        self.assertEqual(meta["name"], "Course A")

        member = space_by_sk[f"MEMBER#{user_id}"]
        self.assertEqual(member["entity"], "Membership")
        self.assertEqual(member["userId"], user_id)
        self.assertEqual(member["role"], "OWNER")

        audits = [
            item for sk, item in space_by_sk.items() if sk.startswith("AUDIT#")
        ]
        self.assertEqual(len(audits), 1, audits)
        audit = audits[0]
        self.assertEqual(audit["entity"], "AuditEvent")
        self.assertEqual(audit["kind"], "ATTENDANCE_SPACE_CREATED")
        self.assertEqual(audit["actorUserId"], user_id)

        user_by_sk = {item["SK"]: item for item in user_items}

        ownership = user_by_sk["OWNERSHIP"]
        self.assertEqual(ownership["entity"], "OwnershipClaim")
        self.assertEqual(ownership["spaceId"], space_id)

        idem = user_by_sk[f"IDEMPOTENCY#{idem_key}"]
        self.assertEqual(idem["entity"], "Idempotency")
        self.assertEqual(idem["requestId"], request_id)

    # ==================================================================
    # 2. forced rollback (mutation-acceptance target)
    # ==================================================================
    def test_forced_rollback_leaves_no_partial_writes(self):
        user_id = self._new_user()
        # Pre-seed a competing ownership claim. The transaction must fail
        # atomically on the third Put; any SPACE# item written before that
        # failure is an orphan.
        self.table.put_item(Item={
            "PK": f"USER#{user_id}",
            "SK": "OWNERSHIP",
            "entity": "OwnershipClaim",
            "spaceId": self._new_space(),
        })

        before = {(i["PK"], i["SK"]) for i in self._scan_prefix("SPACE#")}

        with self.assertRaises(DomainError) as ctx:
            self.repository.create_space(
                user_id,
                "Attempted",
                self._new_request(),
                self._new_idem_key(),
            )
        self.assertEqual(ctx.exception.code, "OWNERSHIP_EXISTS")
        self.assertEqual(ctx.exception.status, 409)

        after = {(i["PK"], i["SK"]) for i in self._scan_prefix("SPACE#")}
        orphans = after - before
        self.assertEqual(
            orphans,
            set(),
            f"orphan SPACE# records leaked from a cancelled transaction: {orphans}",
        )

    # ==================================================================
    # 3. idempotency
    # ==================================================================
    def test_idempotency_replay_returns_established_result(self):
        user_id = self._new_user()
        request_id = self._new_request()
        idem_key = self._new_idem_key()

        first = self.repository.create_space(
            user_id, "Course A", request_id, idem_key,
        )
        second = self.repository.create_space(
            user_id, "Ignored", request_id, idem_key,
        )

        self.assertFalse(first["idempotency"]["replayed"])
        self.assertTrue(second["idempotency"]["replayed"])
        self.assertEqual(first["space"]["spaceId"], second["space"]["spaceId"])

    def test_idempotency_conflict_raises(self):
        user_id = self._new_user()
        idem_key = self._new_idem_key()

        self.repository.create_space(
            user_id, "Course A", self._new_request(), idem_key,
        )
        with self.assertRaises(DomainError) as ctx:
            self.repository.create_space(
                user_id, "Course A", self._new_request(), idem_key,
            )
        self.assertEqual(ctx.exception.code, "IDEMPOTENCY_CONFLICT")
        self.assertEqual(ctx.exception.status, 409)

    # ==================================================================
    # 4. stale correction
    # ==================================================================
    def test_stale_correction_raises_correction_conflict(self):
        space_id = self._new_space()
        user_id = self._new_user()
        checkpoint_id = self._new_checkpoint()

        self.repository.record_fact(
            space_id, user_id, checkpoint_id, "CHECKED_IN", "present",
        )

        # Simulate a concurrent writer that changes occurredAt between
        # correct_fact's read and its conditional transaction. The direct
        # occurrence in correct_fact reads the current value, so we must
        # inject a stale read.
        real_get = self.repository.get

        def stale_get(pk, sk):
            item = real_get(pk, sk)
            if item and sk.startswith("FACT#"):
                self.table.update_item(
                    Key={"PK": pk, "SK": sk},
                    UpdateExpression="SET occurredAt = :new",
                    ExpressionAttributeValues={":new": "2000-01-01T00:00:00Z"},
                )
            return item

        with patch.object(self.repository, "get", side_effect=stale_get):
            with self.assertRaises(DomainError) as ctx:
                self.repository.correct_fact(
                    space_id,
                    self._new_user(),  # actor
                    user_id,
                    checkpoint_id,
                    "CHECKED_OUT",
                    "owner verified",
                    "manager note",
                )
        self.assertEqual(ctx.exception.code, "CORRECTION_CONFLICT")
        self.assertEqual(ctx.exception.status, 409)

    # ==================================================================
    # 5. audit immutability after correction
    # ==================================================================
    def test_audit_immutability_after_correction(self):
        space_id = self._new_space()
        user_id = self._new_user()
        checkpoint_id = self._new_checkpoint()

        self.repository.record_fact(
            space_id, user_id, checkpoint_id, "CHECKED_IN", "present",
        )

        result = self.repository.correct_fact(
            space_id,
            self._new_user(),  # actor
            user_id,
            checkpoint_id,
            "CHECKED_OUT",
            "owner verified",
            "manager only note",
        )

        audit = result["auditEvent"]
        self.assertEqual(audit["kind"], "ATTENDANCE_FACT_CORRECTED")
        self.assertEqual(audit["reason"], "owner verified")
        original = audit["affectedFact"]["original"]
        self.assertEqual(original["kind"], "CHECKED_IN")
        self.assertEqual(original["participantComment"], "present")
        replacement = audit["replacement"]
        self.assertEqual(replacement["kind"], "CHECKED_OUT")
        self.assertEqual(replacement["managerNote"], "manager only note")

        # The audit event survives as an immutable stored record.
        stored = self.table.get_item(
            Key={"PK": f"SPACE#{space_id}", "SK": audit["SK"]},
            ConsistentRead=True,
        ).get("Item")
        self.assertIsNotNone(stored)
        self.assertEqual(stored["kind"], "ATTENDANCE_FACT_CORRECTED")
        self.assertEqual(stored["reason"], "owner verified")

    # ==================================================================
    # 6. participant projection
    # ==================================================================
    def test_participant_projection_excludes_owner_correction_metadata(self):
        space_id = self._new_space()
        user_id = self._new_user()
        checkpoint_id = self._new_checkpoint()

        # Directly seed the fact with every private field, bypassing the
        # normal correction path (which pops these before writing).
        self.table.put_item(Item={
            "PK": f"SPACE#{space_id}",
            "SK": f"FACT#{user_id}#{checkpoint_id}",
            "entity": "AttendanceFact",
            "userId": user_id,
            "checkpointId": checkpoint_id,
            "kind": "CHECKED_OUT",
            "occurredAt": "2025-01-01T00:00:00Z",
            "participantComment": "present",
            "correctedAt": "2025-01-02T00:00:00Z",
            "correctedBy": "usr_private_owner_id_xx",
            "correctionEventId": "evt_private_identifier_xx",
            "managerNote": "owner-only private note",
        })

        view = self.repository.participant_view(space_id, user_id)
        self.assertEqual(len(view["facts"]), 1)
        fact = view["facts"][0]

        self.assertEqual(fact["kind"], "CHECKED_OUT")
        self.assertEqual(fact["participantComment"], "present")
        self.assertEqual(fact["correctedAt"], "2025-01-02T00:00:00Z")

        for excluded in (
            "managerNote",
            "correctedBy",
            "correctionEventId",
            "PK",
            "SK",
        ):
            self.assertNotIn(excluded, fact)

    # ==================================================================
    # 7. export projection
    # ==================================================================
    def test_export_projection_surfaces_both_notes(self):
        space_id = self._new_space()
        user_id = self._new_user()
        checkpoint_id = self._new_checkpoint()

        self.table.put_item(Item={
            "PK": f"SPACE#{space_id}",
            "SK": f"CHECKPOINT#{checkpoint_id}",
            "checkpointId": checkpoint_id,
            "kind": "CHECK_OUT",
            "lifecycle": "CLOSED",
        })
        self.table.put_item(Item={
            "PK": f"SPACE#{space_id}",
            "SK": f"FACT#{user_id}#{checkpoint_id}",
            "entity": "AttendanceFact",
            "userId": user_id,
            "checkpointId": checkpoint_id,
            "kind": "CHECKED_OUT",
            "occurredAt": "2025-01-01T00:00:00Z",
            "participantComment": "present from participant",
        })
        self.table.put_item(Item={
            "PK": f"SPACE#{space_id}",
            "SK": "AUDIT#2025-01-02T00:00:00Z#evt_correction_xx",
            "kind": "ATTENDANCE_FACT_CORRECTED",
            "affectedFact": {
                "userId": user_id,
                "checkpointId": checkpoint_id,
            },
            "replacement": {
                "kind": "CHECKED_OUT",
                "managerNote": "owner only note",
            },
        })

        rows = self.repository.export_rows(space_id)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["participantComment"], "present from participant")
        self.assertEqual(row["managerNote"], "owner only note")
        self.assertNotEqual(row["participantComment"], row["managerNote"])


if __name__ == "__main__":
    unittest.main()
