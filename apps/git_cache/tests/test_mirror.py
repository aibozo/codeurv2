import subprocess
import tempfile
import pathlib
import os
import shutil
import pytest


def test_mirror_and_fetch():
    """Test git mirror creation and update functionality"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        
        # Create a bare origin repository
        origin_repo = tmp_path / "origin.git"
        origin_repo.mkdir()
        subprocess.run(["git", "init", "--bare"], cwd=origin_repo, check=True)
        
        # Create a working repo to push commits
        work_repo = tmp_path / "work"
        work_repo.mkdir()
        subprocess.run(["git", "init"], cwd=work_repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work_repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=work_repo, check=True)
        
        # Add initial commit
        (work_repo / "README.md").write_text("# Test Repository")
        subprocess.run(["git", "add", "README.md"], cwd=work_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=work_repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(origin_repo)], cwd=work_repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "master"], cwd=work_repo, check=True)
        
        # Create mirror
        mirror = tmp_path / "mirror.git"
        subprocess.run(["git", "clone", "--mirror", str(origin_repo), str(mirror)], check=True)
        
        # Verify mirror exists and is bare
        assert mirror.exists()
        assert (mirror / "HEAD").exists()
        assert (mirror / "config").exists()
        
        # Add another commit to origin
        (work_repo / "test.txt").write_text("test content")
        subprocess.run(["git", "add", "test.txt"], cwd=work_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Add test file"], cwd=work_repo, check=True)
        subprocess.run(["git", "push"], cwd=work_repo, check=True)
        
        # Update mirror
        subprocess.run(["git", "-C", str(mirror), "remote", "update", "--prune"], check=True)
        
        # Verify mirror has the new commit
        result = subprocess.run(
            ["git", "-C", str(mirror), "log", "--oneline"],
            capture_output=True,
            text=True,
            check=True
        )
        assert "Add test file" in result.stdout


def test_clone_with_reference():
    """Test cloning with --reference-if-able flag"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        
        # Create origin
        origin_repo = tmp_path / "origin.git"
        origin_repo.mkdir()
        subprocess.run(["git", "init", "--bare"], cwd=origin_repo, check=True)
        
        # Create work repo and add content
        work_repo = tmp_path / "work"
        work_repo.mkdir()
        subprocess.run(["git", "init"], cwd=work_repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work_repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=work_repo, check=True)
        (work_repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=work_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=work_repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(origin_repo)], cwd=work_repo, check=True)
        subprocess.run(["git", "push", "-u", "origin", "master"], cwd=work_repo, check=True)
        
        # Create mirror
        mirror = tmp_path / "mirror.git"
        subprocess.run(["git", "clone", "--mirror", str(origin_repo), str(mirror)], check=True)
        
        # Clone using reference
        clone_dir = tmp_path / "clone"
        subprocess.run([
            "git", "clone",
            "--reference-if-able", str(mirror),
            str(origin_repo),
            str(clone_dir)
        ], check=True)
        
        # Verify clone worked
        assert (clone_dir / "README.md").exists()
        assert (clone_dir / "README.md").read_text() == "# Test"


def test_sha1sum_deterministic():
    """Test that SHA1 hash of repo URL is deterministic"""
    import hashlib
    
    repo_url = "https://github.com/test/repo.git"
    
    # Calculate SHA1 like the script does
    hash1 = hashlib.sha1(repo_url.encode()).hexdigest()[:20]
    hash2 = hashlib.sha1(repo_url.encode()).hexdigest()[:20]
    
    assert hash1 == hash2
    assert len(hash1) == 20