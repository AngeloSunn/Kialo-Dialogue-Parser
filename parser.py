import os
import re
import json
from negate import Negator
from collections import defaultdict

negator = Negator()

def extract_statements_and_topic(file_path):
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
                id_map[label] = st_id

                statements.append({
                    "id": st_id,
                    "text": full_text,
                    "tag": "",
                    "counter_to": gen_id,
                    "source": "kialo-1"
                })

                negation = negator.negate_sentence(full_text)

                statements.append({
                    "id": gen_id,
                    "text": negation,
                    "tag": "generated",
                    "counter_to": st_id,
                    "source": "kialo-1"
                })

                i += 3
            else:
                i += 1
        else:
            i += 1

    return statements, id_map, topic


def extract_arguments(id_map):
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
        argument_counter += 1

        arguments.append({
            "id": arg_id,
            "claim": claim_id,
            "source": "kialo-1"
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


def extract_source(title, url, counter):
    return [{
        "name": "kialo-" + str(counter),
        "topic": title,
        "text": "Full Kialo Text",
        "url": url
    }]


def url_to_filename(url):
    slug = url.split("https://www.kialo.com/")[-1]
    return slug + ".txt", slug + ".json"


def process_topic_file(topic_file):
    with open(topic_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip() and line.startswith("http")]

    counter = 1

    for url in lines:
        input_filename, output_filename = url_to_filename(url)
        input_path = os.path.join("discussions", input_filename)
        output_path = os.path.join("output", output_filename)

        if not os.path.exists(input_path):
            print(f"Missing: {input_path}")
            continue

        print(f"🔍 Processing: {input_path} -> {output_path}")
        statements, id_map, topic = extract_statements_and_topic(input_path)
        arguments, premises_map = extract_arguments(id_map)
        premises = extract_premises(premises_map)
        sources = extract_source(topic, url, counter)

        os.makedirs("output", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as out:
            json.dump({
                "statements": statements,
                "arguments": arguments,
                "premises": premises,
                "sources": sources
            }, out, indent=2, ensure_ascii=False)

        print(f"Saved: {output_path}")
        counter += 1

if __name__ == "__main__":
    topic_file = "topics.txt"  
    process_topic_file(topic_file)
