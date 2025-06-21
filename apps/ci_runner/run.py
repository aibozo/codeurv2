import os
import subprocess
import shutil
import json
import tempfile
import logging
import pathlib
import tarfile
from pathlib import Path
from confluent_kafka import Consumer, Producer, KafkaError
from prometheus_client import Counter, Histogram, start_http_server

from apps.core_contracts_pb2 import CommitResult, BuildReport
from apps.orchestrator import topics as T

BOOT = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
REMOTE_REPO = os.getenv("REMOTE_REPO")
TEST_MARKER = os.getenv("PYTEST_MARK", "fast")
ARTEFACT_BUCKET = "/artefacts"  # mounted path (MinIO or host volume)

log = logging.getLogger("ci-runner")
logging.basicConfig(level=logging.INFO)

# Metrics
BUILD_LAT = Histogram("ci_build_latency_sec", "build duration")
BUILD_OK = Counter("ci_build_ok_total", "build passed")
BUILD_FAIL = Counter("ci_build_fail_total", "build failed")

# Start metrics server
start_http_server(9700)

consumer = Consumer({
    "bootstrap.servers": BOOT,
    "group.id": "ci-runner",
    "auto.offset.reset": "earliest"
})
consumer.subscribe([T.CRES])  # CommitResult SUCCESS

producer = Producer({"bootstrap.servers": BOOT})


def run(cmd: list, cwd: str | Path, check=True):
    log.debug("RUN %s", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=check)


def build(commit_sha: str, branch: str) -> BuildReport:
    with BUILD_LAT.time():
        work = Path(tempfile.mkdtemp())
        repo = work / "repo"
        
        try:
            # Clone and checkout
            run(["git", "clone", "--depth", "1", "--branch", branch, REMOTE_REPO, str(repo)], cwd=work)
            run(["git", "checkout", commit_sha], cwd=repo)
            
            # Dependency cache (pip-tools lock optional)
            if (repo / "requirements.txt").exists():
                run(["python", "-m", "pip", "install", "-r", "requirements.txt", "--cache-dir", "/pipcache"], cwd=repo)
            elif (repo / "pyproject.toml").exists():
                # Use poetry if pyproject.toml exists
                run(["pip", "install", "poetry"], cwd=repo)
                run(["poetry", "install", "--with", "ci"], cwd=repo)
            
            # Formatting + linting
            lint_out, failures = [], []
            for cmd in (["black", "--check", "."], ["ruff", "."]):
                r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
                if r.returncode:
                    lint_out.append(r.stdout + r.stderr)
            
            # Pytest selective
            test_cmd = ["pytest", "-q", f"-m{TEST_MARKER}", "--cov", "--cov-report=json:cov.json"]
            r = subprocess.run(test_cmd, cwd=repo, capture_output=True, text=True)
            if r.returncode:
                failures = [l for l in r.stdout.splitlines() if "FAILED" in l]
            
            # Coverage %
            cov_path = repo / "cov.json"
            if cov_path.exists():
                cov = json.loads(cov_path.read_text())
                line_cov = cov["totals"]["percent_covered"]
            else:
                line_cov = 0.0
            
            # Tarball artefact
            os.makedirs(ARTEFACT_BUCKET, exist_ok=True)
            artefact_file = Path(ARTEFACT_BUCKET) / f"{commit_sha}.tar.gz"
            with tarfile.open(artefact_file, "w:gz") as tar:
                tar.add(repo, arcname="repo")
            
            status = "PASSED" if not lint_out and not failures and r.returncode == 0 else "FAILED"
            
            # Update metrics
            if status == "PASSED":
                BUILD_OK.inc()
            else:
                BUILD_FAIL.inc()
            
            return BuildReport(
                commit_sha=commit_sha,
                status=status,
                failed_tests=failures,
                lint_errors=lint_out,
                line_coverage=line_cov,
                artefact_url=str(artefact_file)
            )
        finally:
            # Cleanup
            shutil.rmtree(work, ignore_errors=True)


def main():
    log.info("CI Runner started, waiting for CommitResult messages...")
    
    while True:
        msg = consumer.poll(0.3)
        if not msg:
            continue
        if msg.error() and msg.error().code() != KafkaError._PARTITION_EOF:
            log.error(msg.error())
            continue
            
        try:
            cres = CommitResult.FromString(msg.value())
            if cres.status != "SUCCESS":
                log.info(f"Skipping non-successful commit: {cres.commit_sha}")
                continue  # ignore failed tasks
            
            log.info(f"Building commit {cres.commit_sha} from branch {cres.branch_name}")
            br = build(cres.commit_sha, cres.branch_name)
            
            log.info(f"Build {br.status} for {br.commit_sha}, coverage: {br.line_coverage:.1f}%")
            
            producer.produce(T.BREPORT, br.SerializeToString())
            producer.flush()
        except Exception as e:
            log.error(f"Error processing message: {e}")


if __name__ == "__main__":
    main()