# PyShield — Python Obfuscation Web Tool
### Diploma Work — Software Protection

---

## Project Structure

```
obfuscator/
├── app.py               ← Flask backend + obfuscation engine
├── requirements.txt     ← Python dependencies
├── README.md
└── templates/
    └── index.html       ← Frontend UI
```

---

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the server
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## Features

| Technique            | Description                                                      |
|----------------------|------------------------------------------------------------------|
| Identifier Renaming  | Replaces all variable/function names with random strings via AST |
| String Encryption    | XOR-encrypts all string literals; runtime decryption injected    |
| Dead Code Insertion  | Adds unreachable code blocks to inflate control flow graph       |

- Upload `.py` files directly
- Toggle each technique independently
- Control dead code intensity with a slider
- Live stats: renamed identifiers, encrypted strings, size growth
- Download obfuscated output as `obfuscated.py`

---

## API

**POST /obfuscate**
```json
{
  "source": "def hello(): ...",
  "rename": true,
  "strings": true,
  "dead": true,
  "dead_count": 2
}
```
Returns:
```json
{
  "obfuscated": "...",
  "stats": {
    "identifiers_renamed": 5,
    "strings_encrypted": 3,
    "dead_lines_injected": 8,
    "original_lines": 12,
    "obfuscated_lines": 22
  }
}
```

**POST /download**
```json
{ "code": "...obfuscated source..." }
```
Returns: `obfuscated.py` file download.
