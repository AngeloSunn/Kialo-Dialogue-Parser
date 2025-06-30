import os
import re
import json
from negate import Negator
from collections import defaultdict
from datetime import datetime

negator = Negator()

def build_db_entries(statements, arguments, premises, url_lookup):
    db_statements = []
    db_counter_statements = []
    db_acp = []
    db_source_manual = []
    db_source_retrieval = []
    db_source_generated = []

    now = datetime.now().isoformat(sep=' ', timespec='seconds')
    statement_id_map = {}
    next_id = 1

    for s in statements:
        statement_id_map[s["id"]] = next_id
        s["_db_id"] = next_id  
        next_id += 1

    for s in statements:
        kind = "retrieved" if s.get("tag") != "generated" else "generated"
        db_statements.append({
            "statement_id": s["_db_id"],
            "text": s["text"],
            "created_at": now,
            "kind": kind,
            "predecessor": None, 
            "successor": None     
        })

        if kind == "retrieved":
            db_source_retrieval.append({
                "statement_id": s["_db_id"],
                "name": "Kialo",
                "url": url_lookup.get(s["source"], "UNKNOWN"),
                "text_raw": s["text"]
            })
        else:
            db_source_generated.append({
                "statement_id": s["_db_id"],
                "model": "Negator",
                "version": "1.1.6",  # found in requirements.txt
                "text_raw": s["text"]
            })

        if s.get("tag") == "generated":
            orig_id = statement_id_map[s["counter_to"]]
            counter_id = s["_db_id"]
            db_counter_statements.append({
                "statement_id": orig_id,
                "counterstatement_id": counter_id
            })

    # Map arguments
    for arg in arguments:
        claim_id = statement_id_map[arg["claim"]]
        arg_id = int(arg["id"].split("-")[1])  # arg-1 → 1
        for p in premises:
            if p["argument"] == arg["id"]:
                premise_id = statement_id_map[p["premise"]]
                db_acp.append({
                    "argument_id": arg_id,
                    "claim_id": claim_id,
                    "premise_id": premise_id
                })

    return {
        "statements": db_statements,
        "counter_statements": db_counter_statements,
        "acp": db_acp,
        "source_manual": db_source_manual,
        "source_generated": db_source_generated,
        "source_retrieval": db_source_retrieval
    }


def extract_statements_and_topic(file_path, file_counter):
    statements = []
    pattern = re.compile(r"((?:\d+\.)*)\s+(Thesis|Pro|Con):\s+(.*)$")
    pattern_short = re.compile(r"((?:\d+\.)*)")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f]

    i = 0
    counter = 0
    id_map = {}
    
    topic = lines[1].strip()

    while (i + 2) < len(lines):
        line1 = lines[i].strip()
        match = pattern_short.match(line1)

        if match:
            line2 = lines[i+1].strip()
            line3 = lines[i+2].strip()
            lines_combined = ' '.join([line1, line2, line3])
            match = pattern.match(lines_combined)

            if match:
                label, claim_type, full_text = match.groups()
                label = label.strip('.')
                counter += 1
                st_id = f"st-{counter}"
                gen_id = f"st-{counter}-gen"
                source = f"kialo-{file_counter}"
                id_map[label] = st_id

                statements.append({
                    "id": st_id,
                    "text": full_text,
                    "tag": "",
                    "counter_to": gen_id,
                    "source": source
                })

                negation = negator.negate_sentence(full_text)

                statements.append({
                    "id": gen_id,
                    "text": negation,
                    "tag": "generated",
                    "counter_to": st_id,
                    "source": source
                })
                i += 3
            else:
                i += 1
        else:
            i += 1

    return statements, id_map, topic


def extract_arguments(id_map, file_counter):
    arguments = []
    premises_map = defaultdict(list)
    argument_counter = 1
    tree = defaultdict(list)

    for label in id_map:
        if '.' in label:
            parent = '.'.join(label.split('.')[:-1])
            tree[parent].append(label)

    for parent, children in tree.items():
        if parent not in id_map:
            continue
        claim_id = id_map[parent]
        arg_id = f"arg-{argument_counter}"
        source = f"kialo-{file_counter}"
        argument_counter += 1

        arguments.append({
            "id": arg_id,
            "claim": claim_id,
            "source": source
        })

        for child in children:
            if child in id_map:
                premises_map[arg_id].append(id_map[child])

    return arguments, premises_map


def extract_premises(premises_map):
    premises = []
    for arg_id, premise_ids in premises_map.items():
        for pid in premise_ids:
            premises.append({
                "argument": arg_id,
                "premise": pid
            })
    return premises


def extract_source(title, url):
    return [{
        "name": "Kialo",
        "topic": title,
        "text": "Full Kialo Text",
        "url": url
    }]

def filename_to_url(filename):
    slug = filename.split(".txt")[0]
    return f"https://www.kialo.com/{slug}"


def process_topics(dir):
    counter = 1
    url_lookup = {}  # source_name → URL

    for filename in os.listdir(dir):
        input_filename = filename 
        output_filename = filename.replace(".txt", ".json")
        input_path = os.path.join("discussions", input_filename)
        output_path = os.path.join("parser_output", output_filename)
        source_name = f"kialo-{counter}"
        url_lookup[source_name] = filename_to_url(input_filename)

        if not os.path.exists(input_path):
            print(f"Missing: {input_path}")
            continue

        print(f"Processing: {input_path} -> {output_path}")
        statements, id_map, topic = extract_statements_and_topic(input_path, counter)
        arguments, premises_map = extract_arguments(id_map, counter)
        premises = extract_premises(premises_map)
        sources = extract_source(topic, url_lookup[source_name])
            
        db_entries = build_db_entries(statements, arguments, premises, url_lookup)

        os.makedirs("parser_output", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as db_out:
            json.dump(db_entries, db_out, indent=2, ensure_ascii=False)

        print(f"Saved: {output_path}")
        counter += 1

if __name__ == "__main__":
    topics_dir = "discussions"  
    process_topics(topics_dir)
