# VeraPDF Report Generator

This project is a simple CLI that allow you to generate an accessibility report based on VeraPDF. VeraPDF is an opensource PDF checker. You will know if your PDF file is accessible and also how to improve it's accessibility based on the pdf report generated.

## Installation

- Install [python](https://www.python.org/downloads/).
- Install [venv](https://docs.python.org/3/library/venv.html/). You may need to install the apt package python3-venv if you're using a ubuntu-based linux distribution.
- You also need JDK in order to run the VeraPDF engine : in debian based distribution you simply run : `sudo apt install default-jre default-jdk`
- You need exiftool to get metadata from your pdf file such as title : `sudo apt install exiftool`

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

## Tweak VeraPDF engine

You can tweak VeraPDF engine used in this project. In order to do so, take a look at [verapdf_checker.py](./app/pdf_checker/service/verapdf_checker.py)

```python
def run_checker(input_file_path: str) -> str | None:
    completed_process = subprocess.run(
        [
            "./verapdf",
            "-f",
            "ua1",
            "--maxfailuresdisplayed",
            "999999",
            "--format",
            "json",
            "--success",
            str(input_file_path),
        ],
        cwd="app/pdf_checker/service/verapdf",
        capture_output=True,
        text=True,
    )
    output = str(completed_process.stdout)

    return output
```

Instead of ua1, you can use any of those value : `{1a, 1b, 2a, 2b, 2u, 3a, 3b, 3u, 4, 4f, 4e, ua1}`.

## Template customization

The report is generated from a HTML/CSS template.
You can customize the report appearance to suit your needs by changing files located in static folder, especially [template file](./static/report-template/template-en.html) and [style sheet](./static/style.css).

# About VeraPDF

VeraPDF is an opensource alternative to PAC 2021 supported by Preforma, PDF Association, Open Preservation Foundation and Digital Preservation Coalition.
This project validates PDF/UA1 conformance and focus on accessibility.
