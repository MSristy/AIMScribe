"""Optional CPU-only portable Ollama setup from the official release ZIP.

Uses HTTP ranges to omit GPU libraries. ZIP CRC checks verify member integrity;
the install report records per-file SHA256, not an independent publisher audit.
Does not modify PATH, install a service, or write outside this project.
"""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT/'.local/ollama'
URL = 'https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip'


class RemoteZip(io.RawIOBase):
    def __init__(self):
        self.position = 0
        with urlopen(Request(URL, headers={'Range': 'bytes=0-0'}), timeout=60) as response:
            if response.status != 206:
                raise ValueError('Server does not support range requests; use the official installer instead.')
            self.url = response.url
            self.size = int(response.headers['Content-Range'].split('/')[-1])
            response.read()

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position+offset if whence == 1 else self.size+offset
        return self.position

    def read(self, size=-1):
        if size < 0:
            size = self.size-self.position
        if not size:
            return b''
        end = min(self.size-1, self.position+size-1)
        with urlopen(Request(self.url, headers={'Range': f'bytes={self.position}-{end}'}), timeout=120) as response:
            if response.status != 206:
                raise ValueError('Expected HTTP 206; refusing full archive download.')
            data = response.read()
            if len(data) != end-self.position+1:
                raise ValueError('Incomplete range download.')
        self.position += len(data)
        return data


def main():
    remote = RemoteZip()
    members = []
    with zipfile.ZipFile(remote) as archive:
        for item in archive.infolist():
            # Root executable and flat shared/CPU libraries only; no CUDA/Vulkan.
            name = PurePosixPath(item.filename)
            wanted = item.filename == 'ollama.exe' or (name.parent.as_posix() == 'lib/ollama' and not item.is_dir())
            if not wanted:
                continue
            target = (DESTINATION/Path(*name.parts)).resolve()
            if not target.is_relative_to(DESTINATION.resolve()):
                raise ValueError('Unsafe archive member path.')
            data = archive.read(item)  # zipfile verifies CRC before returning.
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            members.append({'path': item.filename, 'bytes': len(data), 'compressed_bytes': item.compress_size,
                            'sha256': hashlib.sha256(data).hexdigest()})
            print('Installed', item.filename, len(data), flush=True)
    report = {'source': URL, 'archive_bytes': remote.size, 'installation': 'portable CPU only',
              'files': members, 'compressed_member_bytes': sum(m['compressed_bytes'] for m in members)}
    (DESTINATION/'install-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'files': len(members), 'downloaded_member_bytes': report['compressed_member_bytes'],
                      'executable': str(DESTINATION/'ollama.exe')}), flush=True)


if __name__ == '__main__':
    main()
