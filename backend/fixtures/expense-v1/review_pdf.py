"""Read every test PDF, verify displayed source fields, render a review contact sheet."""
import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image
from pypdf import PdfReader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases = json.loads(Path(__file__).with_name('cases.json').read_text())
    images = []
    for name, case in cases.items():
        for receipt in case['receipts']:
            path = args.assets / name / (receipt['id'] + '.pdf')
            reader = PdfReader(path)
            assert len(reader.pages) == 1 and not reader.is_encrypted
            assert not reader.get_fields()
            content = reader.pages[0].extract_text()
            for expected in ('SYNTHETIC TEST ONLY', 'NOT VALID FOR PAYMENT', 'CNY',
                             receipt['date'], receipt['merchant'], receipt['number'],
                             receipt['amount'] if receipt['amount'] is not None else '[OBSCURED]'):
                assert expected in content, (name, receipt['id'], expected)
            prefix = args.output / (name + '-' + receipt['id'])
            subprocess.run(['pdftoppm', '-r', '72', '-singlefile', '-png', str(path), str(prefix)],
                           check=True, timeout=30, capture_output=True)
            with Image.open(prefix.with_suffix('.png')) as image:
                images.append(image.convert('RGB').copy())
    sheet = Image.new('RGB', (420 * 4, 480 * 2), 'white')
    for index, image in enumerate(images):
        assert image.size == (420, 480)
        sheet.paste(image, ((index % 4) * 420, (index // 4) * 480))
    sheet.save(args.output / 'contact-sheet.png')
    print('8 PDFs parsed, source text checked and rendered; visual inspection still required.')


if __name__ == '__main__':
    main()
