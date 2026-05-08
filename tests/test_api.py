"""
Unit tests for AI Batch Inference API
Tests validation, error handling, and response formats
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from api.main import app

# Test client
client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check_basic(self):
        """Test basic health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
    
    def test_detailed_health_check_success(self):
        """Test detailed health check when Redis is available"""
        # redis_client is already mocked globally in conftest
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_detailed_health_check_failure(self):
        """Test detailed health check when Redis is unavailable"""
        with patch('shared.queue.redis_client') as mock_redis:
            mock_redis.ping.side_effect = Exception("Redis unavailable")
            response = client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert "unavailable" in data["detail"].lower()


class TestSubmitJob:
    """Test job submission endpoint"""
    
    def test_submit_job_valid(self):
        """Test valid job submission"""
        with patch('api.main.enqueue_job', return_value='test-job-id'):
            response = client.post("/submit-job", json={
                "texts": ["This is great!", "This is terrible!"]
            })
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "test-job-id"
            assert data["status"] == "queued"
    
    def test_submit_job_single_text(self):
        """Test submission with single text"""
        with patch('api.main.enqueue_job', return_value='test-job-id'):
            response = client.post("/submit-job", json={
                "texts": ["Just one text"]
            })
            assert response.status_code == 200
            assert response.json()["job_id"] == "test-job-id"
    
    def test_submit_job_empty_texts(self):
        """Test submission with empty texts list"""
        response = client.post("/submit-job", json={"texts": []})
        assert response.status_code == 422  # Validation error
    
    def test_submit_job_empty_text_item(self):
        """Test submission with empty text in list"""
        response = client.post("/submit-job", json={
            "texts": ["Valid text", ""]
        })
        assert response.status_code == 422  # Validation error
    
    def test_submit_job_whitespace_only(self):
        """Test submission with whitespace-only text"""
        response = client.post("/submit-job", json={
            "texts": ["   "]
        })
        assert response.status_code == 422  # Validation error
    
    def test_submit_job_too_many_texts(self):
        """Test submission exceeding max batch size"""
        from shared.config import config
        texts = ["text"] * (config.MAX_BATCH_SIZE + 1)
        response = client.post("/submit-job", json={"texts": texts})
        assert response.status_code == 422  # Validation error
    
    def test_submit_job_text_too_long(self):
        """Test submission with text exceeding max length"""
        from shared.config import config
        long_text = "x" * (config.MAX_TEXT_LENGTH + 1)
        response = client.post("/submit-job", json={
            "texts": [long_text]
        })
        assert response.status_code == 422  # Validation error
    
    def test_submit_job_total_size_exceeds_limit(self):
        """Test submission where total size exceeds 100KB"""
        with patch('api.main.enqueue_job'):
            # Create many texts that sum to > 100KB (each < MAX_TEXT_LENGTH of 5000)
            # 21 texts × 5000 chars = 105KB
            texts = ["x" * 5000 for _ in range(21)]
            response = client.post("/submit-job", json={"texts": texts})
            assert response.status_code == 413
            assert "exceeds 100KB" in response.json()["detail"]
    
    def test_submit_job_non_string_text(self):
        """Test submission with non-string in texts"""
        response = client.post("/submit-job", json={
            "texts": ["valid", 123, "also valid"]
        })
        assert response.status_code == 422  # Validation error


class TestFetchResult:
    """Test result retrieval endpoint"""
    
    def test_fetch_result_success(self):
        """Test successful result retrieval"""
        mock_result = [
            {"label": "POSITIVE", "score": 0.9},
            {"label": "NEGATIVE", "score": 0.8}
        ]
        with patch('api.main.get_result', return_value=mock_result):
            response = client.get("/result/test-job-id")
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "test-job-id"
            assert data["result"] == mock_result
    
    def test_fetch_result_not_found(self):
        """Test result retrieval for non-existent job"""
        with patch('api.main.get_result', return_value=None):
            response = client.get("/result/nonexistent-id")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_fetch_result_with_special_chars_in_id(self):
        """Test result retrieval with special characters in ID"""
        with patch('api.main.get_result', return_value=[]):
            response = client.get("/result/test-id-with-dashes")
            assert response.status_code == 200


class TestJobStatus:
    """Test job status endpoint"""
    
    def test_job_status_queued(self):
        """Test status retrieval for queued job"""
        with patch('api.main.get_status', return_value='QUEUED'):
            response = client.get("/status/test-job-id")
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "test-job-id"
            assert data["status"] == "QUEUED"
    
    def test_job_status_running(self):
        """Test status retrieval for running job"""
        with patch('api.main.get_status', return_value='RUNNING'):
            response = client.get("/status/test-job-id")
            assert response.status_code == 200
            assert response.json()["status"] == "RUNNING"
    
    def test_job_status_completed(self):
        """Test status retrieval for completed job"""
        with patch('api.main.get_status', return_value='COMPLETED'):
            response = client.get("/status/test-job-id")
            assert response.status_code == 200
            assert response.json()["status"] == "COMPLETED"
    
    def test_job_status_failed(self):
        """Test status retrieval for failed job"""
        with patch('api.main.get_status', return_value='FAILED'):
            response = client.get("/status/test-job-id")
            assert response.status_code == 200
            assert response.json()["status"] == "FAILED"
    
    def test_job_status_not_found(self):
        """Test status retrieval for non-existent job"""
        with patch('api.main.get_status', return_value=None):
            response = client.get("/status/nonexistent-id")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint"""
    
    def test_metrics_from_localhost(self):
        """Test metrics endpoint access from localhost"""
        with patch('api.main.get_queue_length', return_value=5):
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "job_queue_length" in response.text
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
    
    def test_metrics_content_format(self):
        """Test metrics are in Prometheus text format"""
        with patch('api.main.get_queue_length', return_value=10):
            response = client.get("/metrics")
            assert response.status_code == 200
            # Should contain Prometheus format lines
            assert "# HELP" in response.text or "# TYPE" in response.text or "}" in response.text


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_submit_job_internal_error(self):
        """Test handling of internal errors during job submission"""
        with patch('api.main.enqueue_job', side_effect=Exception("Database error")):
            response = client.post("/submit-job", json={
                "texts": ["test text"]
            })
            assert response.status_code == 500
            assert "internal" in response.json()["detail"].lower()
    
    def test_malformed_json(self):
        """Test handling of malformed JSON"""
        response = client.post(
            "/submit-job",
            content="not json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_missing_texts_field(self):
        """Test submission without texts field"""
        response = client.post("/submit-job", json={})
        assert response.status_code == 422  # Validation error
    
    def test_wrong_type_for_texts(self):
        """Test submission with wrong type for texts"""
        response = client.post("/submit-job", json={
            "texts": "not a list"
        })
        assert response.status_code == 422  # Validation error


class TestResponseModels:
    """Test response model compliance"""
    
    def test_job_response_structure(self):
        """Test JobResponse has correct structure"""
        with patch('api.main.enqueue_job', return_value='test-id'):
            response = client.post("/submit-job", json={"texts": ["test"]})
            data = response.json()
            assert "job_id" in data
            assert "status" in data
            assert len(data) == 2  # Only these two fields
    
    def test_result_response_structure(self):
        """Test ResultResponse has correct structure"""
        with patch('api.main.get_result', return_value=[]):
            response = client.get("/result/test-id")
            data = response.json()
            assert "job_id" in data
            assert "result" in data
            assert len(data) == 2  # Only these two fields
    
    def test_status_response_structure(self):
        """Test StatusResponse has correct structure"""
        with patch('api.main.get_status', return_value='QUEUED'):
            response = client.get("/status/test-id")
            data = response.json()
            assert "job_id" in data
            assert "status" in data
            assert len(data) == 2  # Only these two fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
