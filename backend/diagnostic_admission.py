"""Pure diagnostic readiness gate; does not grant permissions or execution authority."""
from datetime import datetime

DIAGNOSTIC_BUNDLE = 'com.trycua.driver.pointguard'
DIAGNOSTIC_EXECUTABLE = '/Users/mvpagent/Applications/CuaDriverPointGuard.app/Contents/MacOS/cua-driver-pointguard'
DIAGNOSTIC_SHA256 = '01c3db9176267741a1608c971f2233e0371611d13f2346fecbf97c648f2d2c16'


def require_direct_capture_ready(report, *, expected_pid):
    """Validate live permission-helper report, not a cached daemon status.

    Upstream labels both bundle-resident processes as driver-daemon; the caller
    must independently bind expected_pid to its LaunchServices setup helper.
    """
    def require(condition):
        if not condition:
            raise ValueError('DIAGNOSTIC_DIRECT_CAPTURE_UNCONFIRMED')

    require(type(expected_pid) is int and expected_pid > 1)
    require(type(report) is dict)
    source = report.get('source')
    require(type(source) is dict)
    require(source.get('attribution') == 'driver-daemon')
    require(source.get('bundle_id') == DIAGNOSTIC_BUNDLE)
    require(source.get('executable') == DIAGNOSTIC_EXECUTABLE)
    require(type(source.get('pid')) is int and source['pid'] == expected_pid)
    for field in ('accessibility', 'screen_recording', 'screen_recording_capturable'):
        require(report.get(field) is True)
    require(report.get('direct_capture_status') == 'ready')
    require(report.get('direct_capture_error') is None)
    require('direct_capture_verification_error' not in report)
    evidence = report.get('direct_capture_verification')
    require(type(evidence) is dict)
    require(evidence.get('bundle_id') == DIAGNOSTIC_BUNDLE)
    require(evidence.get('source') == 'permissions_grant')
    stamp = evidence.get('verified_at')
    require(type(stamp) is str)
    try:
        parsed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('DIAGNOSTIC_DIRECT_CAPTURE_UNCONFIRMED') from None
    require(parsed.tzinfo is not None)


def require_direct_capture_admission(setup_report, daemon_report, *, setup_pid, daemon_pid):
    """Bind a live setup result to the separately inspected execution daemon."""
    require_direct_capture_ready(setup_report, expected_pid=setup_pid)
    if type(daemon_pid) is not int or daemon_pid <= 1 or daemon_pid == setup_pid:
        raise ValueError('DIAGNOSTIC_DAEMON_ADMISSION_UNCONFIRMED')
    if type(daemon_report) is not dict:
        raise ValueError('DIAGNOSTIC_DAEMON_ADMISSION_UNCONFIRMED')
    source = daemon_report.get('source')
    if (type(source) is not dict
            or source.get('attribution') != 'driver-daemon'
            or source.get('bundle_id') != DIAGNOSTIC_BUNDLE
            or source.get('executable') != DIAGNOSTIC_EXECUTABLE
            or type(source.get('pid')) is not int or source['pid'] != daemon_pid
            or daemon_report.get('accessibility') is not True
            or daemon_report.get('screen_recording') is not True
            or daemon_report.get('direct_capture_status') != 'not_checked'
            or daemon_report.get('screen_recording_capturable') is not None
            or daemon_report.get('direct_capture_error') is not None
            or 'direct_capture_verification_error' in daemon_report
            or daemon_report.get('direct_capture_verification')
            != setup_report['direct_capture_verification']):
        raise ValueError('DIAGNOSTIC_DAEMON_ADMISSION_UNCONFIRMED')


def require_current_capture_admission(receipt, daemon_report, *, run_id, session_id,
                                      daemon_pid, executable_sha256, now):
    """Check a trusted, current lifecycle receipt before profile/model dispatch.

    This is not an authorization token or proof of file/process provenance.
    The supervisor owns the receipt, observes helper and daemon identities,
    and holds the desktop lock without intervening permission revocation.
    """
    def require(condition):
        if not condition:
            raise ValueError('DIAGNOSTIC_CURRENT_CAPTURE_UNCONFIRMED')

    require(type(receipt) is dict)
    require(type(run_id) is str and bool(run_id))
    require(type(session_id) is str and bool(session_id))
    require(receipt.get('runId') == run_id and receipt.get('sessionId') == session_id)
    require(executable_sha256 == DIAGNOSTIC_SHA256)
    require(receipt.get('sha256') == executable_sha256)
    require(type(receipt.get('daemonPid')) is int and receipt['daemonPid'] == daemon_pid)
    require(isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() is not None)

    def timestamp(value):
        require(type(value) is str)
        try:
            result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('DIAGNOSTIC_CURRENT_CAPTURE_UNCONFIRMED') from None
        require(result.tzinfo is not None and result.utcoffset() is not None)
        return result

    started = timestamp(receipt.get('startedAt'))
    checked = timestamp(receipt.get('checkedAt'))
    require(started <= checked <= now)
    require((now - started).total_seconds() <= 300)
    setup = receipt.get('setupReport')
    require_direct_capture_admission(setup, daemon_report,
                                    setup_pid=receipt.get('setupPid'), daemon_pid=daemon_pid)
    verified = timestamp(setup['direct_capture_verification']['verified_at'])
    # Upstream serializes whole seconds: allow only that rounding difference.
    require(started.replace(microsecond=0) <= verified <= checked)
