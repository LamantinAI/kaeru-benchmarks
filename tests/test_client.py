"""Protocol boundaries: lossless results, exact continuations, no hidden retries."""

from copy import deepcopy
import json
import unittest

from runner import OperationFailed, ProtocolError, R2Client


INPUT = {
    "type": "object",
    "properties": {
        "initiatives": {"type": "array", "items": {"type": "string"}},
        "text": {"type": "string"}, "prefix": {"type": "boolean"},
        "cursor": {"type": "string"}, "budget_chars": {"type": "integer"},
    },
    "required": ["initiatives"], "additionalProperties": False,
}
OUTPUT = {
    "type": "object",
    "required": ["api_version", "operation", "state", "data", "issues"],
    "properties": {
        "api_version": {"type": "integer"}, "operation": {"type": "string"},
        "state": {"enum": ["ok", "applied", "unchanged", "partial", "rejected"]},
        "data": {"type": "object"}, "issues": {"type": "array"},
    },
}
ARGS = {"initiatives": ["sample"], "text": "capture", "prefix": True}


def tool(name="search", *, read_only=True, output=True):
    result = {
        "name": name, "description": "Synthetic tool.", "inputSchema": deepcopy(INPUT),
        "annotations": {"readOnlyHint": read_only},
    }
    if output:
        result["outputSchema"] = deepcopy(OUTPUT)
    return result


def result(*, state="ok", operation="search", continuation=None, complete=True):
    envelope = {
        "api_version": 1, "operation": operation, "state": state,
        "request_id": None, "replayed": False,
        "data": {"hits": [{"id": "synthetic-record"}], "total": 1}, "issues": [],
        "coverage": {"initiatives": ["sample"], "complete": complete,
                     "rules_complete": True, "omitted": []},
    }
    if continuation is not None:
        envelope["continuation"] = deepcopy(continuation)
    return {
        "content": [{"type": "text", "text": json.dumps(envelope)}],
        "structuredContent": envelope, "isError": state in {"partial", "rejected"},
    }


class Peer:
    def __init__(self, calls=(), listings=None):
        self.calls = list(calls)
        self.listings = list(listings or [{"tools": [tool()]}])
        self.requests = []

    def request(self, method, params):
        self.requests.append((method, deepcopy(params)))
        queue = self.listings if method == "tools/list" else self.calls
        if not queue:
            raise AssertionError("unexpected extra request")
        return deepcopy(queue.pop(0))

    def client(self):
        client = R2Client(self.request)
        client.discover()
        return client


class ClientTests(unittest.TestCase):
    def test_discovery_uses_live_paginated_catalogue_and_keeps_definitions(self):
        cloud = tool("cloud_recall", output=False)
        peer = Peer(listings=[{"tools": [tool()], "nextCursor": "catalogue-2"},
                              {"tools": [cloud]}])
        client = R2Client(peer.request)
        catalogue = client.discover()
        self.assertEqual(set(catalogue), {"search", "cloud_recall"})
        self.assertEqual(peer.requests[-1], ("tools/list", {"cursor": "catalogue-2"}))
        catalogue["search"]["description"] = "changed"
        self.assertEqual(client.tools["search"]["description"], "Synthetic tool.")

    def test_discovery_rejects_duplicate_names_and_cursor_loops(self):
        for second in ({"tools": [tool()]}, {"tools": [], "nextCursor": "same"}):
            with self.subTest(second=second):
                peer = Peer(listings=[{"tools": [tool()], "nextCursor": "same"}, second])
                with self.assertRaises(ProtocolError):
                    R2Client(peer.request).discover()

    def test_invalid_schema_and_bounded_catalogue(self):
        invalid = tool()
        invalid["inputSchema"] = {"type": "not-a-json-schema-type"}
        for listing in ({"tools": [invalid]}, {"tools": [tool()], "nextCursor": "more"}):
            with self.subTest(listing=listing):
                peer = Peer(listings=[listing])
                with self.assertRaises(ProtocolError):
                    R2Client(peer.request).discover(max_pages=1)

    def test_one_call_preserves_the_exact_result_and_does_not_expand_pages(self):
        continuation = {"cursor": "page-2", "next_arguments": {**ARGS, "cursor": "page-2"}}
        raw = result(continuation=continuation, complete=False)
        peer = Peer([raw])
        reply = peer.client().call("search", ARGS)
        self.assertEqual(reply.raw, raw)
        self.assertEqual(reply.envelope, raw["structuredContent"])
        self.assertTrue(reply.successful)
        self.assertEqual(len(peer.requests), 2)

    def test_legacy_name_and_arguments_are_rejected_before_sending(self):
        peer = Peer()
        client = peer.client()
        for operation, args in (("awake", ARGS), ("search", {"query": "capture*"})):
            with self.subTest(operation=operation):
                with self.assertRaises(ProtocolError):
                    client.call(operation, args)
        self.assertEqual(len(peer.requests), 1)

    def test_partial_mutation_keeps_committed_ids_and_failed_steps_without_retry(self):
        raw = result(state="partial", operation="note")
        raw["structuredContent"]["data"] = {
            "primary": {"id": "committed"}, "failed_steps": [{"step": "share"}],
        }
        raw["content"][0]["text"] = json.dumps(raw["structuredContent"])
        peer = Peer([raw], listings=[{"tools": [tool("note", read_only=False)]}])
        reply = peer.client().call("note", ARGS)
        self.assertFalse(reply.successful)
        self.assertEqual(reply.envelope["data"]["primary"]["id"], "committed")
        self.assertEqual(len(peer.requests), 2)

    def test_json_text_fallback_and_cloud_text_are_distinct(self):
        local = result()
        local.pop("structuredContent")
        self.assertEqual(Peer([local]).client().call("search", ARGS).envelope["state"], "ok")
        cloud = {"content": [{"type": "text", "text": "No shared records."}]}
        peer = Peer([cloud], listings=[{"tools": [tool("cloud_recall", output=False)]}])
        reply = peer.client().call("cloud_recall", ARGS)
        self.assertIsNone(reply.envelope)
        self.assertEqual(reply.raw, cloud)
        self.assertTrue(reply.successful)

    def test_mismatched_or_malformed_local_results_fail(self):
        wrong_text = result()
        wrong_text["content"][0]["text"] = "{}"
        missing_data = result()
        del missing_data["structuredContent"]["data"]
        missing_data["content"][0]["text"] = json.dumps(missing_data["structuredContent"])
        wrong_version = result()
        wrong_version["structuredContent"]["api_version"] = 2
        wrong_version["content"][0]["text"] = json.dumps(wrong_version["structuredContent"])
        for raw in (wrong_text, missing_data, wrong_version, result(operation="context"),
                    {"content": [{"type": "text", "text": "old prose result"}]}):
            with self.subTest(raw=raw):
                with self.assertRaises(ProtocolError):
                    Peer([raw]).client().call("search", ARGS)

    def test_read_pages_uses_exact_next_arguments_and_preserves_coverage(self):
        next_args = {**ARGS, "cursor": "page-2", "budget_chars": 12000}
        first = result(continuation={"cursor": "page-2", "next_arguments": next_args},
                       complete=False)
        last = result(complete=False)
        last["structuredContent"]["coverage"]["omitted"] = [
            {"section": "candidate_scan", "count": 1, "reason": "candidate_cap"}
        ]
        last["content"][0]["text"] = json.dumps(last["structuredContent"])
        original = deepcopy(ARGS)
        peer = Peer([first, last])
        pages = peer.client().read_pages("search", ARGS)
        self.assertEqual(len(pages), 2)
        self.assertEqual(peer.requests[-1][1]["arguments"], next_args)
        self.assertFalse(pages[-1].envelope["coverage"]["complete"])
        self.assertEqual(pages[0].raw, first)
        self.assertEqual(ARGS, original)

    def test_cursor_stale_preserves_evidence_and_does_not_restart(self):
        first = result(continuation={"cursor": "page-2", "next_arguments": {**ARGS, "cursor": "page-2"}})
        rejected = result(state="rejected")
        rejected["structuredContent"]["issues"] = [{"code": "CURSOR_STALE"}]
        rejected["content"][0]["text"] = json.dumps(rejected["structuredContent"])
        peer = Peer([first, rejected])
        with self.assertRaises(OperationFailed) as caught:
            peer.client().read_pages("search", ARGS)
        self.assertEqual(caught.exception.reply.envelope["issues"][0]["code"], "CURSOR_STALE")
        self.assertEqual(len(caught.exception.previous_pages), 1)
        self.assertEqual(len(peer.requests), 3)

    def test_paging_rejects_mutations_clouds_and_invalid_page_limit(self):
        for definition in (tool("note", read_only=False), tool("cloud_recall", output=False)):
            peer = Peer(listings=[{"tools": [definition]}])
            with self.subTest(name=definition["name"]):
                with self.assertRaises(ProtocolError):
                    peer.client().read_pages(definition["name"], ARGS)
                self.assertEqual(len(peer.requests), 1)
        with self.assertRaises(ValueError):
            Peer().client().read_pages("search", ARGS, max_pages=0)

    def test_paging_stops_on_loops_malformed_continuations_and_limit(self):
        good = {"cursor": "same", "next_arguments": {**ARGS, "cursor": "same"}}
        malformed = {"cursor": "same", "next_arguments": ARGS}
        cases = [([result(continuation=good)] * 2, 128),
                 ([result(continuation=malformed)], 128),
                 ([result(continuation=good)], 1)]
        for replies, limit in cases:
            with self.subTest(limit=limit, replies=len(replies)):
                peer = Peer(replies)
                with self.assertRaises(ProtocolError):
                    peer.client().read_pages("search", ARGS, max_pages=limit)


if __name__ == "__main__":
    unittest.main()
