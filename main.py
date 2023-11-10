from io import BytesIO
from datetime import datetime

import fitz
# from app.pdf_checker.service.verapdf_checker import run_checker
from helpers import (
    filter_group_data_simplified,
    # run_pdf_checker,
    compute_status,
)
from pdf_generator import run_pdf_checker

from pdf_generator import generate_report_pdf

import argparse
from pathlib import Path

import base64
import pandas as pd
import json
from weasyprint import HTML
from datetime import datetime
from pathlib import Path
import weasyprint
from jinja2 import Template
from tempfile import TemporaryDirectory
import zipfile

import pandas as pd
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
import os
import json
from pathlib import Path
from datetime import datetime
import re
import codecs
import fitz


def process_file(filename):
    # This function will handle the processing of the file
    # try:
    with open(filename, 'rb') as file:
        # Read and process the file
        content = BytesIO(file.read())
        print("File content:")
        print(content)

    res = run_pdf_checker(content)
    if res is None:
        st.error("Error with file, please contact support!")
        exit(-1)
        ###
    data_dict = res["report"]

    file_size = len(content.getvalue())
    pdf_document = fitz.open(stream=content.getvalue(), filetype="pdf")
    metadata = pdf_document.metadata

    ## misc
    current_datetime: str = datetime.now().strftime("%d/%m/%Y, %H:%M")
    # create a tempdir for storing the images
    tmp_dir = TemporaryDirectory("")

    my_dict = filter_group_data_simplified(
        data_dict
    )
    pdf_bytes_simplified = generate_report_pdf(BytesIO(content.getvalue()), "en", Path(filename).name)
    # language["pdf_bytes"] = pdf_bytes_simplified
    tmp_dir.cleanup()

    # Add your file processing logic here
    # report = generate_report_pdf(content)
    with open("report.pdf", "wb") as file:
        file.write(pdf_bytes_simplified.getvalue())
    # except FileNotFoundError:
    #     print(f"Error: The file '{filename}' was not found.")
    # except Exception as e:
    #     print(f"An error occurred: {e}")

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Process a file.")

    # Add the arguments
    parser.add_argument('file', help="The file to be processed")

    # Execute the parse_args() method
    args = parser.parse_args()

    process_file(args.file)

if __name__ == "__main__":
    main()
