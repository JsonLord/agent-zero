import unittest
from unittest.mock import patch, MagicMock
from models import LocalSentenceTransformerWrapper, get_embedding_model

class TestLocalSentenceTransformerWrapper(unittest.TestCase):
    def test_local_sentence_transformer_wrapper_init(self):
        with patch("models.SentenceTransformer") as mock_st:
            mock_st_instance = MagicMock()
            mock_st.return_value = mock_st_instance

            wrapper = LocalSentenceTransformerWrapper(
                provider="huggingface",
                model="sentence-transformers/all-MiniLM-L6-v2",
                device="cpu"
            )

            # Check SentenceTransformer was called with model_kwargs containing low_cpu_mem_usage=False
            mock_st.assert_called_once()
            call_kwargs = mock_st.call_args[1]
            self.assertEqual(call_kwargs.get("device"), "cpu")
            self.assertEqual(call_kwargs.get("model_kwargs"), {"low_cpu_mem_usage": False})

    def test_get_embedding_model_sentence_transformer(self):
        with patch("models.SentenceTransformer") as mock_st:
            mock_st_instance = MagicMock()
            mock_st.return_value = mock_st_instance

            model = get_embedding_model("huggingface", "sentence-transformers/all-MiniLM-L6-v2")
            self.assertIsInstance(model, LocalSentenceTransformerWrapper)

if __name__ == "__main__":
    unittest.main()
