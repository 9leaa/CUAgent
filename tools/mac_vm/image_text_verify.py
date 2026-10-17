"""Offline screenshot text evidence. Never grants a desktop action permission."""
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile


def dimensions(png):
    if (not isinstance(png, bytes) or not 33 <= len(png) <= 20 * 1024 * 1024
            or png[:8] != b'\x89PNG\r\n\x1a\n' or png[8:16] != b'\0\0\0\rIHDR'):
        raise ValueError('bounded PNG required')
    width, height = struct.unpack('>II', png[16:24])
    if not 0 < width <= 16384 or not 0 < height <= 16384:
        raise ValueError('bounded PNG dimensions required')
    return width, height


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def verify_region_text(png, report, *, region, expected):
    """Caller must obtain report from its pinned recognizer, never the model.

    Region is trusted (left, top, right, bottom) in original screenshot pixels.
    Reject any extra/partial text overlapping the region; no normalization,
    substring match or expected-text hint is sent to the recognizer.
    """
    width, height = dimensions(png)
    sha = hashlib.sha256(png).hexdigest()
    if (not isinstance(report, dict) or type(report.get('version')) is not int or report['version'] != 1
            or report.get('engine') != 'AppleVision' or report.get('sha256') != sha
            or type(report.get('width')) is not int or report['width'] != width
            or type(report.get('height')) is not int or report['height'] != height):
        raise ValueError('recognition must bind original PNG')
    if (not isinstance(region, (list, tuple)) or len(region) != 4
            or not all(_finite(v) for v in region)
            or not 0 <= region[0] < region[2] <= width
            or not 0 <= region[1] < region[3] <= height
            or not isinstance(expected, str) or not 0 < len(expected.encode()) <= 256):
        raise ValueError('trusted bounded region and expected text required')
    items = report.get('items')
    if not isinstance(items, list) or len(items) > 20000:
        raise ValueError('bounded recognition results required')
    matches = []
    left, top, right, bottom = region
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('invalid recognition item')
        rect, confidence, text = item.get('rect'), item.get('confidence'), item.get('text')
        if (not isinstance(rect, list) or len(rect) != 4 or not all(_finite(v) for v in rect)
                or not _finite(confidence) or not 0 <= confidence <= 1
                or not isinstance(text, str) or len(text.encode()) > 65536):
            raise ValueError('invalid recognition item')
        x, y, w, h = rect
        if not (0 <= x < x+w <= width and 0 <= y < y+h <= height):
            raise ValueError('invalid recognition rectangle')
        if x < right and x+w > left and y < bottom and y+h > top:
            if not (left <= x and x+w <= right and top <= y and y+h <= bottom):
                raise ValueError('text crosses trusted region')
            matches.append(item)
    if len(matches) != 1 or matches[0]['confidence'] < .9 or matches[0]['text'] != expected:
        raise ValueError('unique high-confidence exact text required')
    return dict(status='REGION_TEXT_OBSERVED', sha256=sha, region=list(region),
                text=expected, confidence=matches[0]['confidence'],
                inputPermitted=False, actionEffectVerified=False)


def recognize_png(png, *, executable, executable_sha256):
    """Pinned offline helper; receives pixels only, never expected text."""
    dimensions(png)
    path = Path(executable)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError('canonical recognizer required')
    metadata = path.stat()
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o022 or not os.access(path, os.X_OK)
            or hashlib.sha256(path.read_bytes()).hexdigest() != executable_sha256):
        raise ValueError('pinned owned recognizer required')
    with tempfile.TemporaryDirectory(prefix='cuagent-image-text-') as directory:
        image = Path(directory) / 'input.png'
        image.write_bytes(png)
        image.chmod(0o400)
        result = subprocess.run([str(path), str(image)], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if (result.returncode != 0 or not 0 < len(result.stdout) <= 2 * 1024 * 1024
                or image.read_bytes() != png
                or hashlib.sha256(path.read_bytes()).hexdigest() != executable_sha256):
            raise ValueError('recognition unconfirmed')
        report = json.loads(result.stdout)
    if not isinstance(report, dict) or report.get('sha256') != hashlib.sha256(png).hexdigest():
        raise ValueError('recognition image changed')
    return report
