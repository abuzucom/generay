"""Tests for the deterministic scanners in scripts/time_checks and scripts/check_time_handling.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import time_checks  # resolved through the path set above


class ScanCase(unittest.TestCase):
    """Base case that writes one file and scans it."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def scan(self, name: str, text: str) -> set[str]:
        """Return the check IDs the scanners report for one file."""
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return {item.class_id for item in time_checks.run_checks(list(time_checks.CHECKS), [path], self.root)}


class PatternRuleTest(ScanCase):
    def test_day_constant(self) -> None:
        self.assertIn("C1.2", self.scan("a.py", "TOMORROW = now + 86400\n"))

    def test_leap_test_without_century_rule(self) -> None:
        self.assertIn("C2.1", self.scan("a.js", "const leap = year % 4 == 0;\n"))

    def test_full_leap_rule_not_reported(self) -> None:
        self.assertNotIn(
            "C2.1", self.scan("a.js", "const leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);\n")
        )

    def test_end_of_day_literal(self) -> None:
        self.assertIn("C3.6", self.scan("q.sql", "WHERE t <= '2026-01-01 23:59:59'\n"))

    def test_fixed_offset_tz_in_yaml(self) -> None:
        self.assertIn("C11.5", self.scan("job.yaml", "env:\n  TZ: EST5\n"))

    def test_legacy_zone_in_toml(self) -> None:
        self.assertIn("C10.4", self.scan("cfg.toml", 'zone = "Asia/Calcutta"\n'))

    def test_gmt_literal_reported_but_http_header_not(self) -> None:
        self.assertIn("C13.1", self.scan("a.py", 'zone = "GMT"\n'))
        self.assertNotIn("C13.1", self.scan("b.py", 'header = "GMT"  # HTTP date header\n'))

    def test_week_year_pattern(self) -> None:
        self.assertIn("C24.4", self.scan("A.java", 'ofPattern("YYYY-MM-dd");\n'))

    def test_js_date_only_string(self) -> None:
        self.assertIn("C8.3", self.scan("a.ts", 'const d = new Date("2026-10-03");\n'))

    def test_js_wall_clock_duration(self) -> None:
        self.assertIn("C18.1", self.scan("a.js", "const took = Date.now() - start;\n"))

    def test_jvm_host_zone(self) -> None:
        self.assertIn("C9.1", self.scan("A.kt", "val now = LocalDateTime.now()\n"))

    def test_go_bare_duration(self) -> None:
        self.assertIn("C21.1", self.scan("w.go", "time.Sleep(time.Duration(cfg.Delay))\n"))

    def test_go_scaled_duration_not_reported(self) -> None:
        self.assertNotIn("C21.1", self.scan("w.go", "time.Sleep(time.Duration(cfg.Delay) * time.Second)\n"))

    def test_dotnet_host_zone(self) -> None:
        self.assertIn("C9.1", self.scan("A.cs", "var t = DateTime.Now;\n"))

    def test_python_year_replace(self) -> None:
        self.assertIn("C7.2", self.scan("a.py", "d = d.replace(year=d.year + 1)\n"))

    def test_gnss_and_sync_rules(self) -> None:
        text = 'fix = "$GPRMC"\nsubprocess.run(["timedatectl"])\nwait = "hwclock"\n'
        self.assertTrue({"C27.21", "C27.6", "C27.24"} <= self.scan("a.py", text))

    def test_hardcoded_ntp_ip(self) -> None:
        self.assertIn("C27.7", self.scan("fw.c", 'static const char *NTP_SERVER = "128.105.39.11";\n'))

    def test_pool_in_dockerfile_echo(self) -> None:
        self.assertIn("C27.7", self.scan("Dockerfile", 'RUN echo "pool pool.ntp.org iburst" >> /etc/chrony.conf\n'))

    def test_inet_only_socket(self) -> None:
        self.assertIn("C27.13", self.scan("a.py", "s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n"))
        self.assertNotIn("C27.13", self.scan("b.py", "s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)\n"))

    def test_government_server_and_stratum_claim(self) -> None:
        self.assertIn("C27.9", self.scan("c.conf", "server time.nist.gov iburst\n"))
        self.assertIn("C27.9", self.scan("a.py", "# stratum 1 so authoritative\n"))

    def test_override_header_in_config(self) -> None:
        self.assertIn("C25.2", self.scan("nginx.conf", "proxy_set_header X-Debug-Time $arg_t;\n"))

    def test_very_long_lines_skipped(self) -> None:
        self.assertEqual(self.scan("min.js", "var a = 86400;" + " " * 3000 + "\n"), set())

    def test_unrelated_file_type_ignored(self) -> None:
        self.assertEqual(self.scan("notes.txt", "86400\n"), set())


class PythonAstTest(ScanCase):
    def test_naive_now(self) -> None:
        self.assertIn("C9.1", self.scan("a.py", "from datetime import datetime\nx = datetime.now()\n"))

    def test_aware_now_not_reported(self) -> None:
        self.assertNotIn(
            "C9.1", self.scan("a.py", "from datetime import datetime, timezone\nx = datetime.now(timezone.utc)\n")
        )

    def test_fromtimestamp_without_tz(self) -> None:
        self.assertIn("C9.1", self.scan("a.py", "import datetime\nx = datetime.datetime.fromtimestamp(t)\n"))

    def test_fromtimestamp_with_tz_not_reported(self) -> None:
        self.assertNotIn("C9.1", self.scan("a.py", "import datetime\nx = datetime.datetime.fromtimestamp(t, tz=utc)\n"))

    def test_astimezone_without_argument(self) -> None:
        self.assertIn("C9.1", self.scan("a.py", "y = value.astimezone()\n"))

    def test_pytz_tzinfo(self) -> None:
        text = "import datetime, pytz\nd = datetime.datetime(2026, 1, 1, tzinfo=pytz.timezone('Europe/London'))\n"
        self.assertIn("C10.6", self.scan("a.py", text))

    def test_time_seeded_random(self) -> None:
        self.assertIn("C19.5", self.scan("a.py", "import random, time\nrandom.seed(time.time())\n"))

    def test_negative_sleep(self) -> None:
        self.assertIn("C21.3", self.scan("a.py", "import time\ntime.sleep(-1)\n"))

    def test_wall_clock_subtraction(self) -> None:
        self.assertIn("C18.1", self.scan("a.py", "import time\nd = time.time() - start\n"))

    def test_monotonic_subtraction_not_reported(self) -> None:
        self.assertNotIn("C18.1", self.scan("a.py", "import time\nd = time.monotonic() - start\n"))

    def test_module_scope_now(self) -> None:
        self.assertIn("C18.3", self.scan("a.py", "import time\nSTARTED = time.time()\n"))

    def test_function_scope_now_not_reported_as_module_scope(self) -> None:
        self.assertNotIn("C18.3", self.scan("a.py", "import time\n\n\ndef f():\n    return time.time()\n"))

    def test_syntax_error_does_not_crash(self) -> None:
        self.assertEqual(self.scan("bad.py", "def (:\n"), set())


class ConfigScanTest(ScanCase):
    def test_public_pool_and_missing_makestep(self) -> None:
        found = self.scan("chrony.conf", "pool pool.ntp.org iburst\n")
        self.assertTrue({"C27.7", "C27.2", "C27.16"} <= found)

    def test_hardcoded_ip_source(self) -> None:
        found = self.scan("chrony.conf", "server 192.0.2.1 iburst\nmakestep 1 3\nrtcsync\n")
        self.assertTrue({"C27.7", "C27.13", "C27.15"} <= found)

    def test_two_direct_sources_cannot_vote(self) -> None:
        text = "server a.example\nserver b.example\nmakestep 1 3\nrtcsync\n"
        self.assertIn("C27.15", self.scan("chrony.conf", text))

    def test_four_sources_clean(self) -> None:
        text = "".join(f"server s{i}.example\n" for i in range(4)) + "makestep 1 3\nrtcsync\n"
        self.assertEqual(self.scan("chrony.conf", text), set())

    def test_unlimited_makestep(self) -> None:
        self.assertIn(
            "C27.11", self.scan("chrony.conf", "server a\nserver b\nserver c\nserver d\nmakestep 1 -1\nrtcsync\n")
        )

    def test_open_command_port_and_allow_all(self) -> None:
        text = "server a\nserver b\nserver c\nserver d\nbindcmdaddress 0.0.0.0\nallow\nmakestep 1 3\nrtcsync\n"
        self.assertIn("C27.23", self.scan("chrony.conf", text))

    def test_fast_poll(self) -> None:
        self.assertIn("C27.14", self.scan("chrony.conf", "server a minpoll 2\nmakestep 1 3\nrtcsync\n"))

    def test_trusted_refclock(self) -> None:
        self.assertIn("C27.22", self.scan("chrony.conf", "refclock SHM 0 trust prefer\nmakestep 1 3\nrtcsync\n"))

    def test_gps_only(self) -> None:
        self.assertIn("C27.19", self.scan("chrony.conf", "refclock PPS /dev/pps0\nmakestep 1 3\nrtcsync\n"))

    def test_ntpd_without_restrict(self) -> None:
        self.assertIn("C27.23", self.scan("ntp.conf", "server a\nserver b\nserver c\nserver d\n"))

    def test_ntpd_with_restrict_clean(self) -> None:
        text = "server a\nserver b\nserver c\nserver d\nrestrict default nomodify noquery\n"
        self.assertNotIn("C27.23", self.scan("ntp.conf", text))

    def test_md5_key(self) -> None:
        self.assertIn("C27.23", self.scan("ntp.keys", "1 MD5 secret\n"))

    def test_sys_time_capability_and_privileged(self) -> None:
        found = self.scan("pod.yaml", "securityContext:\n  privileged: true\n  capabilities:\n    add: [SYS_TIME]\n")
        self.assertIn("C27.23", found)

    def test_world_open_ntp_port(self) -> None:
        text = 'from_port = 123\ncidr_blocks = ["0.0.0.0/0"]\n'
        self.assertIn("C27.23", self.scan("sg.tf", text))

    def test_daemon_forced_to_ipv4(self) -> None:
        self.assertIn("C27.13", self.scan("chronyd.service", "ExecStart=/usr/sbin/chronyd -4\n"))

    def test_dhcp_ntp(self) -> None:
        self.assertIn("C27.10", self.scan("net.network", "UseNTP=yes\n"))

    def test_yaml_implicit_date(self) -> None:
        self.assertIn("C23.8", self.scan("a.yml", "due: 2026-10-03\n"))

    def test_yaml_quoted_date_clean(self) -> None:
        self.assertNotIn("C23.8", self.scan("a.yml", 'due: "2026-10-03"\n'))

    def test_sql_timestamp_column(self) -> None:
        self.assertIn("C22.6", self.scan("s.sql", "CREATE TABLE t (maturity TIMESTAMP NOT NULL);\n"))

    def test_sql_timestamp_with_time_zone_clean(self) -> None:
        self.assertNotIn("C22.6", self.scan("s.sql", "CREATE TABLE t (maturity TIMESTAMP WITH TIME ZONE);\n"))


class RunnerTest(ScanCase):
    def test_findings_sorted_and_deduplicated(self) -> None:
        path = self.root / "a.py"
        path.write_text("a = 86400\nb = 86400\n", encoding="utf-8")
        findings = time_checks.run_checks(list(time_checks.CHECKS), [path, path], self.root)
        self.assertEqual([item.line for item in findings if item.class_id == "C1.2"], [1, 2])

    def test_skipped_directories(self) -> None:
        skipped = self.root / "node_modules" / "lib.js"
        skipped.parent.mkdir()
        skipped.write_text("const d = 86400;\n", encoding="utf-8")
        self.assertEqual(time_checks.run_checks(list(time_checks.CHECKS), [self.root], self.root), [])

    def test_no_finding_blocks(self) -> None:
        path = self.root / "a.py"
        path.write_text("x = 86400\nimport time\nt0 = time.time()\n", encoding="utf-8")
        findings = time_checks.run_checks(list(time_checks.CHECKS), [path], self.root)
        self.assertTrue(findings)
        self.assertFalse(any(item.blocking for item in findings))

    def test_every_finding_check_exists_in_the_ledger(self) -> None:
        methods = time_checks.load_methods()
        for item in time_checks.run_checks(list(time_checks.CHECKS), [REPO_ROOT / "eval" / "cases"], REPO_ROOT):
            self.assertIn(item.class_id, methods)

    def test_prescan_entries_carry_method(self) -> None:
        path = self.root / "a.py"
        path.write_text("x = 86400\n", encoding="utf-8")
        findings = time_checks.run_checks(list(time_checks.CHECKS), [path], self.root)
        entries = time_checks.prescan_entries(findings, time_checks.load_methods())
        self.assertEqual(entries[0]["id"], "P1")
        self.assertEqual(entries[0]["method"], "both")


class CliTest(ScanCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(REPO_ROOT / "scripts" / "check_time_handling.py"), *args]
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def test_json_output_and_zero_exit(self) -> None:
        (self.root / "a.py").write_text("x = 86400\n", encoding="utf-8")
        result = self.run_cli("all", str(self.root / "a.py"), "--root", str(self.root), "--json")
        self.assertEqual(result.returncode, 0)
        entries = json.loads(result.stdout)
        self.assertEqual((entries[0]["check"], entries[0]["method"], entries[0]["blocking"]), ("C1.2", "both", False))

    def test_path_outside_root_rejected(self) -> None:
        result = self.run_cli("all", "/etc/hostname", "--root", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the repository root", result.stderr)

    def test_exclude_prefix(self) -> None:
        (self.root / "skip").mkdir()
        (self.root / "skip" / "a.py").write_text("x = 86400\n", encoding="utf-8")
        result = self.run_cli("all", str(self.root), "--root", str(self.root), "--exclude", "skip", "--json")
        self.assertEqual(json.loads(result.stdout), [])

    def test_text_output(self) -> None:
        (self.root / "a.py").write_text("x = 86400\n", encoding="utf-8")
        result = self.run_cli("code-patterns", str(self.root / "a.py"), "--root", str(self.root))
        self.assertIn("a.py:1: C1.2 candidate: fixed 24-hour day constant", result.stdout)


if __name__ == "__main__":
    unittest.main()
