file_path = 'prefect/tests/fixtures/post_metrics.json'
with open(file_path, 'r') as f:
    content = f.read()

offset = 13773
start = max(0, offset - 50)
end = min(len(content), offset + 50)
print(f"Context: {content[start:end]}")
print(f"Char at {offset}: '{content[offset]}'")
