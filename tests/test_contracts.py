import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / 'contracts'

class ContractTests(unittest.TestCase):
    def load(self, name):
        return json.loads((CONTRACTS / name).read_text(encoding='utf-8'))

    def test_every_schema_has_draft_id_title(self):
        for path in sorted(CONTRACTS.glob('*.schema.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data['$schema'], 'https://json-schema.org/draft/2020-12/schema')
            self.assertTrue(data['$id'].endswith('/' + path.name))
            self.assertTrue(data['title'])

    def test_domain_vocabulary_is_exact(self):
        props = self.load('domain-v1.schema.json')['properties']
        self.assertEqual(props['roles']['const'], ['OWNER', 'PARTICIPANT'])
        self.assertEqual(props['checkpointKinds']['const'], ['CHECK_IN', 'PRESENCE_CHECK', 'CHECK_OUT'])
        self.assertEqual(props['checkpointLifecycle']['const'], ['DRAFT', 'SCHEDULED', 'OPEN', 'CLOSED', 'CANCELLED'])
        self.assertEqual(props['attendanceFacts']['const'], ['CHECKED_IN', 'PRESENCE_CONFIRMED', 'CHECKED_OUT'])
        self.assertEqual(props['displayStates']['const'], ['UPCOMING', 'AVAILABLE', 'COMPLETED', 'ABSENT', 'MISSED', 'CANCELLED'])

    def test_invitation_token_cannot_be_a_space_id(self):
        defs = self.load('identifiers-v1.schema.json')['$defs']
        self.assertIsNotNone(re.fullmatch(defs['spaceId']['pattern'], 'spc_1234567890abcdef'))
        self.assertIsNone(re.fullmatch(defs['invitationToken']['pattern'], 'spc_1234567890abcdef'))
        self.assertIsNotNone(re.fullmatch(defs['invitationToken']['pattern'], 'inv_' + 'a' * 32))

    def test_space_creation_requires_complete_atomic_result(self):
        schema = self.load('attendance-space-created-v1.schema.json')
        self.assertEqual(schema['required'], ['space', 'ownerMembership', 'ownershipClaim', 'auditEvent', 'idempotency'])
        self.assertEqual(schema['properties']['ownerMembership']['properties']['role']['const'], 'OWNER')
        self.assertIs(schema['properties']['ownershipClaim']['properties']['unique']['const'], True)

    def test_url_context_explicitly_denies_authority(self):
        schema = self.load('api-context-v1.schema.json')
        self.assertIn('Authorization requires', schema['description'])
        self.assertEqual(set(schema['properties']), {'space', 'checkpoint', 'invite'})

if __name__ == '__main__':
    unittest.main()
