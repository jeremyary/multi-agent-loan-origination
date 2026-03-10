# This project was developed with assistance from AI tools.
"""Tests for the embedding provider abstraction."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.inference.embeddings import (
    LocalEmbeddingProvider,
    RemoteEmbeddingProvider,
    _build_provider,
    get_embedding_provider,
    reset_embedding_provider,
)


class TestLocalEmbeddingProvider:
    """Tests for in-process sentence-transformers provider."""

    @pytest.mark.asyncio
    async def test_returns_list_of_float_lists(self):
        """Embed returns list[list[float]] from numpy output."""
        provider = LocalEmbeddingProvider("test-model", dimensions=4)

        fake_model = MagicMock()
        fake_model.encode.return_value = np.array(
            [
                [0.1, 0.2, 0.3, 0.4],
                [0.5, 0.6, 0.7, 0.8],
            ]
        )
        provider._model = fake_model

        result = await provider.embed(["hello", "world"])

        assert len(result) == 2
        assert result[0] == pytest.approx([0.1, 0.2, 0.3, 0.4])
        assert result[1] == pytest.approx([0.5, 0.6, 0.7, 0.8])
        fake_model.encode.assert_called_once_with(
            ["hello", "world"],
            normalize_embeddings=True,
        )

    @pytest.mark.asyncio
    async def test_lazy_loads_model(self):
        """Model is not loaded until first embed call."""
        provider = LocalEmbeddingProvider("test-model")
        assert provider._model is None

        fake_model = MagicMock()
        fake_model.encode.return_value = np.array([[0.1] * 768])

        with patch(
            "src.inference.embeddings.SentenceTransformer", return_value=fake_model
        ) as mock_cls:
            result = await provider.embed(["test"])
            mock_cls.assert_called_once_with("test-model", trust_remote_code=True)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_caches_model_after_first_load(self):
        """Subsequent calls reuse the cached model instance."""
        provider = LocalEmbeddingProvider("test-model")

        fake_model = MagicMock()
        fake_model.encode.return_value = np.array([[0.1] * 768])

        with patch(
            "src.inference.embeddings.SentenceTransformer", return_value=fake_model
        ) as mock_cls:
            await provider.embed(["first"])
            await provider.embed(["second"])
            # Only constructed once
            assert mock_cls.call_count == 1
            assert fake_model.encode.call_count == 2


class TestRemoteEmbeddingProvider:
    """Tests for OpenAI-compatible remote provider."""

    @pytest.mark.asyncio
    async def test_delegates_to_openai_client(self):
        """Embed call delegates to AsyncOpenAI.embeddings.create."""
        with patch("openai.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client

            provider = RemoteEmbeddingProvider(
                endpoint="http://localhost:8000/v1",
                model_name="test-embed",
                api_key="test-key",
            )

            mock_item_1 = MagicMock()
            mock_item_1.embedding = [0.1, 0.2, 0.3]
            mock_item_2 = MagicMock()
            mock_item_2.embedding = [0.4, 0.5, 0.6]
            mock_response = MagicMock()
            mock_response.data = [mock_item_1, mock_item_2]
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await provider.embed(["hello", "world"])

            assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            mock_client.embeddings.create.assert_called_once_with(
                model="test-embed",
                input=["hello", "world"],
            )


class TestProviderFactory:
    """Tests for provider construction from config."""

    def test_builds_local_provider(self, monkeypatch):
        """provider=local creates LocalEmbeddingProvider."""
        monkeypatch.setattr(
            "src.inference.embeddings.get_model_config",
            lambda tier: {
                "provider": "local",
                "model_name": "nomic-ai/nomic-embed-text-v1.5",
                "dimensions": 768,
            },
        )
        provider = _build_provider()
        assert isinstance(provider, LocalEmbeddingProvider)
        assert provider._model_name == "nomic-ai/nomic-embed-text-v1.5"
        assert provider._dimensions == 768

    def test_builds_remote_provider(self, monkeypatch):
        """provider=openai_compatible creates RemoteEmbeddingProvider."""
        monkeypatch.setattr(
            "src.inference.embeddings.get_model_config",
            lambda tier: {
                "provider": "openai_compatible",
                "model_name": "text-embedding-3-small",
                "endpoint": "https://api.openai.com/v1",
                "api_key": "sk-test",
            },
        )
        provider = _build_provider()
        assert isinstance(provider, RemoteEmbeddingProvider)

    def test_defaults_to_remote_when_provider_unset(self, monkeypatch):
        """Missing provider key defaults to openai_compatible."""
        monkeypatch.setattr(
            "src.inference.embeddings.get_model_config",
            lambda tier: {
                "model_name": "text-embedding-3-small",
                "endpoint": "https://api.openai.com/v1",
            },
        )
        provider = _build_provider()
        assert isinstance(provider, RemoteEmbeddingProvider)


class TestSingletonManagement:
    """Tests for provider caching and reset."""

    def setup_method(self):
        reset_embedding_provider()

    def teardown_method(self):
        reset_embedding_provider()

    def test_caches_provider_instance(self, monkeypatch):
        """get_embedding_provider returns the same instance on repeated calls."""
        monkeypatch.setattr(
            "src.inference.embeddings.get_model_config",
            lambda tier: {
                "provider": "local",
                "model_name": "test-model",
                "dimensions": 768,
            },
        )
        p1 = get_embedding_provider()
        p2 = get_embedding_provider()
        assert p1 is p2

    def test_reset_clears_cache(self, monkeypatch):
        """reset_embedding_provider forces a new instance on next call."""
        call_count = 0

        def fake_config(tier):
            nonlocal call_count
            call_count += 1
            return {"provider": "local", "model_name": "test-model", "dimensions": 768}

        monkeypatch.setattr("src.inference.embeddings.get_model_config", fake_config)
        get_embedding_provider()
        assert call_count == 1

        reset_embedding_provider()
        get_embedding_provider()
        assert call_count == 2
