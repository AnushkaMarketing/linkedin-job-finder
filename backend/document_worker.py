"""Bounded parser subprocess. No document macros or embedded code are executed."""
import io
import json
import sys
import zipfile

MAX_BYTES = 5 * 1024 * 1024


def extract(blob: bytes, extension: str) -> str:
    if len(blob) > MAX_BYTES: raise ValueError('Maximum file size is 5 MB')
    if extension == '.txt': return blob.decode('utf-8-sig')[:100_000]
    if extension == '.pdf':
        if not blob.startswith(b'%PDF-'): raise ValueError('Invalid PDF signature')
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(blob), strict=True)
        if reader.is_encrypted: raise ValueError('Password-protected PDFs are not supported')
        if len(reader.pages) > 40: raise ValueError('CV must contain at most 40 pages')
        text = '\n'.join((p.extract_text() or '')[:20_000] for p in reader.pages)
        if len(text.strip()) < 20: raise ValueError('No readable text. Paste text or OCR a scanned PDF first.')
        return text[:100_000]
    if extension == '.docx':
        from defusedxml.ElementTree import fromstring
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            entries = archive.infolist()
            if len(entries) > 1000 or sum(e.file_size for e in entries) > 20_000_000:
                raise ValueError('DOCX decompression limit exceeded')
            if any(e.file_size / max(1, e.compress_size) > 250 for e in entries):
                raise ValueError('Suspicious DOCX compression ratio')
            xml = fromstring(archive.read('word/document.xml'))
            ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            return '\n'.join(''.join(p.itertext()) for p in xml.iter(ns + 'p'))[:100_000]
    raise ValueError('Use PDF, DOCX or UTF-8 TXT')


if __name__ == '__main__':
    try:
        # -I excludes the script directory from sys.path; load trusted sibling explicitly.
        from pathlib import Path
        import importlib.util
        spec = importlib.util.spec_from_file_location('parser_limits', Path(__file__).with_name('parser_limits.py'))
        limits = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(limits)
        limits.contain()
        print(json.dumps({'text': extract(sys.stdin.buffer.read(MAX_BYTES + 1), sys.argv[1])}))
    except Exception as exc:
        print(json.dumps({'error': str(exc)[:250]}))
        sys.exit(1)
