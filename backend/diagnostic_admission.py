"""Pure diagnostic readiness gate; does not grant permissions or execution authority."""
from datetime import datetime
import hashlib

DIAGNOSTIC_BUNDLE = 'com.trycua.driver.pointguard'
DIAGNOSTIC_EXECUTABLE = '/Users/mvpagent/CUAgentDriverDiagnostic-e4c312cc74f23058e0cf89c7c1ac1decbbab83934661601aa32847da10e81aef/CuaDriverPointGuard.app/Contents/MacOS/cua-driver-pointguard'
DIAGNOSTIC_SHA256 = '8a3aa74805cb35c527f4e338d5ee42291695f09152758fab48464aa1f7d9af64'


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


def require_business_capture_admission(receipt, daemon_report, *, desktop_review,
                                       desktop_png, **context):
    """Require a trusted operator's fresh full-VM-desktop review before dispatch.

    The digest binds reviewed bytes, not an automated semantic proof. Callers
    must collect these privately under the lifecycle lock, never from the model.
    Per-click hit testing remains mandatory after this point-in-time review.
    """
    require_current_capture_admission(receipt, daemon_report, **context)

    def require(condition):
        if not condition:
            raise ValueError('DIAGNOSTIC_DESKTOP_REVIEW_UNCONFIRMED')

    review = desktop_review
    require(type(review) is dict)
    require(set(review) == {'version', 'source', 'scope', 'runId', 'sessionId',
                           'daemonPid', 'sha256', 'observedAt', 'reviewedAt',
                           'pngSha256', 'blockingPromptAbsent'})
    require(type(review['version']) is int and review['version'] == 1)
    require(review['source'] == 'trusted-operator')
    require(review['scope'] == 'full-vm-desktop')
    require(review['blockingPromptAbsent'] is True)
    for key in ('runId', 'sessionId', 'daemonPid', 'sha256'):
        require(type(review[key]) is type(receipt[key]) and review[key] == receipt[key])
    require(type(desktop_png) is bytes and 8 < len(desktop_png) <= 16 * 1024 * 1024)
    require(desktop_png.startswith(b'\x89PNG\r\n\x1a\n'))
    require(review['pngSha256'] == hashlib.sha256(desktop_png).hexdigest())

    def stamp(value):
        require(type(value) is str)
        try:
            result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('DIAGNOSTIC_DESKTOP_REVIEW_UNCONFIRMED') from None
        require(result.tzinfo is not None and result.utcoffset() is not None)
        return result

    observed = stamp(review['observedAt'])
    reviewed = stamp(review['reviewedAt'])
    now = context['now']
    require(stamp(receipt['checkedAt']) <= observed <= reviewed <= now)
    require((now - observed).total_seconds() <= 30)
