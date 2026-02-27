"""Unit tests for feedback router"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from routers import feedback
from services.feedback.collector import FeedbackCollector
import tempfile

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(feedback.router, prefix="/v1")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        feedback.feedback_collector = FeedbackCollector(f.name)
    feedback.metrics = {'feedback_received': 0, 'feedback_submitted': 0}
    
    yield app
    
    if os.path.exists(feedback.feedback_collector.storage_path):
        os.unlink(feedback.feedback_collector.storage_path)

@pytest.fixture
def client(app):
    return TestClient(app)

class TestFeedbackRouter:
    def test_submit_feedback(self, client):
        response = client.post("/v1/feedback", json={
            "query": "Test query",
            "rating": 1
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert "feedback" in data
    
    def test_get_stats(self, client):
        # Submit feedback
        client.post("/v1/feedback", json={"query": "Q1", "rating": 1})
        client.post("/v1/feedback", json={"query": "Q2", "rating": -1})
        
        response = client.get("/v1/feedback/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["positive"] == 1
        assert data["negative"] == 1
    
    def test_invalid_rating(self, client):
        response = client.post("/v1/feedback", json={
            "query": "Test",
            "rating": 5  # Invalid
        })
        assert response.status_code == 422  # Validation error
