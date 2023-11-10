import argparse
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import generate_report_pdf, run_pdf_checker


def process_file(filename, output_filename):
    # This function will handle the processing of the file
    # try:
    with open(filename, 'rb') as file:
        # Read and process the file
        content = BytesIO(file.read())

    try:
        res = run_pdf_checker(content)
        if res is None:
            exit(-1)
    except Exception as e :
        print("Error while running pdf checker: " + str(e))
        exit(-1)

    # misc
    # create a tempdir for storing the images
    tmp_dir = TemporaryDirectory("")
    pdf_bytes_simplified = generate_report_pdf(
        BytesIO(content.getvalue()), "en", Path(filename).name)
    tmp_dir.cleanup()
    with open(output_filename, "wb") as file:
        file.write(pdf_bytes_simplified.getvalue())

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Generate a PDF report based on VeraPDF.")

    # Add the arguments
    parser.add_argument('input_file', help="The path to the file to be checked")
    parser.add_argument('output_file', help="The path where the report will be written")

    # Execute the parse_args() method
    args = parser.parse_args()

    process_file(args.input_file, args.output_file)

if __name__ == "__main__":
    main()
