"""
Tests that send_at_command surfaces the raw modem response on failure.

The Pi deployment failed with `Failed to execute: AT+CPIN?` while the
journal never showed *why* (the response was discarded), so these tests
lock the diagnostic logging that makes that failure self-explaining.
"""
from src.data.sms_handler import SMSHandler


class FakeSerial:
    """Minimal serial stand-in feeding scripted readline() responses."""

    def __init__(self, lines):
        self._lines = list(lines)
        self.is_open = True
        self.written = b""

    @property
    def in_waiting(self):
        return len(self._lines[0]) if self._lines else 0

    def reset_input_buffer(self):
        pass

    def write(self, data):
        self.written += data

    def readline(self):
        return self._lines.pop(0)


def make_handler(lines):
    handler = SMSHandler.__new__(SMSHandler)  # skip __init__ (opens real port)
    handler.serial_port = FakeSerial(lines)
    handler.last_sms_time = None
    handler.enabled = True
    return handler


def test_error_response_is_logged(capsys):
    handler = make_handler([b"+CME ERROR: SIM not inserted\r\n"])
    assert handler.send_at_command("AT+CPIN?", expected_response="READY") is False
    out = capsys.readouterr().out
    assert "AT command returned error" in out
    assert "AT+CPIN?" in out
    assert "+CME ERROR: SIM not inserted" in out


def test_timeout_logs_partial_response(capsys):
    handler = make_handler([b"+CPIN: SIM PIN\r\n"])
    assert handler.send_at_command(
        "AT+CPIN?", expected_response="READY", timeout=0.3
    ) is False
    out = capsys.readouterr().out
    assert "AT command timed out" in out
    assert "+CPIN: SIM PIN" in out


def test_expected_response_still_succeeds(capsys):
    handler = make_handler([b"+CPIN: READY\r\n", b"OK\r\n"])
    assert handler.send_at_command("AT+CPIN?", expected_response="READY") is True
    assert "AT command" not in capsys.readouterr().out
    assert handler.serial_port.written == b"AT+CPIN?\r\n"


def test_initialize_module_reports_failing_command(capsys):
    handler = make_handler([b"OK\r\n", b"+CME ERROR: SIM not inserted\r\n"])
    assert handler.initialize_module() is False
    out = capsys.readouterr().out
    assert "Failed to execute: AT+CPIN?" in out
    assert "+CME ERROR: SIM not inserted" in out
