import streamlit as st
from llama_parse import LlamaParse
import pandas as pd
import re
import tempfile
import os

def extract_markdown_tables(text: str):
    tables = []
    pattern = re.compile(
    r"\|(?:[^\n|]+\|)+\n\|(?:[-: ]+\|)+\n(?:\|(?:[^\n|]+\|)+\n?)+", re.MULTILINE)
    matches = pattern.findall(text)
    for i, match in enumerate(matches):
        try:
            # Split the match into lines and strip whitespace
            lines = [line.strip() for line in match.strip().split('\n') if line.strip()]
            # Remove the separator line (usually the second line)
            if len(lines) > 2:
                header = [col.strip() for col in lines[0].split('|')[1:-1]]
                data = [
                    [cell.strip() for cell in row.split('|')[1:-1]]
                    for row in lines[2:]
                ]
                df = pd.DataFrame(data, columns=header)
        except Exception as e:
            print(f"Error parsing table {i}: {e}")
            df = df.dropna(axis=1, how="all")
            df.columns = df.columns.str.strip()
            df = df[1:]  # Remove possible duplicate header
            tables.append((f"Table_{i+1}", df))
        except Exception as e:
            st.warning(f"Failed to parse table {i+1}: {e}")
    return tables

def parse_pdf_with_llamacloud(pdf_path, output_excel_path, api_key=None):
    parser = LlamaParse(
        api_key=api_key,
        result_type='markdown')
    documents = parser.load_data(pdf_path)
    all_text = "\n".join(doc.text for doc in documents)
    print(all_text)
    tables = extract_markdown_tables(all_text)
    if not tables:
        raise ValueError("No tables found in the parsed document.")
    with pd.ExcelWriter(output_excel_path, engine="openpyxl") as writer:
        for name, df in tables:
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return len(tables)

st.title("PDF Table Extractor (LlamaParse)")

api_key = st.text_input("LlamaParse API Key", type="password")
uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
output_filename = st.text_input("Output Excel Filename", value="output.xlsx")

if st.button("Extract Tables"):
    if not api_key:
        st.error("Please enter your LlamaParse API key.")
    elif not uploaded_file:
        st.error("Please upload a PDF file.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(uploaded_file.read())
            tmp_pdf_path = tmp_pdf.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_xlsx:
            tmp_xlsx_path = tmp_xlsx.name

        try:
            num_tables = parse_pdf_with_llamacloud(tmp_pdf_path, tmp_xlsx_path, api_key=api_key)
            with open(tmp_xlsx_path, "rb") as f:
                st.success(f"✅ Extracted {num_tables} tables.")
                st.download_button(
                    label="Download Excel File",
                    data=f,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            os.remove(tmp_pdf_path)
            os.remove(tmp_xlsx_path)
