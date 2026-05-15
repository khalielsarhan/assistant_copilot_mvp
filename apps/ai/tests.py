from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from apps.ai.ollama import generate


class OllamaTests(SimpleTestCase):
    @override_settings(OLLAMA_BASE_URL="http://ollama.local", OLLAMA_MODEL="qwen-test")
    @patch("apps.ai.ollama.requests.post")
    def test_generate_sends_chat_payload(self, mock_post):
        response = Mock()
        response.json.return_value = {"message": {"content": "Summary"}}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        result = generate("Summarize this")

        self.assertEqual(result, "Summary")
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["model"], "qwen-test")
        self.assertEqual(kwargs["json"]["messages"][1]["content"], "Summarize this")

    @override_settings(OLLAMA_BASE_URL="http://ollama.local", OLLAMA_MODEL="qwen-test")
    @patch("apps.ai.ollama.requests.post", side_effect=Exception("offline"))
    def test_generate_returns_readable_fallback_when_unavailable(self, _mock_post):
        result = generate("Summarize this")

        self.assertEqual(result, "AI unavailable: offline")
