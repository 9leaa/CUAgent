"""Read only attachments named by independently matched original observations.

Layout verified against the installed official attachment-local implementation.
No directory enumeration, writes, image conversion, or model-controlled paths.
Caller supplies the trusted project Harness home and matched observation list.
"""
import hashlib
import os
from pathlib import Path
import re
import stat


def require(condition):
    if not condition:
        raise ValueError('HANDOFF_ATTACHMENT_COLLECTION_UNVERIFIED')


def read_handoff_attachments(home, observations):
    require(type(observations) is list and 0 < len(observations) <= 30)
    refs, snapshots, last_used = {}, set(), 0
    for observation in observations:
        require(type(observation) is dict and set(observation) == {'snapshotId', 'used', 'attachment'})
        snapshot, used = observation['snapshotId'], observation['used']
        require(type(snapshot) is str and bool(snapshot) and snapshot not in snapshots
                and type(used) is int and last_used < used <= 30)
        snapshots.add(snapshot); last_used = used
        ref = observation['attachment']
        require(type(ref) is dict and set(ref) in (
            {'attachmentId', 'mediaType', 'bytes', 'width', 'height'},
            {'attachmentId', 'mediaType', 'bytes', 'width', 'height', 'name'}))
        key = ref['attachmentId']
        require(type(key) is str and re.fullmatch(r'sha256:[0-9a-f]{64}', key)
                and ref['mediaType'] in ('image/png', 'image/webp')
                and all(type(ref[k]) is int and ref[k] > 0 for k in ('bytes', 'width', 'height')))
        require(ref['bytes'] <= 8 * 1024 * 1024)
        metadata = {k: v for k, v in ref.items() if k != 'name'}
        require(key not in refs or refs[key] == metadata)
        refs[key] = metadata  # Display name is never used as a filesystem path.
    require(sum(ref['bytes'] for ref in refs.values()) <= 64 * 1024 * 1024)
    home = Path(home).absolute()
    require(home.resolve(strict=True) == home)
    root = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    def directory(info):
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077)
        return (info.st_dev, info.st_ino, info.st_uid, info.st_mode)
    def signature(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink, info.st_mode, info.st_uid)
    try:
        root_identity = directory(os.fstat(root))
        def read(key):
            digest = key[7:]
            parent = os.dup(root)
            chain = []
            try:
                for component in ('attachments', 'v1', 'objects', digest[:2]):
                    child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    os.close(parent); parent = child
                    chain.append(directory(os.fstat(parent)))
                fd = os.open(digest, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(fd, 'rb') as stream:
                    before = os.fstat(stream.fileno())
                    require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
                            and not before.st_mode & 0o077 and before.st_nlink == 1
                            and before.st_size == refs[key]['bytes'])
                    raw = stream.read(before.st_size + 1)
                    after = os.fstat(stream.fileno())
                require(len(raw) == before.st_size and signature(before) == signature(after)
                        == signature(os.stat(digest, dir_fd=parent, follow_symlinks=False)))
                require(hashlib.sha256(raw).hexdigest() == digest)
                if refs[key]['mediaType'] == 'image/png': require(raw.startswith(b'\x89PNG\r\n\x1a\n'))
                else: require(len(raw) >= 12 and raw[:4] == b'RIFF' and raw[8:12] == b'WEBP')
                return raw, signature(after), chain
            finally:
                os.close(parent)
        collected = {key: read(key) for key in refs}
        for key, original in collected.items(): require(read(key) == original)
        require(home.resolve(strict=True) == home and directory(home.stat(follow_symlinks=False)) == root_identity)
        return {key: entry[0] for key, entry in collected.items()}
    finally:
        os.close(root)
