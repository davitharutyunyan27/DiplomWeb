

from flask import Flask, render_template, request, jsonify, send_file
import ast
import random
import string
import io
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB max upload

XOR_KEY = int(os.getenv('XOR_KEY'))

DECRYPT_HELPER = f"""def _xd(data, k={XOR_KEY}):
    return ''.join(chr(b ^ k) for b in data)
"""

DEAD_CODE_TEMPLATES = [
    "while False:\n    pass",
    "if 1 == 2:\n    raise RuntimeError('dead branch')",
    "_dead_{{uid}} = [x * 3 for x in range(20)]",
    "try:\n    pass\nexcept Exception:\n    pass",
    "if False:\n    _noop_{{uid}} = 'unreachable'",
    "_sink_{{uid}} = sum(i**2 for i in range(10))",
]

PROTECTED_NAMES = {
    "print", "range", "len", "sum", "str", "int", "float", "list",
    "dict", "set", "tuple", "bool", "None", "True", "False",
    "open", "input", "type", "isinstance", "hasattr", "getattr",
    "setattr", "enumerate", "zip", "map", "filter", "sorted",
    "append", "extend", "update", "keys", "values", "items",
    "split", "join", "strip", "startswith", "endswith", "encode",
    "decode", "hexdigest", "format", "ord", "chr",
    "Exception", "RuntimeError", "ValueError", "TypeError",
    "self", "cls", "return", "import", "from", "as",
}


class IdentifierRenamer(ast.NodeTransformer):
    def __init__(self):
        self.mapping = {}

    def _get_name(self, original):
        if original in PROTECTED_NAMES:
            return original
        if original not in self.mapping:
            while True:
                candidate = (
                    random.choice(string.ascii_letters) +
                    ''.join(random.choices(string.ascii_letters + string.digits, k=5))
                )
                if candidate not in self.mapping.values():
                    self.mapping[original] = candidate
                    break
        return self.mapping[original]

    def visit_FunctionDef(self, node):
        node.name = self._get_name(node.name)
        for arg in node.args.args:
            arg.arg = self._get_name(arg.arg)
        self.generic_visit(node)
        return node

    def visit_Name(self, node):
        node.id = self._get_name(node.id)
        return node


class StringEncryptor(ast.NodeTransformer):
    def __init__(self):
        self.encrypted_count = 0

    def visit_Constant(self, node):
        if not isinstance(node.value, str) or not node.value:
            return node
        encrypted = [ord(c) ^ XOR_KEY for c in node.value]
        self.encrypted_count += 1
        call_node = ast.Call(
            func=ast.Name(id='_xd', ctx=ast.Load()),
            args=[ast.List(elts=[ast.Constant(value=b) for b in encrypted], ctx=ast.Load())],
            keywords=[]
        )
        return ast.copy_location(call_node, node)


def _random_uid():
    return ''.join(random.choices(string.ascii_lowercase, k=4))


def _indent(code, spaces=4):
    pad = " " * spaces
    return "\n".join(pad + line for line in code.splitlines())


def inject_dead_code(source, injections_per_function=2):
    lines = source.splitlines()
    output_lines = []
    total_injected = 0
    for line in lines:
        output_lines.append(line)
        stripped = line.strip()
        if stripped.startswith("def ") and stripped.endswith(":"):
            base_indent = len(line) - len(line.lstrip())
            body_indent = base_indent + 4
            for _ in range(injections_per_function):
                template = random.choice(DEAD_CODE_TEMPLATES)
                snippet = template.replace("{uid}", _random_uid())
                indented = _indent(snippet, body_indent)
                output_lines.append(indented)
                total_injected += len(indented.splitlines())
    return "\n".join(output_lines), total_injected


def obfuscate(source, do_rename=True, do_strings=True, do_dead=True, dead_count=2):
    stats = {
        "identifiers_renamed": 0,
        "strings_encrypted": 0,
        "dead_lines_injected": 0,
        "original_lines": len(source.splitlines()),
        "obfuscated_lines": 0,
        "name_mapping": {},
    }
    result = source

    if do_dead:
        result, injected = inject_dead_code(result, injections_per_function=dead_count)
        stats["dead_lines_injected"] = injected

    if do_strings:
        tree = ast.parse(result)
        enc = StringEncryptor()
        new_tree = enc.visit(tree)
        ast.fix_missing_locations(new_tree)
        result = DECRYPT_HELPER + "\n" + ast.unparse(new_tree)
        stats["strings_encrypted"] = enc.encrypted_count

    if do_rename:
        tree = ast.parse(result)
        renamer = IdentifierRenamer()
        new_tree = renamer.visit(tree)
        ast.fix_missing_locations(new_tree)
        result = ast.unparse(new_tree)
        stats["identifiers_renamed"] = len(renamer.mapping)
        stats["name_mapping"] = renamer.mapping

    stats["obfuscated_lines"] = len(result.splitlines())
    return result, stats


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/obfuscate", methods=["POST"])
def obfuscate_route():
    data = request.get_json()
    if not data or "source" not in data:
        return jsonify({"error": "No source code provided."}), 400

    source = data["source"].strip()
    if not source:
        return jsonify({"error": "Source code is empty."}), 400

    # Parse options
    do_rename  = data.get("rename", True)
    do_strings = data.get("strings", True)
    do_dead    = data.get("dead", True)
    dead_count = int(data.get("dead_count", 2))

    try:
        ast.parse(source)
    except SyntaxError as e:
        return jsonify({"error": f"Syntax error in your code: {e}"}), 400

    try:
        obfuscated, stats = obfuscate(source, do_rename, do_strings, do_dead, dead_count)
        return jsonify({"obfuscated": obfuscated, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    code = data.get("code", "")
    buf = io.BytesIO(code.encode("utf-8"))
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="obfuscated.py", mimetype="text/x-python")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
