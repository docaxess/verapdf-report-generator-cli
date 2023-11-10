# VeraPDF Report Generator

This project is a simple CLI that allow you to generate an accessibility report based on VeraPDF. VeraPDF is an opensource PDF checker. You will know if your PDF file is accessible and also how to improve it's accessibility based on the pdf report generated.

## Installation

- Install [venv](https://docs.python.org/3/library/venv.html/). You may need to install the apt package python3-venv if you're using a ubuntu-based linux distribution.

### Prepare virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## Run the program

1. The help command

You can get help using -h or --help command like below.

```
➜  verapdf-report-generator git:(main) ✗ python3 main.py -h
usage: main.py [-h] input_file output_file

Process a file.

positional arguments:
  input_file   The path to the file to be checked
  output_file  The path where the report will be written

options:
  -h, --help   show this help message and exit
```

2. Example

In order to generate a report : python3 main.py path/to/input_file.pdf path/to/output_file.pdf

You can get you can then open and analyze the generated report.

## Template

The report is generated from a HTML/CSS template.
You can customize the report appearance by changing files located in static folder, especially [template file](./static/report-template/template-en.html) and [style sheed](./static/style.css).
