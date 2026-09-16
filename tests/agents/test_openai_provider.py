import os
import unittest
from unittest.mock import patch

from agents.providers.openai_provider import OpenAIProvider


class OpenAIProviderTests(unittest.TestCase):
    def test_default_model_is_configurable_without_legacy_ai_helper(self):
        provider = OpenAIProvider()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_MODEL", None)
            self.assertEqual(provider._model(), "gpt-5.6")
        with patch.dict(os.environ, {"OPENAI_MODEL": "custom-model"}):
            self.assertEqual(provider._model(), "custom-model")

    def test_generate_uses_responses_api_directly(self):
        provider = OpenAIProvider()
        response = {"output_text": "Привет из SØNA"}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "gpt-5.6"}), \
             patch.object(provider, "_request", return_value=response) as request:
            result = provider.generate(system="system", messages=[{"role": "user", "content": [{"type": "input_text", "text": "hello"}]}])

        self.assertEqual(result, "Привет из SØNA")
        request.assert_called_once()
        endpoint, api_key, payload = request.call_args.args
        self.assertTrue(endpoint.endswith("/v1/responses"))
        self.assertEqual(api_key, "test-key")
        self.assertEqual(payload["model"], "gpt-5.6")
        self.assertEqual(payload["store"], False)

    def test_generate_requires_api_key(self):
        provider = OpenAIProvider()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                provider.generate(system="system", messages=[])


if __name__ == "__main__":
    unittest.main()
