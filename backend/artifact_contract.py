"""Task-bound download names; never a GUI success verifier."""


def artifact_names(payload):
    if 'kind' not in payload:
        return ('report.json', 'report.md')
    if payload['kind'] == 'desktop-textedit':
        return ('document.txt', 'result.txt')
    return ()  # Unknown task types never gain a download capability.


def media_type(name):
    if name == 'report.json':
        return 'application/json'
    if name == 'report.md':
        return 'text/markdown'
    return 'text/plain'
