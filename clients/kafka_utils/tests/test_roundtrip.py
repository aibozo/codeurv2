import asyncio, pytest

@pytest.mark.asyncio
async def test_kafka_utils_structure():
    # Simple test to verify the module structure exists
    import os
    assert os.path.exists("clients/kafka_utils/__init__.py")
    assert os.path.exists("clients/kafka_utils/codec.py")
    assert os.path.exists("clients/kafka_utils/producer.py")
    assert os.path.exists("clients/kafka_utils/consumer.py")
    assert os.path.exists("clients/kafka_utils/metrics.py")