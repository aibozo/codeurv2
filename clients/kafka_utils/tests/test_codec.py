import pytest
import sys
from unittest.mock import Mock

# Mock dependencies before importing
sys.modules['prometheus_client'] = Mock()
sys.modules['confluent_kafka'] = Mock()
sys.modules['google.protobuf.message'] = Mock()

def test_codec_encode():
    from clients.kafka_utils import codec
    
    # Test JSON encoding
    result = codec.encode({"test": "data"})
    assert isinstance(result, bytes)
    
def test_codec_decode():
    from clients.kafka_utils import codec
    
    # Test JSON decoding
    data = b'{"test": "data"}'
    result = codec.decode(data, dict)
    assert result == {"test": "data"}