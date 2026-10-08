"""Render synthetic source receipts, never a reconciled result. Needs reportlab."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas


def render(receipt):
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(420, 480), invariant=1, pageCompression=1)
    canvas.setTitle('Synthetic expense test receipt')
    canvas.setAuthor('CUAgent test fixtures')
    canvas.setFillColorRGB(0.1, 0.2, 0.3)
    canvas.rect(0, 395, 420, 85, fill=1, stroke=0)
    canvas.setFillColorRGB(1, 1, 1)
    canvas.setFont('Helvetica-Bold', 18)
    canvas.drawString(30, 440, 'SYNTHETIC TEST ONLY')
    canvas.setFont('Helvetica', 11)
    canvas.drawString(30, 415, 'NOT VALID FOR PAYMENT')
    canvas.setFillColorRGB(0.1, 0.1, 0.1)
    rows = [('Receipt number', receipt['number']), ('Merchant', receipt['merchant']),
            ('Date', receipt['date']), ('Currency', 'CNY'),
            ('Amount', receipt['amount'] if receipt['amount'] is not None else '[OBSCURED]')]
    for index, (label, value) in enumerate(rows):
        y = 355 - index * 52
        canvas.setFont('Helvetica', 10)
        canvas.drawString(30, y, label)
        canvas.setFont('Helvetica-Bold', 15)
        canvas.drawString(30, y - 21, value)
    canvas.setFont('Helvetica', 9)
    canvas.drawString(30, 58, 'Fictional merchant. No real purchase or payment.')
    canvas.drawString(30, 42, 'Obscured fields are unknown, not zero. Page 1 of 1.')
    canvas.showPage()
    canvas.save()
    return stream.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name('cases.json').read_text())
    # Refuse overwriting an existing fixture generation, including partial output.
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for name, case in cases.items():
        directory = args.output / name
        directory.mkdir()
        originals = {}
        entries = []
        for receipt in case['receipts']:
            data = originals[receipt['copyOf']] if 'copyOf' in receipt else render(receipt)
            originals[receipt['id']] = data
            filename = receipt['id'] + '.pdf'
            with (directory / filename).open('xb') as target:
                target.write(data)
            entries.append(dict(id=receipt['id'], sha256=hashlib.sha256(data).hexdigest(),
                                sizeBytes=len(data), mediaType='application/pdf', pageCount=1))
        manifest[name] = entries
    with (args.output / 'manifest.json').open('x') as target:
        json.dump(manifest, target, ensure_ascii=False, indent=2)
        target.write('\n')
    print('Generated 8 synthetic source PDFs; no model or GUI activity.')


if __name__ == '__main__':
    main()
