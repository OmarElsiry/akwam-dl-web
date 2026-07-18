import sys, re
sys.stdout.reconfigure(encoding='utf-8')

html = open('../scratch/debug_step4_b.html', encoding='utf-8').read()

# Look for the download button element with all its attributes
download_sections = re.findall(r'(?i)<a[^>]*download[^>]*>.*?</a>', html, re.S)
print('Download anchor elements:')
for d in download_sections[:10]:
    print(repr(d[:500]))
    print()

# Also look for file-name class
file_name = re.findall(r'class=["\'][^"\']*file-name[^"\']*["\'][^>]*>(.*?)<', html, re.S)
print('file-name elements:', file_name[:5])

# Look for any element with class 'download'
dl_class = re.findall(r'class=["\'][^"\']*\bdownload\b[^"\']*["\'][^>]*>(.*?)<', html, re.S)
print('class=download elements:', dl_class[:5])

# Look for <a class="download"
a_dl = re.findall(r'<a[^>]*class=["\'][^"\']*download[^"\']*["\'][^>]*>', html, re.I)
print('a.download tags:', a_dl[:5])
