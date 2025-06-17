import json
from anytree import Node, RenderTree
from anytree.exporter import DotExporter
from parser import extract_statements_new

def split_text(text, max_len=40):
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        # Check if adding the next word exceeds max_len
        if len(' '.join(current_line + [word])) <= max_len:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return '\n'.join(lines)

def build_tree(statements, id_map):
    label_map = {v: k for k, v in id_map.items()}  # Reverse mapping
    node_map = {}
    root = None

    for stmt in statements:
        if stmt["tag"] == "generated":
            continue
        stmt_id = stmt["id"]
        label = label_map.get(stmt_id, "")
        # Replace double quotes with single quotes and split text nicely
        text = stmt["text"].replace('"', "'")
        text = split_text(text, max_len=40)

        node = Node(f"{label} [{stmt_id}]\n{text}")
        node_map[label] = node

    for label, node in node_map.items():
        if '.' in label:
            parent_label = '.'.join(label.split('.')[:-1])
            parent_node = node_map.get(parent_label)
            if parent_node:
                node.parent = parent_node
        else:
            root = node  # top-level Thesis node

    return root

def render_tree_pdf(root, output_file="kialo_tree.pdf"):
    # Export .dot file
    DotExporter(root).to_dotfile("kialo_tree.dot")
    
    # Use Graphviz to render it to PDF
    import subprocess
    subprocess.run(["dot", "-Tpdf", "-Gdpi=150", "kialo_tree.dot", "-o", output_file])
    print(f"✅ PDF tree generated: {output_file}")

if __name__ == "__main__":
    input_file = "kialo_input.txt"
    statements, id_map = extract_statements_new(input_file)
    root = build_tree(statements, id_map)
    render_tree_pdf(root)
