import json
from fairness_engine.anonymizer import redact_header, build_candidate_id_map

header = json.load(open('data/segmented/rohan_mehta_docx_sections.json', encoding='utf-8'))['sections']['HEADER']
print("Original:", header)
print("Redacted:", redact_header(header))

print()
id_map = build_candidate_id_map('data/segmented')
print("Total mapped:", len(id_map))
print("rohan_mehta_docx ->", id_map.get('rohan_mehta_docx'))
print("divya_menon_docx ->", id_map.get('divya_menon_docx'))