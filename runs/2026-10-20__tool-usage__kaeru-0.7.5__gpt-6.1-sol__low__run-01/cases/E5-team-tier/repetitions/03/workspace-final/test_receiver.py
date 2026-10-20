import hashlib
import hmac
import unittest
from unittest.mock import Mock, patch

from receiver import DeliveryFailed, InvalidDelivery, MAX_BODY_BYTES, receive


class ReceiverTests(unittest.TestCase):
    body = b'{"id":"evt_1"}'
    keys = (b'old-test-key', b'new-test-key')

    def deliver(self, process, body=None, key=None, signature=None, keys=None):
        body = self.body if body is None else body
        signature = signature if signature is not None else hmac.new(
            key or self.keys[0], body, hashlib.sha256).hexdigest()
        return receive(body, process, signature=signature,
                       signing_keys=self.keys if keys is None else keys)

    def test_both_rotation_keys_are_accepted(self):
        for key in self.keys:
            process = Mock()
            self.assertTrue(self.deliver(process, key=key))
            process.assert_called_once_with({'id': 'evt_1'})

    def test_invalid_auth_never_processes(self):
        for signature in ('', '0' * 64, 'é' * 64, 'x' * 64):
            process = Mock()
            with self.assertRaises(InvalidDelivery):
                self.deliver(process, signature=signature)
            process.assert_not_called()
        with self.assertRaises(InvalidDelivery):
            self.deliver(Mock(), key=b'retired-key')

    def test_tampered_body_rejected(self):
        signature = hmac.new(self.keys[0], self.body, hashlib.sha256).hexdigest()
        with self.assertRaises(InvalidDelivery):
            self.deliver(Mock(), body=self.body + b' ', signature=signature)

    def test_bad_payloads_rejected(self):
        for body in (b'[]', b'null', b'{', b'\xff', b'x' * (MAX_BODY_BYTES + 1)):
            process = Mock()
            with self.assertRaises(InvalidDelivery):
                self.deliver(process, body=body)
            process.assert_not_called()

    def test_missing_keys_fail_closed(self):
        with self.assertRaises(ValueError):
            self.deliver(Mock(), keys=())

    @patch('receiver.time.sleep')
    def test_transient_failure_retries_with_backoff(self, sleep):
        process = Mock(side_effect=[RuntimeError(), RuntimeError(), None])
        self.assertTrue(self.deliver(process))
        self.assertEqual(process.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [.01, .02])

    @patch('receiver.time.sleep')
    def test_exhaustion_is_visible_without_payload_logging(self, sleep):
        process = Mock(side_effect=RuntimeError('private billing data'))
        with self.assertLogs('receiver') as logs:
            with self.assertRaises(DeliveryFailed):
                self.deliver(process)
        self.assertEqual(process.call_count, 3)
        self.assertNotIn('private billing data', str(logs.output))

    @patch('receiver.time.sleep')
    def test_retry_restores_mutated_payload(self, sleep):
        seen = []
        def process(event):
            seen.append(event['id'])
            event.clear()
            if len(seen) == 1:
                raise RuntimeError()
        self.assertTrue(self.deliver(process))
        self.assertEqual(seen, ['evt_1', 'evt_1'])


if __name__ == '__main__':
    unittest.main()
