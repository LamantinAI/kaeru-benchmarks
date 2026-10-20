import hashlib
import hmac
import unittest
from unittest.mock import Mock, patch

from receiver import receive, InvalidDelivery, DeliveryFailed, MAX_BODY_BYTES


class ReceiverTests(unittest.TestCase):
    body = b'{"id":"evt_1","type":"billing"}'
    keys = (b'old-key', b'new-key')

    def deliver(self, process, body=None, key=None, **kwargs):
        body = self.body if body is None else body
        signature = hmac.new(key or self.keys[0], body, hashlib.sha256).hexdigest()
        return receive(body, process, signature=signature, signing_keys=self.keys, **kwargs)

    def test_both_rotation_keys(self):
        for key in self.keys:
            process = Mock()
            self.assertTrue(self.deliver(process, key=key))
            process.assert_called_once_with({'id': 'evt_1', 'type': 'billing'})

    def test_rejects_untrusted_or_malformed_input(self):
        for body, signature in [(self.body, '0' * 64), (self.body, ''),
                                (self.body, None), (b'x' * (MAX_BODY_BYTES + 1), '0' * 64)]:
            process = Mock()
            with self.assertRaises(InvalidDelivery):
                receive(body, process, signature=signature, signing_keys=self.keys)
            process.assert_not_called()
        for body in [b'[]', b'{', b'\xff']:
            with self.assertRaises(InvalidDelivery):
                self.deliver(Mock(), body=body)

    def test_requires_key_collection(self):
        for keys in [[], b'single', [b'']]:
            with self.assertRaises(ValueError):
                receive(self.body, Mock(), signature='0' * 64, signing_keys=keys)

    @patch('receiver.time.sleep')
    def test_retry_then_success(self, sleep):
        process = Mock(side_effect=[RuntimeError(), None])
        self.assertTrue(self.deliver(process))
        self.assertEqual(process.call_count, 2)
        sleep.assert_called_once_with(0.01)

    @patch('receiver.time.sleep')
    def test_exhaustion_requires_redelivery(self, sleep):
        process = Mock(side_effect=RuntimeError('sensitive payload'))
        with self.assertLogs('receiver', level='WARNING') as logs:
            with self.assertRaises(DeliveryFailed):
                self.deliver(process)
        self.assertEqual(process.call_count, 3)
        self.assertNotIn('sensitive payload', ' '.join(logs.output))
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [0.01, 0.02])

    @patch('receiver.time.sleep')
    def test_failure_handoff(self, sleep):
        process = Mock(side_effect=RuntimeError())
        retain = Mock()
        self.assertFalse(self.deliver(process, on_failure=retain))
        retain.assert_called_once_with({'id': 'evt_1', 'type': 'billing'})
        retain.side_effect = OSError()
        with self.assertRaises(DeliveryFailed):
            self.deliver(process, on_failure=retain)

    @patch('receiver.time.sleep')
    def test_mutation_does_not_corrupt_retry(self, sleep):
        def process(event):
            self.assertEqual(event.pop('id'), 'evt_1')
            raise RuntimeError()
        retain = Mock()
        self.assertFalse(self.deliver(process, on_failure=retain))
        self.assertEqual(retain.call_args.args[0]['id'], 'evt_1')


if __name__ == '__main__':
    unittest.main()
