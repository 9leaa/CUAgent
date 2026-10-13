"""Pure diagnostic readiness gate; does not grant permissions or execution authority."""
from datetime import datetime

DIAGNOSTIC_BUNDLE = 'com.trycua.driver.local'
DIAGNOSTIC_EXECUTABLE = '/Users/mvpagent/Applications/CuaDriverLocal.app/Contents/MacOS/cua-driver-local'


def require_direct_capture_ready(report, *, expected_pid):
    """Caller must obtain report live from its controlled daemon, not a cache."""
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
