"""Offline unit tests for Fedora security posture diagnostics."""
import importlib.util
import pathlib
import subprocess
import unittest

from unittest import mock

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "tools" / "fedora-security-report.py"
SPEC = importlib.util.spec_from_file_location("fedora_security_report", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SecurityReportTests(unittest.TestCase):
    def test_fips_flag_missing_is_unknown_not_false(self):
        with mock.patch.object(MODULE.Path, "read_text", side_effect=FileNotFoundError):
            self.assertEqual(MODULE.kernel_fips(), "unknown")

    def test_fips_flag_unexpected_value_is_unknown(self):
        with mock.patch.object(MODULE.Path, "read_text", return_value="unexpected\n"):
            self.assertEqual(MODULE.kernel_fips(), "unknown")

    def test_command_output_is_bounded(self):
        response = subprocess.CompletedProcess(["rpm"], 0, stdout="Z" * 500, stderr="")
        with mock.patch.object(MODULE.shutil, "which", return_value="/usr/bin/rpm"):
            with mock.patch.object(MODULE.subprocess, "run", return_value=response) as execute:
                self.assertEqual(len(MODULE.run("rpm", "-q", "solaar")), 240)
                self.assertEqual(execute.call_args.kwargs["timeout"], 4)
                self.assertFalse(execute.call_args.kwargs["check"])

    def test_missing_command_is_not_executed(self):
        with mock.patch.object(MODULE.shutil, "which", return_value=None):
            with mock.patch.object(MODULE.subprocess, "run") as execute:
                self.assertEqual(MODULE.run("not-installed"), "not installed")
                execute.assert_not_called()

    def test_report_does_not_certify_fips(self):
        with mock.patch.object(MODULE, "run", return_value="unavailable"):
            with mock.patch.object(MODULE, "distro", return_value={"id": "fedora", "version": "44"}):
                with mock.patch.object(MODULE, "kernel_fips", return_value="1"):
                    with mock.patch.object(MODULE.Path, "is_file", return_value=False):
                        data = MODULE.report()
        self.assertEqual(data["kernel_fips_flag"], "1")
        self.assertIn("NOT ASSESSED", data["compliance"])
        self.assertTrue(any("CMVP" in item for item in data["observations"]))


if __name__ == "__main__":
    unittest.main()
