import re
import json
import pandas as pd
from bs4 import BeautifulSoup
import ollama
from PyPDF2 import PdfReader
import pdfplumber


# ---------------------------------------------------------------
# 1. HTML Quality Checker
# ---------------------------------------------------------------
def is_html_malformed(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")

    if len(rows) < 3:
        return True

    for r in rows:
        tds = r.find_all("td")
        if 0 < len(tds) <= 2:
            return True

    return False

def fix_bad_unicode(text):
    try:
        return text.encode("latin1").decode("utf-8")
    except:
        return text  # return original if decoding fails


def extract_json_array(text):
    match = re.search(r"\[[\s\S]*\]", text)
    return match.group(0) if match else None

def remove_empty_rows(data):
    cleaned = []

    for row in data:
        # remove rows where ALL values are empty after stripping
        if any(str(v).strip() for v in row.values()):
            cleaned.append(row)

    return cleaned

def fix_unicode_dict(d):
    return {k: fix_bad_unicode(v) if isinstance(v, str) else v for k, v in d.items()}


def extract_full_page_text(pdf_path):
    reader = PdfReader(pdf_path)
    full_text = ""

    for page in reader.pages:
        t = page.extract_text()
        if t:
            full_text += "\n" + t

    return full_text


def extract_table_pdfplumber_transposed(pdf_path):
   

    with pdfplumber.open(pdf_path) as pdf:
        tables = pdf.pages[0].extract_tables()

    if not tables:
        return None

    table = tables[0]
    table = [[cell or "" for cell in row] for row in table]

    header_idx = next(
        (i for i, r in enumerate(table) if any("S.No" in str(c) for c in r)),
        None
    )
    if header_idx is None:
        return None

    headers = table[header_idx]
    data_row = table[header_idx + 1]
    
    material_description = data_row[1]
    print("Material Description cell:", material_description)

    # split multiline columns
    cols = [col.split("\n") for col in data_row]
    cols = [[x.strip() for x in col if x.strip()] for col in cols]

    max_len = max(len(col) for col in cols)

    for i in range(len(cols)):
        if len(cols[i]) < max_len:
            cols[i] += [""] * (max_len - len(cols[i]))

    rows = []
    for r in range(max_len):
        row = {headers[c]: cols[c][r] for c in range(len(headers))}
        rows.append(row)
        

    return  material_description,pd.DataFrame(rows)

# def extract_description_block(text):
#     """
#     Extracts only the MATERIAL DESCRIPTION text block.
#     """
#     import re

#     # Everything between "Material" and next known column (Item, HSN, Batch…)
#     patt = re.compile(
#         r"Material\s*Description[\s:]*([\s\S]*?)(?=\b(Item\s*Code|HSN|Qty|Batch)\b)",
#         re.IGNORECASE
#     )

#     m = patt.search(text)
#     if not m:
#         return ""

#     block = m.group(1).strip()
#     return block

def extract_descriptions_gemma(material_description):

    prompt = f"""
    Extract distinct items from the text.
 
        Rules:
        - Merge lines belonging to the same item.
        - Each item appears once.
        - Include only explicit attributes.
        - Do not infer missing data.
        - Ignore formatting noise.
        
        Output:
        - Return ONLY a Python list of strings.
        - Format: "ITEM NAME – attributes"
        - Use "–" as separator.
        
        Text:
        
        {material_description}
        """
    

    response = ollama.chat(
        model="gemma3:4b",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response["message"]["content"]
    print("Gemma output:\n", text)

    # # Clean JSON
    # text = text.strip()
    # if text.startswith("```"):
    #     text = text.split("```")[1]
    # if text.endswith("```"):
    #     text = text.rsplit("```")[0]

    cleaned = extract_json_array(text)
    descriptions = json.loads(cleaned)
    return descriptions


    
    


def extract_descriptions(pdf_path):
    reader = PdfReader(pdf_path)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    items = []
    current = None

    sno_pattern = re.compile(r"^\s*(\d{1,3})\b\s*(.*)$")

    for line in full_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        match = sno_pattern.match(line)
        if match:
            sno, first_desc = match.groups()

            if current:
                items.append(current)

            current = {"sno": sno, "desc": [first_desc]}
        else:
            if current:
                current["desc"].append(line)

    if current:
        items.append(current)

    # Convert into lookup dict
    return {item["sno"]: " ".join(item["desc"]).strip() for item in items}

def merge_descriptions(df, descriptions):
    df = df.copy()

    # Find any column containing 'Description'
    desc_col = next((c for c in df.columns if "Description" in c), None)
    print("Description column found:", desc_col)

    if not desc_col:
        print("❌ No description column found in DF")
        return df

    n_rows = len(df)
    n_desc = len(descriptions)

    print(f"DF rows = {n_rows}, Description count = {n_desc}")

    # ---- FIX LENGTH MISMATCH ----
    if n_desc < n_rows:
        descriptions = descriptions + [""] * (n_rows - n_desc)
    elif n_desc > n_rows:
        descriptions = descriptions[:n_rows]

    df[desc_col] = descriptions

    print("✔ Merged descriptions correctly.")
    return df



# ---------------------------------------------------------------
# 3. Cleaning model output
# ---------------------------------------------------------------
def clean_model_output(raw):
    raw = raw.strip()

    if raw.startswith("```"):
        raw = raw.split("```", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]

    raw = raw.replace("json\n", "").replace("json\r\n", "")
    return raw.strip()


# ---------------------------------------------------------------
# 4. Gemma extractor (for correct HTML)
# ---------------------------------------------------------------
def extract_items_gemma(html):

    prompt = f"""
    You are an expert invoice parser. Extract clean structured JSON from this invoice HTML.
    Missing values = empty string.
    Return ONLY JSON.

    HTML:
    {html}
    """

    response = ollama.chat(
        model="gemma3:4b",
        messages=[{"role": "user", "content": prompt}]
    )

    cleaned = clean_model_output(response["message"]["content"])

    try:
        parsed = json.loads(cleaned)
        with open("output/Goyal_Medical_Agency.json", "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=4, ensure_ascii=False)
            print("\n✔ JSON saved to output/Goyal_Medical_Agency.json")
        return pd.DataFrame(parsed.get("items", []))
    except:
        print("❌ Gemma returned invalid JSON → switching to fallback regex")
        # text = BeautifulSoup(html, "html.parser").get_text("\n")
        # return extract_items(text)


# ---------------------------------------------------------------
# 5. MAIN HYBRID EXTRACTOR
# ---------------------------------------------------------------
def extract_invoice_items(pdf_path, md5_html):

    # Step 1: check if HTML from md5 is malformed
    if is_html_malformed(md5_html):
        print("⚠ MD5 HTML collapsed — Using Hybrid pdfplumber + PyPDF2")

        material_description,df = extract_table_pdfplumber_transposed(pdf_path)
        
        
        full_text = extract_full_page_text(pdf_path)

    # STEP 2 — Extract the description block

        # STEP 3 — Get clean descriptions via Gemma
        descriptions = extract_descriptions_gemma(material_description)

        # STEP 4 — Merge back into df
        df_final = merge_descriptions(df, descriptions)



        # if df is None:
        #     print("⚠ pdfplumber failed → no table found.")
        #     return pd.DataFrame()

        # # (B) extract long descriptions
        # desc_map = extract_descriptions(pdf_path)

        # # (C) merge description column
        # df = merge_description(df, desc_map)

        

        json_data = df_final.to_dict(orient="records")
        
        json_data = [fix_unicode_dict(row) for row in json_data]
        
        print("Final extracted data:", json_data)

        
        with open("output/Goyal_Medical_Agency.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        
        
        with open("output/Goyal_Medical_Agency.json") as f:
            data = json.load(f)

        cleaned = remove_empty_rows(data)

        with open("output/Goyal_Medical_Agency.json", "w") as f:
            json.dump(cleaned, f, indent=4)    
            
        
        return  df_final

    else:
        print("✔ HTML OK → Using Gemma")
        return extract_items_gemma(html)


# ---------------------------------------------------------------
# RUN IT
# ---------------------------------------------------------------
with open("output/Goyal_Medical_Agency.md", "r", encoding="utf-8") as f:
    html = f.read()

df = extract_invoice_items(r"data/GOYAL MEDICAL AGENCY NAGAUR.pdf",html)
print(df)
