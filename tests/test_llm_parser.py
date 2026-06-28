import unittest
from types import SimpleNamespace

import llm_parser


class FakeResponse:
    def __init__(self, content):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]


class FakeClient:
    def __init__(self, responses):
        self._responses = responses
        self._index = 0

    @property
    def chat(self):
        return SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, *args, **kwargs):
        response = FakeResponse(self._responses[self._index])
        self._index = min(self._index + 1, len(self._responses) - 1)
        return response


class LLMParserTests(unittest.TestCase):
    def test_invalid_json_from_llm_raises(self):
        llm_parser.client = FakeClient(["not-json"])

        with self.assertRaises(ValueError):
            llm_parser.extract_expense("coffee 200")

    def test_retry_on_invalid_json(self):
        llm_parser.client = FakeClient([
            "here is the result:\n{item_name: not valid}",
            '{"item_name": "creatine", "amount": 200, "category": "Health", "type": "expense"}'
        ])

        parsed = llm_parser.extract_expense("200 rupees creatine")

        self.assertEqual(parsed["item_name"], "creatine")
        self.assertEqual(parsed["amount"], 200)
        self.assertEqual(parsed["category"], "Health")
        self.assertEqual(parsed["type"], "expense")


if __name__ == "__main__":
    unittest.main()
