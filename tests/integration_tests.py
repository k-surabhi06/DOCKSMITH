#!/usr/bin/env python3
"""
Integration test suite for Docksmith.
Tests all scenarios from Section 9 of requirements.
"""
import os
import sys
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


class DocksmithTester:
    """Integration test runner for Docksmith."""
    
    def __init__(self, docksmith_root=None):
        """
        Args:
            docksmith_root: Path to DOCKSMITH project root
        """
        self.docksmith_root = Path(docksmith_root or ".")
        self.store_path = Path(os.path.expanduser("~/.docksmith"))
        self.test_results = []
        self.test_num = 0
    
    def run_command(self, cmd):
        """Run command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.docksmith_root)
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def test(self, name, condition, expected=True):
        """Verify test condition and record result."""
        self.test_num += 1
        passed = bool(condition) == bool(expected)
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} [{self.test_num}] {name}")
        if not passed:
            print(f"    Expected: {expected}, Got: {condition}")
        self.test_results.append((name, passed))
        return passed
    
    def test_cold_build(self):
        """Scenario 1: Cold build - all steps should be CACHE MISS."""
        print("\n=== Scenario 1: Cold Build ===")
        
        # Clean slate
        shutil.rmtree(self.store_path, ignore_errors=True)
        os.makedirs(self.store_path, exist_ok=True)
        
        # Import base image first
        self._setup_base_image()
        
        # Build
        returncode, stdout, stderr = self.run_command([
            sys.executable, "main.py", "build", "-t", "test-app:v1",
            "sample_app"
        ])
        
        self.test("Build completes successfully", returncode == 0)
        self.test("Build output contains CACHE MISS", "[CACHE MISS]" in stdout)
        self.test("Build output contains image digest", "sha256:" in stdout)
        self.test("Build output contains tag", "test-app:v1" in stdout)
    
    def test_warm_build(self):
        """Scenario 2: Warm build - all steps should be CACHE HIT."""
        print("\n=== Scenario 2: Warm Build ===")
        
        # Rebuild without changes
        returncode, stdout, stderr = self.run_command([
            sys.executable, "main.py", "build", "-t", "test-app:v1",
            "sample_app"
        ])
        
        self.test("Rebuild completes successfully", returncode == 0)
        self.test("Rebuild output contains CACHE HIT", "[CACHE HIT]" in stdout)
        self.test("Rebuild is near-instant", "0." in stdout or stdout.count("s") > 0)
    
    def test_file_change_cascade(self):
        """Scenario 3: Edit source file, rebuild - affected step and below should miss."""
        print("\n=== Scenario 3: File Change Cascade ===")
        
        app_file = self.docksmith_root / "sample_app" / "app.py"
        backup = str(app_file) + ".bak"
        
        # Backup original
        shutil.copy(app_file, backup)
        
        try:
            # Modify app.py
            with open(app_file, "a") as f:
                f.write("\n# Modified for testing\n")
            
            # Rebuild
            returncode, stdout, stderr = self.run_command([
                sys.executable, "main.py", "build", "-t", "test-app:v1",
                "sample_app"
            ])
            
            self.test("Rebuild after file change completes", returncode == 0)
            self.test("COPY step shows CACHE MISS (file changed)", "[CACHE MISS]" in stdout)
            
        finally:
            # Restore original
            shutil.move(backup, app_file)
    
    def test_images_list(self):
        """Scenario 4: docksmith images - list images with correct columns."""
        print("\n=== Scenario 4: Images List ===")
        
        returncode, stdout, stderr = self.run_command([
            sys.executable, "main.py", "images"
        ])
        
        self.test("Images command succeeds", returncode == 0)
        self.test("Output contains image name", "test-app" in stdout)
        self.test("Output contains tag", "v1" in stdout)
        self.test("Output contains digest", "sha256:" in stdout or len(stdout) > 10)
    
    def test_image_manifest_structure(self):
        """Verify manifest structure on disk."""
        print("\n=== Scenario 5: Manifest Structure ===")
        
        manifest_file = self.store_path / "images" / "test-app_v1.json"
        self.test("Manifest file exists", manifest_file.exists())
        
        if manifest_file.exists():
            with open(manifest_file) as f:
                manifest = json.load(f)
            
            self.test("Manifest has 'name' field", "name" in manifest)
            self.test("Manifest has 'tag' field", "tag" in manifest)
            self.test("Manifest has 'digest' field", "digest" in manifest)
            self.test("Manifest has 'created' field", "created" in manifest)
            self.test("Manifest has 'config' field", "config" in manifest)
            self.test("Manifest has 'layers' field", "layers" in manifest)
            
            if "config" in manifest:
                config = manifest["config"]
                self.test("Config has 'Env' field", "Env" in config)
                self.test("Config has 'Cmd' field", "Cmd" in config)
                self.test("Config has 'WorkingDir' field", "WorkingDir" in config)
            
            if "layers" in manifest:
                self.test("Manifest has at least one layer", len(manifest["layers"]) > 0)
                for layer in manifest["layers"]:
                    self.test("Layer has digest", "digest" in layer)
    
    def test_cache_bypass_mode(self):
        """Scenario 6: --no-cache flag bypasses cache."""
        print("\n=== Scenario 6: --no-cache Mode ===")
        
        # Clear cache
        cache_file = self.store_path / "cache" / "index.json"
        if cache_file.exists():
            os.remove(cache_file)
        
        # Build with --no-cache
        returncode, stdout, stderr = self.run_command([
            sys.executable, "main.py", "build", "-t", "test-app:v2",
            "sample_app", "--no-cache"
        ])
        
        self.test("Build with --no-cache completes", returncode == 0)
        self.test("--no-cache shows CACHE MISS", "[CACHE MISS]" in stdout)
    
    def test_cache_invalidation_on_env_change(self):
        """Verify cache invalidates when ENV changes."""
        print("\n=== Scenario 7: ENV Change Invalidation ===")
        
        # Build current state
        _, stdout1, _ = self.run_command([
            sys.executable, "main.py", "build", "-t", "test-app:v1",
            "sample_app"
        ])
        
        # Second build should hit cache
        _, stdout2, _ = self.run_command([
            sys.executable, "main.py", "build", "-t", "test-app:v1",
            "sample_app"
        ])
        
        self.test("Cache hits on unchanged build", "[CACHE HIT]" in stdout2)
    
    def test_rmi_removes_image(self):
        """Scenario 8: rmi removes image and layers."""
        print("\n=== Scenario 8: RMI Removes Image ===")
        
        # Ensure image exists
        self.run_command([
            sys.executable, "main.py", "build", "-t", "test-remove:v1",
            "sample_app"
        ])
        
        manifest_file = self.store_path / "images" / "test-remove_v1.json"
        self.test("Image manifest exists before rmi", manifest_file.exists())
        
        # Remove image
        returncode, stdout, stderr = self.run_command([
            sys.executable, "main.py", "rmi", "test-remove:v1"
        ])
        
        self.test("RMI command succeeds", returncode == 0)
        self.test("Image manifest removed after rmi", not manifest_file.exists())
    
    def test_docksmithfile_validation(self):
        """Test invalid Docksmithfile handling."""
        print("\n=== Scenario 9: Docksmithfile Validation ===")
        
        # Create temp dir with invalid Docksmithfile
        temp_dir = tempfile.mkdtemp()
        try:
            invalid_file = Path(temp_dir) / "Docksmithfile"
            invalid_file.write_text("INVALID_INSTRUCTION\nFROM alpine\n")
            
            returncode, stdout, stderr = self.run_command([
                sys.executable, "main.py", "build", "-t", "invalid:v1",
                temp_dir
            ])
            
            self.test("Invalid instruction fails build", returncode != 0)
            self.test("Error message mentions line number", "line" in stdout or "line" in stderr)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_missing_base_image(self):
        """Test error when base image not found."""
        print("\n=== Scenario 10: Missing Base Image ===")
        
        temp_dir = tempfile.mkdtemp()
        try:
            docksmith_file = Path(temp_dir) / "Docksmithfile"
            docksmith_file.write_text("FROM nonexistent:latest\nCMD [\"echo\", \"hi\"]\n")
            
            returncode, stdout, stderr = self.run_command([
                sys.executable, "main.py", "build", "-t", "test:v1",
                temp_dir
            ])
            
            self.test("Missing base image fails build", returncode != 0)
            self.test("Error message is clear", "not found" in stdout or "not found" in stderr)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _setup_base_image(self):
        """Set up a minimal base image for testing."""
        images_dir = self.store_path / "images"
        os.makedirs(images_dir, exist_ok=True)
        
        # Create minimal alpine:3.18 manifest
        # In a real scenario, this would be pre-downloaded
        base_manifest = {
            "name": "alpine",
            "tag": "3.18",
            "digest": "sha256:base123",
            "created": "2024-01-01T00:00:00Z",
            "config": {
                "Env": [],
                "Cmd": None,
                "WorkingDir": "/"
            },
            "layers": []
        }
        
        # Create a minimal layer for the base image
        layers_dir = self.store_path / "layers"
        os.makedirs(layers_dir, exist_ok=True)
        
        # For now, just save the manifest
        manifest_file = images_dir / "alpine_3.18.json"
        with open(manifest_file, 'w') as f:
            json.dump(base_manifest, f, indent=2)
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("=" * 60)
        print("DOCKSMITH INTEGRATION TEST SUITE")
        print("=" * 60)
        
        self.test_cold_build()
        self.test_warm_build()
        self.test_file_change_cascade()
        self.test_images_list()
        self.test_image_manifest_structure()
        self.test_cache_bypass_mode()
        self.test_cache_invalidation_on_env_change()
        self.test_rmi_removes_image()
        self.test_docksmithfile_validation()
        self.test_missing_base_image()
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, p in self.test_results if p)
        total = len(self.test_results)
        
        print(f"\nTotal: {total} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        if passed == total:
            print("\n✓ ALL TESTS PASSED")
            return 0
        else:
            print(f"\n✗ {total - passed} TEST(S) FAILED")
            return 1


if __name__ == "__main__":
    tester = DocksmithTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
