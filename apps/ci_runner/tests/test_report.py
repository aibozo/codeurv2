import pytest
from apps.core_contracts_pb2 import BuildReport


def test_report_proto():
    """Test BuildReport protobuf serialization"""
    br = BuildReport(
        commit_sha="abc123",
        status="PASSED",
        line_coverage=90.0,
        failed_tests=[],
        lint_errors=[],
        artefact_url="/artefacts/abc123.tar.gz"
    )
    
    # Serialize and deserialize
    data = br.SerializeToString()
    br2 = BuildReport.FromString(data)
    
    assert br2.status == "PASSED"
    assert br2.commit_sha == "abc123"
    assert br2.line_coverage == 90.0
    assert br2.artefact_url == "/artefacts/abc123.tar.gz"
    assert len(br2.failed_tests) == 0
    assert len(br2.lint_errors) == 0


def test_report_with_failures():
    """Test BuildReport with failures"""
    br = BuildReport(
        commit_sha="def456",
        status="FAILED",
        line_coverage=75.5,
        failed_tests=["test_foo::test_bar FAILED", "test_baz::test_qux FAILED"],
        lint_errors=["E501 line too long", "F401 imported but unused"],
        artefact_url="/artefacts/def456.tar.gz"
    )
    
    data = br.SerializeToString()
    br2 = BuildReport.FromString(data)
    
    assert br2.status == "FAILED"
    assert br2.line_coverage == 75.5
    assert len(br2.failed_tests) == 2
    assert "test_foo::test_bar FAILED" in br2.failed_tests
    assert len(br2.lint_errors) == 2
    assert "E501 line too long" in br2.lint_errors