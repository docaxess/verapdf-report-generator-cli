import base64
import json
import os
import subprocess
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz
import jinja2
import pandas as pd
import weasyprint

from app.pdf_checker.service.verapdf_checker import run_checker


def get_metadata_one_file(filenames):
    command = ["exiftool", "-G", "-j", filenames]
    result = subprocess.run(command, capture_output=True, text=True)
    output = json.loads(result.stdout)
    return output[0]


class add_path:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        sys.path.insert(0, self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            sys.path.remove(self.path)
        except ValueError:
            pass


def get_lang2(file_bytes: BytesIO) -> str:
    lang = None
    with TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, "file.pdf"), "wb") as f:
            f.write(file_bytes.read())

        metadata = get_metadata_one_file(os.path.join(temp_dir, "file.pdf"))
        lang = metadata.get("PDF:Language", "")
    return lang.upper()


def run_pdf_checker(file_content: BytesIO) -> dict | None:
    # file_content = BytesIO(uploaded_file.file.read())

    file_content.seek(0)
    with TemporaryDirectory() as tmp_dir:
        input_f = str(tmp_dir) + "/tmp.pdf"
        with open(input_f, "wb") as f:
            f.write(file_content.getvalue())
        res = run_checker(input_f)

    json_data = json.loads(res)
    if json_data["report"]["jobs"][0].get("validationResult") is None:
        return None
    passed_rules = json_data["report"]["jobs"][0]["validationResult"]["details"][
        "passedRules"
    ]
    failed_rules = json_data["report"]["jobs"][0]["validationResult"]["details"][
        "failedRules"
    ]
    passed_checks = json_data["report"]["jobs"][0]["validationResult"]["details"][
        "passedChecks"
    ]
    failed_checks = json_data["report"]["jobs"][0]["validationResult"]["details"][
        "failedChecks"
    ]

    score_rules = passed_rules / (passed_rules + failed_rules)
    score_checks = passed_checks / (passed_checks + failed_checks)

    return {
        "passed_rules": passed_rules,
        "failed_rules": failed_rules,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "score_rules": "{:.2f}".format(score_rules * 100),
        "score_checks": "{:.2f}".format(score_checks * 100),
        "report": json_data,
        "language": get_lang2(file_content),
    }


def get_template_by_lang(lang: str = None) -> str:
    prefix = "static/report-template"
    if lang == "fr":
        return f"{prefix}/template-fr.html"
    return f"{prefix}/template-en.html"


def get_datetime():
    return datetime.now().strftime("%d/%m/%Y, %H:%M")


def get_title(file_content_bytes: BytesIO) -> str:
    pdf_document = fitz.open(stream=file_content_bytes, filetype="pdf")
    metadata = pdf_document.metadata
    return metadata.get("title", "")


def get_nb_pages(file_content_bytes: BytesIO) -> int:
    pdf_document = fitz.open(stream=file_content_bytes, filetype="pdf")
    return len(pdf_document)


def generate_report_pdf(
    file_content: BytesIO, language: str = "en", filename: str = "filename.pdf"
) -> BytesIO:
    res = run_pdf_checker(file_content)
    if res is None:
        raise Exception("Error with file, please contact support!")

    data_dict = res["report"]
    my_dict_simplified = filter_group_data(data_dict)
    rows_simplified = [
        {
            "Status": my_dict_simplified["ruleStatus"][i],
            "Clause": str(my_dict_simplified["clause"][i]),
            "TestNumber": str(my_dict_simplified["testNumber"][i]),
            "PassedChecks": my_dict_simplified["passedChecks"][i],
            "FailedChecks": my_dict_simplified["failedChecks"][i],
        }
        for i in range(len(my_dict_simplified["ruleStatus"]))
    ]
    # Load the Jinja template

    with add_path("static/report-template"):
        with open(get_template_by_lang(language), "r") as f:
            template_str = f.read()
        template = jinja2.Template(template_str)
        # Render the template with the data

    rendered_table_simplified = template.render(
        rows=rows_simplified,
        date=get_datetime(),
        file_title=get_title(file_content),
        lang=language,
        file_size=format_bytes(file_content.getbuffer().nbytes),
        thumbnail_verapdf="vera-logo-shadow.jpg",
        thumbnail=convert_to_base64(file_content),
        file_name=filename,
        nb_pages=get_nb_pages(file_content),
    )

    # write rendered_table_simplified into a file

    html_simplified = weasyprint.HTML(
        string=rendered_table_simplified, base_url=".")
    pdf_bytes_simplified = BytesIO()
    html_simplified.write_pdf(target=pdf_bytes_simplified)
    return pdf_bytes_simplified


def convert_to_base64(file_content: BytesIO):
    file_content.seek(0)
    pdf_document = fitz.open(stream=file_content, filetype="pdf")
    with TemporaryDirectory() as tmp_dir:
        path_tmp_dir = Path(tmp_dir)
        path_tmp_dir.mkdir(parents=True, exist_ok=True)
        first_page = pdf_document[0]
        pix = first_page.get_pixmap()
        pix.save(path_tmp_dir / "page-0.png")

        with open(path_tmp_dir / "page-0.png", "rb") as f:
            image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    return image_base64


def format_bytes(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0: "", 1: "k", 2: "M", 3: "G", 4: "T"}
    while size > power:
        size /= power
        n += 1
    return "{:.2f}".format(size) + " " + power_labels[n] + "b"


def filter_group_data(data_dict: dict) -> dict:
    df = pd.DataFrame(
        data_dict["report"]["jobs"][0]["validationResult"]["details"]["ruleSummaries"]
    )

    # filter, aggregate and group data
    filtered_data: pd.DataFrame = (
        df.drop(
            columns=[
                "status",
                "checks",
                "test",
                "object",
                "ruleStatus",
            ],
            axis=0,
        )
        .sort_values(by=["clause"])
        .reset_index(drop=True)
    )
    df_grouped_data = (
        filtered_data.groupby(["specification", "clause", "testNumber"])
        .sum()
        .reset_index()
    )
    df_grouped_data["ruleStatus"] = df_grouped_data.apply(
        lambda row: "PASSED" if int(row["failedChecks"]) == 0 else "FAILED", axis=1
    )

    # prepare jinja2 values
    # stats
    passed_checks_totals = df["passedChecks"].sum()
    failed_checks_totals = df["failedChecks"].sum()
    percent_total = "{:.2f}".format(
        passed_checks_totals / (passed_checks_totals +
                                failed_checks_totals) * 100
    )

    # rows
    my_dict = df_grouped_data.to_dict(orient="list")
    my_dict["passed_checks_totals"] = passed_checks_totals
    my_dict["failed_checks_totals"] = failed_checks_totals
    my_dict["percent_total"] = percent_total
    return my_dict


def convert_clause_to_simplified(clause_number: str) -> str:
    clause_number = clause_number["clause"]
    if clause_number[0] == "5":
        return "5-x"
    else:
        clause_number_split = clause_number.split(".")
        return (
            clause_number_split[0] + "." +
            clause_number_split[1].split("-")[0] + "-x"
        )


def compute_status(failed_check: int, passed_check: int) -> str:
    if failed_check > 0:
        return "FAILED"
    else:
        return "PASSED"
