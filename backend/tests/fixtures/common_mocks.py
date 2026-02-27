"""
Reusable test fixtures for mocking common dependencies

Use these fixtures in your tests to avoid repetitive mock setup.
"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch


# ═══════════════════════════════════════════════════════════════
# LLM SERVICE MOCKS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_llm_service():
    """Mock LLM service with generate method"""
    mock = Mock()
    mock.generate = Mock(return_value="Generated response")
    mock.is_available = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_bedrock_client():
    """Mock AWS Bedrock client"""
    with patch('boto3.client') as mock:
        client = Mock()
        client.invoke_model = Mock(return_value={
            'body': Mock(read=Mock(return_value=b'{"completion": "test"}'))
        })
        mock.return_value = client
        yield client


# ═══════════════════════════════════════════════════════════════
# WEB SEARCH MOCKS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_web_search_service():
    """Mock web search service"""
    mock = Mock()
    mock.search = Mock(return_value=[
        {'title': 'Test', 'url': 'http://test.com', 'snippet': 'Test snippet'}
    ])
    return mock


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for web scraping"""
    with patch('requests.get') as mock:
        response = Mock()
        response.status_code = 200
        response.text = '<html><body>Test content</body></html>'
        mock.return_value = response
        yield mock


# ═══════════════════════════════════════════════════════════════
# FAISS / RAG MOCKS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_embedding_model():
    """Mock sentence transformer embedding model"""
    import numpy as np
    mock = Mock()
    mock.encode = Mock(return_value=np.random.rand(2, 384).astype('float32'))
    mock.get_sentence_embedding_dimension = Mock(return_value=384)
    return mock


@pytest.fixture
def mock_faiss_index():
    """Mock FAISS index"""
    import faiss
    index = faiss.IndexFlatL2(384)
    return index


@pytest.fixture
def mock_rag_engine():
    """Mock RAG engine"""
    mock = Mock()
    mock.search = Mock(return_value=[
        {'text': 'Test doc', 'metadata': {}, 'score': 0.9}
    ])
    mock.load_index = Mock(return_value=True)
    mock.save_index = Mock()
    return mock


# ═══════════════════════════════════════════════════════════════
# CACHE MOCKS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    mock = Mock()
    mock.get = Mock(return_value=None)
    mock.set = Mock(return_value=True)
    mock.delete = Mock(return_value=1)
    mock.ping = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_cache_service():
    """Mock cache service"""
    mock = Mock()
    mock.enabled = True
    mock.get = Mock(return_value=None)
    mock.set = Mock()
    return mock


# ═══════════════════════════════════════════════════════════════
# FASTAPI MOCKS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_fastapi_app():
    """Mock FastAPI app with test client"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    client = TestClient(app)
    return app, client


# ═══════════════════════════════════════════════════════════════
# ASYNC MOCKS
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_async_llm():
    """Mock async LLM service"""
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value="Async response")
    return mock


@pytest.fixture
def mock_async_web_search():
    """Mock async web search"""
    mock = AsyncMock()
    mock.search = AsyncMock(return_value=[
        {'title': 'Test', 'url': 'http://test.com'}
    ])
    return mock


# ═══════════════════════════════════════════════════════════════
# USAGE EXAMPLES
# ═══════════════════════════════════════════════════════════════

"""
Example test using fixtures:

def test_my_function(mock_llm_service, mock_web_search_service):
    # Fixtures are automatically injected
    result = my_function(mock_llm_service, mock_web_search_service)
    assert result is not None
    mock_llm_service.generate.assert_called_once()
"""
