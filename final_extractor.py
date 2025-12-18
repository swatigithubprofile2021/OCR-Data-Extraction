import re
from PyPDF2 import PdfReader
import pdfplumber
import pandas as pd


"""
FIELD_PATTERNS = {
    # "supplier_name": (
    #     r"(?mi)(?:\bSupplier\s*Name\b|\bSupplier\b|\bVendor\s*Name\b|\bVendor\b|\bSeller\b|\bParty\s*Name\b)"
    #     r"\s*[:\-]?\s*(.+)$"
    # ),

    # "address": (
    #     r"(?:Address|Addr|Supplier\s*Address|Billing\s*Address)"
    #     r"\s*[:\-]?\s*(.+)"
    # ),

    # "pin_code": (
    #     r"(?:Pin\s*Code|Pincode|PIN)"
    #     r"\s*[:\-]?\s*(\d{6})"
    # ),

    # "mobile": (
    #     r"(?:Mobile\s*Number|Mobile|Phone\s*No|Phone|Contact|Contact\s*No)"
    #     r"\s*[:\-]?\s*([6-9]\d{9})"
    # ),

    # "email": (
    #     r"(?:Email\s*ID|Email|E-mail|Mail)"
    #     r"\s*[:\-]?\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    # ),

    "gstin_number": (
        r"(?:GST\s*IN|GSTIN|GSTIN\s*Number|GST\s*No|GST\s*Number|GST\s*Registration\s*No)"
        r"\s*[:\-]?\s*([0-9A-Z]{15})"
    ),

    "pan_number": (
        r"(?:PAN\s*Number|PAN|Permanent\s*Account\s*Number)"
        r"\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])"
    ),

    # "state_code": (
    #     r"(?:State\s*Code|State\s*code)"
    #     r"\s*[:\-]?\s*([0-9]{2})"
    # ),

    "invoice_no": (
        r"(?:Invoice\s*No|Invoice\s*Number|Inv\s*No|Bill\s*No|Purchase\s*Invoice\s*No|PI\s*No)"
        r"\s*[:\-]?\s*([A-Za-z0-9/\-]+)"
    ),

    "invoice_date": (
        r"(?:Invoice\s*Date|Inv\s*Date|Bill\s*Date|Purchase\s*Invoice\s*Date)"
        r"\s*[:\-]?\s*([0-3]?\d/[01]?\d/[12]\d{3})"
    ),

    "grn_no": (
        r"(?:GRN\s*No|GRN)"
        r"\s*[:\-]?\s*([A-Za-z0-9\-]+)"
    ),

    "grn_date": (
        r"(?:GRN\s*Date|GRN\s*Dt)"
        r"\s*[:\-]?\s*([0-3]?\d/[01]?\d/[12]\d{3})"
    )
}
"""

FIELD_PATTERNS = {
    # ---------------------------------------------
    #  Combined Fields: Invoice No/Date (same line)
    # ---------------------------------------------
    "invoice_combined": (
       r"(?mi)Invoice\s*No\.?(?:\s*/\s*Date)?\s*[:\-]?\s*"
       r"([A-Za-z0-9\-\/]+)\s+(([0-3]?\d[\/\.-]\s*[01]?\s*\d[\/\.-][12]\d{3}))"

    ),

    # ---------------------------------------------
    #  Combined Fields: GRN No/Date (same line)
    # ---------------------------------------------
    "grn_combined": (
        r"(?mi)GRN\s*No\.?/Date\s*[:\-]?\s*"
        r"([A-Za-z0-9\/\-]+)\s+([0-3]?\d[\/\.-]\s*[01]?\s*\d[\/\.-][12]\d{3})"
    ),

    # ---------------------------------------------
    #  Individual invoice fields (fall back)
    # ---------------------------------------------
    "invoice_no": (
        r"(?mi)(?:\bInvoice\s*No\.?|\bInv\s*No\.?|\bInvoice\s*Number\b)"
        r"\s*[:\-]?\s*([A-Za-z0-9\/\-]+)"
    ),

    "invoice_date": (
        r"(?mi)(?:\bInvoice\s*Date\b|\bInv\s*Date\b|\bBill\s*Date\b)"
        r"\s*[:\-]?\s*([0-3]?\d[-\/\.][01]?\d[-\/\.][12]\d{3})"
    ),

    # ---------------------------------------------
    #  Tax Identifiers
    # ---------------------------------------------
    "gstin_number": (
        r"(?mi)(?:\bGSTIN\b|\bGST\s*IN\b|\bGST\s*No\b|\bGST\s*Number\b)"
        r"\s*[:\-]?\s*([0-9A-Z]{15})"
    ),

    "pan_number": (
        r"(?mi)(?:\bPAN\b|\bPAN\s*No\b|\bPAN\s*Number\b)"
        r"\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])"
    ),

    # ---------------------------------------------
    #  GRN fallback fields
    # ---------------------------------------------
    "grn_no": (
        r"(?mi)(?:\bGRN\s*No\b|\bGRN\b)\s*[:\-]?\s*([A-Za-z0-9\/\-]+)"
    ),

    "grn_date": (
        r"(?mi)(?:\bGRN\s*Date\b|\bGRN\s*Dt\b)"
        r"\s*[:\-]?\s*([0-3]?\d[-\/\.][01]?\d[-\/\.][12]\d{3})"
    ),
}

FIELD_MAP = {
    "supplier_name": "Supplier Name",
    "address": "Address",
    "pin_code": "Pin code",
    "mobile": "Mobile Number",
    "gstin_number": "GSTIN Number",
    "pan_number": "Pan Number",
    "state_code": "State code",
    "grn_no": "GRN No",
    "grn_date": "GRN Date",
    "purchase_invoice_no": "Purchase Invoice No",
    "purchase_invoice_date": "Purchase Invoice Date",
}



def extract_fields_multiline(text):
    lines = text.split("\n")
    fields = {k: None for k in FIELD_MAP}

    for i, line in enumerate(lines):
        clean = line.strip().replace(":", "")
        for key, label in FIELD_MAP.items():
            if clean.lower() == label.lower():
                # value is usually on next line
                if i + 1 < len(lines):
                    value = lines[i + 1].strip()
                    if value and not value.endswith(":"):
                        fields[key] = value
                break
    
    return fields


#  def extract_fields(text):
#     output = {}
#     for field, pattern in FIELD_PATTERNS.items():
#         m = re.search(pattern, text, flags=re.IGNORECASE)
#         output[field] = m.group(1).strip() if m else None
#     return output

def extract_field(text, pattern):
    m = re.search(pattern, text)
    if m:
        # If combined (two capture groups)
        if m.lastindex == 2:
            return m.group(1).strip(), m.group(2).strip()
        # If normal (one capture group)
        return m.group(1).strip()
    return None

def extract_next_line(lines, label_regex):
    for i, line in enumerate(lines):
        if re.search(label_regex, line, flags=re.I):
            if i + 1 < len(lines):
                val = lines[i+1].strip()
                if val and ':' not in val:
                    return val
    return None

def extract_fields_engine(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {}

    # ---------------------------------------
    # 1️⃣ Invoice No + Date (Combined)
    # ---------------------------------------
    invoice_combined = extract_field(text, FIELD_PATTERNS["invoice_combined"])
    if invoice_combined:
        result["invoice_no"], result["invoice_date"] = invoice_combined

    # ---------------------------------------
    # 2️⃣ GRN No + Date (Combined)
    # ---------------------------------------
    grn_combined = extract_field(text, FIELD_PATTERNS["grn_combined"])
    if grn_combined:
        result["grn_no"], result["grn_date"] = grn_combined

    # ---------------------------------------
    # 3️⃣ Fallback: Individual Fields
    # ---------------------------------------
    for key in ["invoice_no", "invoice_date", "grn_no", "grn_date", "gstin_number", "pan_number"]:
        if key not in result:
            val = extract_field(text, FIELD_PATTERNS[key])
            if val:
                result[key] = val

    # ---------------------------------------
    # 4️⃣ Next-line fallback for all fields
    # ---------------------------------------
    next_line_map = {
        "invoice_no": r"\bInvoice\s*No",
        "invoice_date": r"\bInvoice\s*Date",
        "grn_no": r"\bGRN\s*No",
        "grn_date": r"\bGRN\s*Date",
    }

    for key, pattern in next_line_map.items():
        if key not in result:
            val = extract_next_line(lines, pattern)
            if val:
                result[key] = val

    return result




def extract_table_rows(text):
    
    
    # Regex for table rows
    row_pattern = r"""
      # (\d+)                                     # S.No
       #\s+
       #([A-Za-z0-9 &/]+(?:\n[A-Za-z0-9 &/]+)?)   # Description (may span lines)
       #\s+
        #([0-9]+)                                  # Barcode
        ^(\d*)$                                     #Barcode

        \s+
        ([0-9]+)                                  # HSN
        \s+
        ([0-9.]+)                                 # Qty
        \s+
        ([A-Za-z]+)                               # UOM
        \s+
        ([0-9.]+)                                 # Rate
        \s+
        ([0-9.]+)                                 # Discount
        \s+
        ([0-9.]+)                                 # Taxable
        \s+
        (0%?)                                     # CGST%
        \s+
        ([0-9.]+)                                 # CGST Amount
        \s+
        (0%?)                                     # SGST%
        \s+
        ([0-9.]+)                                 # SGST Amount
        \s+
        (0%?)                                     # IGST%
        \s+
        ([0-9.]+)                                 # IGST Amount
        \s+
        ([0-9.]+)                                 # Amount
    """

    rows = re.findall(row_pattern, text, flags=re.IGNORECASE | re.VERBOSE)
    print("rows:", rows)
    return rows



def extract_descriptions(pdf_path):
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    items = []
    current = None
    sno_pattern = re.compile(r"^\s*(\d{1,3})\b\s*(.*)$")

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        match = sno_pattern.match(line)
        if match:
            sno = match.group(1)
            desc_first = match.group(2)

            if current:
                items.append(current)

            current = {"sno": sno, "desc": [desc_first]}
        else:
            if current:
                current["desc"].append(line)

    if current:
        items.append(current)

    return {it["sno"]: " ".join(it["desc"]).strip() for it in items}

def extract_sample_invoice_items(text):
    """
    Extract table items for invoices like sample_invoice2.pdf.
    Ignores description, extracts only structured numeric/text fields.
    """

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    print("sample invoice items",text)

    # Pattern:
    # S.No  Qty  (ignored desc)  Batch  Exp  HSN  Rate  Discount  Amount
    pattern = re.compile(
        r"(\d+)\s+"                 # S.No
        r"(\d+)\s+"                 # Qty
        r"(?:[A-Za-z0-9 \-\*]+?)\s+"# Description (ignored)
        r"([A-Za-z0-9\-\*]+)\s+"    # Batch
        r"(\d{2}-\d{4})\s+"         # Exp
        r"(\d+)\s+"                 # HSN
        r"(\d+\.\d+)\s+"            # Rate
        r"(\d+\.\d+)\s+"            # Discount
        r"(\d+\.\d+)"               # Amount
    )

    matches = pattern.findall(text)
    print("sample invoice matches:", matches)

    df = pd.DataFrame(matches, columns=[
        "S.No", "Qty", "Batch", "Exp", "HSN", "Rate", "Discount", "Amount"
    ])
    print("sample invoice df:", df)

    return df

def clean_hsn_list(hsn_list, expected_rows):
    clean = []

    for v in hsn_list:
        v = v.strip()
        if re.match(r"^\d{4,8}$", v):
            clean.append(v)

    # Insert blank at top if first row has no HSN
    if len(clean) == 1 and expected_rows >= 2:
        clean = ["", clean[0]]

    # Pad remaining rows
    if len(clean) < expected_rows:
        clean += [""] * (expected_rows - len(clean))

    return clean



def extract_table(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        tables = pdf.pages[0].extract_tables()

    if not tables:
        return None, None

    table = tables[0]
    table = [[cell or "" for cell in row] for row in table]

    # find header
    header_idx = next((i for i, r in enumerate(table) if any("S.No" in str(c) for c in r)), None)
    if header_idx is None:
        return None, None

    headers = table[header_idx]
    
    data_row = table[header_idx + 1]

    split_cols = [cell.split("\n") for cell in data_row]
    cleaned_cols = [[x.strip() for x in col if x.strip()] for col in split_cols]

    #print(" extract table headers:", headers)
    #print(" extract table cleaned_cols:", cleaned_cols)
    return headers, cleaned_cols



def reconstruct_rows(headers, cols):

    # 1. Clean headers (collapse empty ones)
    clean_headers = []
    for h in headers:
        if h.strip() == '':
            clean_headers.append(None)
        else:
            clean_headers.append(h.strip())
            
    # Clean HSN column before reconstructing rows
    HSN_INDEX = headers.index("HSN")
    print("HSON_INDEX:", HSN_INDEX)
    # number of logical rows = length of S.No column
    expected_rows = len(cols[0])

    cols[HSN_INDEX] = clean_hsn_list(cols[HSN_INDEX], expected_rows)

    print("Cleaned HSN column:", cols[HSN_INDEX])
        

    # 2. Transpose columns → rows
    max_len = max(len(c) for c in cols)
    for i in range(len(cols)):
        if len(cols[i]) < max_len:
            cols[i] += [""] * (max_len - len(cols[i]))

    rows = []

    for r in range(max_len):
        row = {}
        for c in range(len(cols)):
            header = clean_headers[c]

            # Skip unusable header
            if header is None:
                continue

            # Get value if exists
            val = cols[c][r] if r < len(cols[c]) else ''

            # Append value
            if header not in row:
                row[header] = val
            else:
                # merge multi-column description
                if val.strip():
                    row[header] += " " + val.strip()
                    
        print("reconstructed row:", row)
        rows.append(row)

    return pd.DataFrame(rows)

def normalize_kalagram_lines(text):
    """
    Converts the multi-line Kalagram item block into single-line rows.
    Each item starts with S.No (a number), followed by many broken lines.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    items = []
    buff = []

    for l in lines:
        # Item starts when l is a number (S.No)
        if l.isdigit():
            if buff:
                items.append(buff)
            buff = []
        else:
            buff.append(l)

    # Add last item
    if buff:
        items.append(buff)

    # Join rows into single-line
    normalized = [" ".join(row) for row in items]

    return normalized


def extract_table_rows_kalagram(text):

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)

    # FINAL regex that works for all Kalagram invoices
    pattern = re.compile(
        r"([A-Z]?\d{4,})\s+"          # BARCODE (A1400173, S300470, 1400173 etc.)
        r"(\d{4,8})\s+"               # HSN (71171100)
        r"(\d+\.?\d*)\s+"             # QTY (3.00)
        r"([A-Za-z]+)\s+"             # UOM (PCS)
        r"(\d+\.?\d*)\s+"             # RATE (225.00)
        r"(\d+\.?\d*)\s+"             # DISCOUNT (0.00)
        r"(\d+\.?\d*)\s+"             # TAXABLE (675.00)
        r"(\d+\.?\d*)%?\s+"           # CGST% (2.5)
        r"(\d+\.?\d*)\s+"             # CGST AMT (16.88)
        r"(\d+\.?\d*)%?\s+"           # SGST% (2.5)
        r"(\d+\.?\d*)\s+"             # SGST AMT (16.88)
        r"(\d+\.?\d*)%?\s+"           # IGST% (0)
        r"(\d+\.?\d*)\s+"             # IGST AMT (0.00)
        r"(\d+\.?\d*)"                # TOTAL (709)
    )

    return pattern.findall(text)

def extract_kalagram_items(text):
    rows = extract_table_rows_kalagram(text)

    columns = [
        "BARCODE","HSN","Qty","UOM","Rate","Discount","Taxable",
        "CGST%","CGST Amt","SGST%","SGST Amt","IGST%","IGST Amt","Amount"
    ]

    df = pd.DataFrame(rows, columns=columns)
    return df

UNIT_RE = re.compile(r"^[A-Za-z]$")


def is_valid_start(lines, i):
    if i + 3 >= len(lines):
        return False

    # S.No must be integer
    if not lines[i].isdigit():
        return False

    # Line i+1 is description → NOT numeric
    if re.match(r"^\d+(\.\d+)?$", lines[i+1]):
        return False

    # Line i+2 is HSN → 4-8 digits
    if not re.match(r"^\d{4,8}$", lines[i+2]):
        return False

    # Line i+3 is Qty → decimal number
    if not re.match(r"^\d+(\.\d+)?$", lines[i+3]):
        return False

    return True


def extract_pi1_items(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    items = []
    i = 0
    
    while i < len(lines):
        # Detect start of item: S.No
        if is_valid_start(lines, i):

            sno = lines[i]
            hsn = lines[i+2]
            qty = lines[i+3]

            # Batch may be 1 or 2 lines → merge them logically
            batch_line_start = i + 4
            batch = lines[batch_line_start]

            # If batch breaks, merge next line if it looks like continuation
            if batch.endswith("-"):
                batch = batch[:-1] + lines[batch_line_start + 1]
                unit_start_search = batch_line_start + 2
            else:
                unit_start_search = batch_line_start + 1

            #⭐ Detect the UOM dynamically
            #unit_idx = unit_start_search(lines, unit_start_search)
            unit_idx = unit_start_search 
            # if unit_idx is None:
            #     i += 1
            #     continue

            unit= lines[unit_idx]

            # After UOM, numeric sequence begins
            rate      = lines[unit_idx + 1]
            taxable   = lines[unit_idx + 2]
            tax_rate  = lines[unit_idx + 3]
            gst_amt   = lines[unit_idx + 4]
            cess_amt  = lines[unit_idx + 5]
            amount    = lines[unit_idx + 6]

            items.append({
                "S.No": sno,
                "HSN": hsn,
                "Qty": qty,
                "Batch": batch,
                "Unit": unit,
                "Unit_Price": rate,
                "Taxable": taxable,
                "TaxRate": tax_rate,
                "GST_Amt": gst_amt,
                "Cess_Amt": cess_amt,
                "Amount": amount
            })

            i = unit_start_search + 7
            continue
            
        
        i += 1
       
        
    print("PI-1 Df------",pd.DataFrame(items))   

    return pd.DataFrame(items)


def merge_description(headers, cols, desc_map):
    sno_list = cols[0]
    final_desc = [desc_map.get(sno, "") for sno in sno_list]

    cols[1] = final_desc

    count = len(sno_list)
    for i in range(len(cols)):
        if len(cols[i]) < count:
            cols[i] += [""] * (count - len(cols[i]))
            

    df = pd.DataFrame({headers[i]: cols[i] for i in range(len(headers))})
    
   
    
    if "Material\nDescription" in df.columns:
        df.drop(['Material\nDescription'], axis = 1,inplace=True)
        
    #print("Merged description df columns: ", df.columns)    
    
    print("Merged description df:", df)
    return df




def is_hsn(line):
    """HSN is always 4–8 digits."""
    return bool(re.fullmatch(r"\d{4,8}", line))


def is_barcode(line):
    """Barcode for PI-3: digits only, 4–15 digits."""
    return bool(re.fullmatch(r"\d{4,15}", line))


def extract_pi3_items(text):
    # Split and clean lines
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    n = len(lines)
    items = []

    i = 0
    while i < n:
        # -----------------------------
        # 1️⃣ Detect potential barcode
        # -----------------------------
        barcode = ""
        hsn = ""
        qty = ""
        uom = ""
        rate = ""
        discount = ""
        taxable = ""
        cgst_percent = ""
        cgst_amt = ""
        sgst_percent = ""
        sgst_amt = ""
        igst_percent = ""
        igst_amt = ""
        amount = ""

        # Case A → barcode present
        if i + 1 < n and is_barcode(lines[i]) and is_hsn(lines[i+1]):
            barcode = lines[i]
            hsn = lines[i+1]
            offset = 2

        # Case B → barcode absent
        elif is_hsn(lines[i]):
            barcode = ""          # empty barcode
            hsn = lines[i]
            offset = 1
        else:
            i += 1
            continue  # Not a row start → move on

        # -------------------------------------
        # 2️⃣ Read remaining 13 numeric fields
        # -------------------------------------
        try:
            qty         = lines[i + offset + 0]
            uom         = lines[i + offset + 1]
            rate        = lines[i + offset + 2]
            discount    = lines[i + offset + 3]
            taxable     = lines[i + offset + 4]
            cgst_percent= lines[i + offset + 5]
            cgst_amt    = lines[i + offset + 6]
            sgst_percent= lines[i + offset + 7]
            sgst_amt    = lines[i + offset + 8]
            igst_percent= lines[i + offset + 9]
            igst_amt    = lines[i + offset + 10]
            amount      = lines[i + offset + 11]
        except IndexError:
            # incomplete line item → ignore
            i += 1
            continue

        # Validate quantity & rate
        if not re.fullmatch(r"\d+(\.\d+)?", qty):
            i += 1
            continue

        # Save the extracted line item
        items.append([
            barcode, hsn, qty, uom, rate, discount,
            taxable, cgst_percent, cgst_amt,
            sgst_percent, sgst_amt,
            igst_percent, igst_amt,
            amount
        ])

        # Move to next line
        i += offset + 12

    # Convert results into DataFrame
    columns = [
        "BARCODE", "HSN/SAC", "Qty", "UOM", "Rate",
        "Discount", "Taxable", "CGST%", "CGST Amt",
        "SGST%", "SGST Amt", "IGST%", "IGST Amt",
        "Amount"
    ]

    return pd.DataFrame(items, columns=columns)

   

def extract_invoice(pdf_path):
    # Extract full text
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    #print("Full extracted text:\n", text)

    # Header fields
    #fields = extract_fields_multiline(text)
    fields = extract_fields_engine(text)

    # Try normal pdfplumber table
    headers, cols = extract_table(pdf_path)
    #print("Extracted headers:", headers)
    #print("Extracted cols:", cols)

    # If pdfplumber fails → PI-3 mode
    if headers is None or len(cols[0]) == 0:
        print("⚠ Falling back to PI-3 parser")
        if 'chokhi dhani' in  text.lower():
            print("✔ Kalagram Mode")
            df = extract_kalagram_items(text)
            return fields,df
            
        else:
            print("✔ PI-3 Mode")
            df = extract_pi3_items(text)
            if df.empty:
                print("⚠ PI-3 extraction failed, trying other parser")
                df = extract_pi1_items(text)
            return  fields,df
            

    # Detect broken description (needs hybrid)
    desc_list = cols[1]
    hybrid_needed = (
        len(desc_list) != len(cols[0]) or
        any(len(x) > 20 and " " not in x for x in desc_list)
    )

    if hybrid_needed:
        print("🔄 Hybrid Mode: pdfplumber + PyPDF2")
        desc_map = extract_descriptions(pdf_path)
        df = merge_description(headers, cols, desc_map)
        
        
          
    else:
        print("✔ pdfplumber Mode")
        print(("headers-----",headers))
        print(("cols------",cols))
        try:            
            #df = pd.DataFrame({headers[i]: cols[i] for i in range(len(headers))})            
            df = reconstruct_rows(headers, cols)
            # 1️⃣ Drop Description column
            if "Description" in df.columns:
                df = df.drop(columns=["Description"])

            # 2️⃣ Clean numeric columns
            num_cols = ["S.No.", "Qty.", "Rate", "HSN","IGST", "Amount"]
            for c in num_cols:
                if c in df.columns:
                    df[c] = df[c].astype(str).str.replace(r"[^0-9.]", "", regex=True)

            # 3️⃣ Remove garbage rows
            df = df[df["S.No."].str.isdigit()]               # S.No must be numeric
            df = df[df["Qty."].str.isdigit()]                # Qty must be numeric
            df = df[df["Amount"].str.replace(".", "").str.isdigit()]  # Amount must be numeric

            # 4️⃣ Reset index
            df = df.reset_index(drop=True)

        except: 
            df = extract_sample_invoice_items(text)
              

    return fields, df

required_cols = [
    'Item\nCode','BARCODE','HSN/SAC','MRP','Batch No','Exp','CLD','Qty','UOM',
    'Rate','Tot\nDis','Taxable','CGST%','CGST\nAmt','SGST%','SGST\nAmt',
    'IGST%','IGST\nAmount','Amount'
]

def filter_columns(df):
    available = [c for c in required_cols if c in df.columns]
    print(type(available))
    print("Available columns for output:", available)
    
    return df[available]


fields, df = extract_invoice("data/GOYAL MEDICAL AGENCY NAGAUR.pdf")


#df = filter_columns(df)
print("\nEXTRACTED FIELDS:\n", fields)
print("\nEXTRACTED ITEMS:\n", df)
df.to_excel("output/Goyal_Medical_Agency.xlsx", index=False)

