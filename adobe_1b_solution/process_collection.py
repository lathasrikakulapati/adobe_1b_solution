import json
import fitz
from pathlib import Path
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def parse_pdf(path):
    doc = fitz.open(path)
    content = []
    for i, page in enumerate(doc, start=1):
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        txt = span["text"].strip()
                        if txt:
                            content.append({
                                "text": txt,
                                "page": i,
                                "size": span["size"],
                                "flags": span["flags"]
                            })
    return content

def rank_content(items, persona, task):
    query = persona + " " + task
    texts = [item["text"] for item in items]
    tfidf = TfidfVectorizer(stop_words="english")
    vecs = tfidf.fit_transform([query] + texts)
    scores = cosine_similarity(vecs[0], vecs[1:]).flatten()
    for i, s in enumerate(scores):
        items[i]["score"] = s
    return sorted(items, key=lambda x: x["score"], reverse=True)

def run(input_json, input_dir, output_json):
    with open(input_json, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    role = cfg["persona"]["role"]
    task = cfg["job_to_be_done"]["task"]
    docs = cfg["documents"]

    data = []
    for doc in docs:
        path = Path(input_dir) / doc["filename"]
        parts = parse_pdf(path)
        for part in parts:
            part["document"] = doc["filename"]
        data.extend(parts)

    ranked = rank_content(data, role, task)
    top = ranked[:10]

    result = {
        "metadata": {
            "input_documents": [d["filename"] for d in docs],
            "persona": role,
            "job_to_be_done": task,
            "processing_timestamp": datetime.now().isoformat()
        },
        "extracted_sections": [
            {
                "document": item["document"],
                "section_title": item["text"][:100],
                "importance_rank": i + 1,
                "page_number": item["page"]
            }
            for i, item in enumerate(top)
        ],
        "subsection_analysis": [
            {
                "document": item["document"],
                "refined_text": item["text"],
                "page_number": item["page"]
            }
            for item in top
        ]
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    in_dir = Path("/app/input")
    out_dir = Path("/app/output")
    out_dir.mkdir(parents=True, exist_ok=True)

    in_json = in_dir / "challenge1b_input.json"
    out_json = out_dir / "challenge1b_output.json"

    run(in_json, in_dir, out_json)
