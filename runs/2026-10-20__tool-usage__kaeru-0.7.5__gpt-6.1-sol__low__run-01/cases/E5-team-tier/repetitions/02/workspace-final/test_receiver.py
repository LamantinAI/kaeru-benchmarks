import hmac
import unittest
from unittest.mock import Mock, patch

from receiver import DeliveryFailed, InvalidDelivery, receive, receive_signed


class ReceiverTests(unittest.TestCase):
    def signed(self, body=b'{"id":"event-1"}', key=b'new', **kwargs):
        process = kwargs.pop('process', Mock())
        signature = hmac.digest(key, body, 'sha256').hex()
        return receive_signed(body, signature, process,
                              signing_keys=[b'new', b'old'], **kwargs)

    def test_both_rotation_keys(self):
        for key in (b'new', b'old'):
            self.assertTrue(self.signed(key=key))

    def test_invalid_signature_never_processes(self):
        process = Mock()
        for signature in ('', 'z' * 64, '0' * 64):
            with self.assertRaises(InvalidDelivery):
                receive_signed(b'{}', signature, process, signing_keys=[b'new'])
        process.assert_not_called()

    def test_tampering_rejected(self):
        with self.assertRaises(InvalidDelivery):
            receive_signed(b'{ }', hmac.digest(b'new', b'{}', 'sha256').hex(),
                           Mock(), signing_keys=[b'new'])

    def test_invalid_body(self):
        for body in (b'[]', b'null', b'{', b'\xff', b'x' * (1024 * 1024 + 1)):
            with self.assertRaises(InvalidDelivery):
                self.signed(body=body)

    def test_missing_keys_fail_closed(self):
        with self.assertRaises(ValueError):
            receive_signed(b'{}', '0' * 64, Mock(), signing_keys=[])

    @patch('receiver.time.sleep')
    def test_transient_failure_and_mutation(self, sleep):
        seen = []
        def process(event):
            seen.append(event['id'])
            event['id'] = 'changed'
            if len(seen) < 3:
                raise RuntimeError('temporary')
        event = {'id': 'original'}
        self.assertTrue(receive(event, process))
        self.assertEqual(seen, ['original'] * 3)
        self.assertEqual(event, {'id': 'original'})
        self.assertEqual(sleep.call_count, 2)

    @patch('receiver.time.sleep')
    def test_exhaustion_is_retryable_and_logs_no_exception_details(self, sleep):
        process = Mock(side_effect=RuntimeError('sensitive payload'))
        with self.assertLogs('receiver', level='WARNING') as logs:
            with self.assertRaises(DeliveryFailed):
                receive({}, process)
        self.assertEqual(process.call_count, 3)
        self.assertNotIn('sensitive payload', '\n'.join(logs.output))


if __name__ == '__main__':
    unittest.main()
