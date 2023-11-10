import jinja2
from jinja2 import Environment, FileSystemLoader
import pandas as pd
import json
from weasyprint import HTML
from datetime import datetime
from pathlib import Path
import weasyprint

import pandas as pd
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
import os
from app.pdf_checker.service.verapdf_checker import run_checker
import json
from pathlib import Path
from datetime import datetime
import re
import codecs
import fitz
import base64

import fitz
import sys
from pathlib import Path


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
    prefix = "app/presentation/report-template"
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
    file_content: BytesIO, language: str, filename: str = "filename.pdf"
) -> BytesIO:
    res = run_pdf_checker(file_content)
    if res is None:
        st.error("Error with file, please contact support!")
        raise Exception("Error with file, please contact support!")

    data_dict = res["report"]
    my_dict_simplified = filter_group_data_simplified(data_dict, language)
    my_dict = my_dict_simplified
    rows_simplified = [
        {
            "Status": my_dict_simplified["ruleStatus"][i],
            "Description": my_dict_simplified["description"][i],
            "PassedChecks": my_dict_simplified["passedChecks"][i],
            "FailedChecks": my_dict_simplified["failedChecks"][i],
        }
        for i in range(len(my_dict_simplified["ruleStatus"]))
    ]
    # Load the Jinja template

    with add_path("app/application/handler/pdf_report_generator/report-template"):
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
        thumbnail=convert_to_base64(file_content, 128, 128),
        file_name=filename,
        nb_pages=get_nb_pages(file_content),
        passed_checks_totals=my_dict["passed_checks_totals"],
        failed_checks_totals=my_dict["failed_checks_totals"],
        passed_rules_totals=my_dict["passed_rules_totals"],
        failed_rules_totals=my_dict["failed_rules_totals"],
        percent_total=my_dict["percent_total"],
    )

    # write rendered_table_simplified into a file

    html_simplified = weasyprint.HTML(string=rendered_table_simplified, base_url=".")
    pdf_bytes_simplified = BytesIO()
    html_simplified.write_pdf(target=pdf_bytes_simplified)
    return pdf_bytes_simplified


def convert_to_base64(file_content: BytesIO, width, height):
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


def get_nb_pages(file_content_bytes: BytesIO) -> int:
    pdf_document = fitz.open(stream=file_content_bytes, filetype="pdf")
    return len(pdf_document)


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
    ## stats
    passed_checks_totals = df["passedChecks"].sum()
    failed_checks_totals = df["failedChecks"].sum()
    percent_total = "{:.2f}".format(
        passed_checks_totals / (passed_checks_totals + failed_checks_totals) * 100
    )

    ## rows
    my_dict = df_grouped_data.to_dict(orient="list")
    my_dict["passed_checks_totals"] = passed_checks_totals
    my_dict["failed_checks_totals"] = failed_checks_totals
    my_dict["percent_total"] = percent_total
    return my_dict


# def convert_clause_to_simplified(clause_number: str) -> str:
#     clause_number = clause_number["clause"]
#     if clause_number[0] == "5":
#         return "5-x"
#     else:
#         clause_number_split = clause_number.split(".")
#         return (
#             clause_number_split[0] + "." + clause_number_split[1].split("-")[0] + "-x"
#         )

def replace_oassed_checks_with_dash(checkpoint_name: str, passedChecks) -> str | int:
    return '-' if '*' in checkpoint_name else passedChecks

def custom_grouping_function(clause_number: str, language: str):
    clause_number = clause_number["clause"]
    pdf_categories_descriptions_dict_en: dict = {
        "5-x": "PDF Syntax",
        "7.1-x": "PDF Syntax",
        "7.7-x": "PDF Syntax",
        "7.10-x": "PDF Syntax",
        "7.11-x": "PDF Syntax",
        "7.12-x": "PDF Syntax",
        "7.13-x": "PDF Syntax",
        "7.14-x": "PDF Syntax",
        "7.15-x": "PDF Syntax",
        "7.16-x": "PDF Syntax",
        "7.19-x": "PDF Syntax",
        "7.20-x": "PDF Syntax",
        "7.2-x": "Text",
        "7.3-x": "Graphics*",
        "7.4-x": "Headings*",
        "7.5-x": "Tables*",
        "7.6-x": "Lists",
        "7.8-x": "Page headers and footers",
        "7.9-x": "Notes and references*",
        "7.17-x": "Navigation",
        "7.18-x": "Annotations",
        "7.21-x": "Fonts",
    }

    pdf_categories_descriptions_dict_fr: dict = {
        "5-x": "Syntaxe PDF",
        "7.1-x": "Syntaxe PDF",
        "7.7-x": "Syntaxe PDF",
        "7.10-x": "Syntaxe PDF",
        "7.11-x": "Syntaxe PDF",
        "7.12-x": "Syntaxe PDF",
        "7.13-x": "Syntaxe PDF",
        "7.14-x": "Syntaxe PDF",
        "7.15-x": "Syntaxe PDF",
        "7.16-x": "Syntaxe PDF",
        "7.19-x": "Syntaxe PDF",
        "7.20-x": "Syntaxe PDF",
        "7.2-x": "Textes",
        "7.3-x": "Éléments graphiques*",
        "7.4-x": "Titres*",
        "7.5-x": "Tableaux*",
        "7.6-x": "Listes",
        "7.8-x": "En-têtes et pieds de pages",
        "7.9-x": "Notes et références*",
        "7.17-x": "Navigation",
        "7.18-x": "Annotations",
        "7.21-x": "Polices",
    }

    if language == "fr":
        return pdf_categories_descriptions_dict_fr[clause_number]
    return pdf_categories_descriptions_dict_en[clause_number]


def custom_order_function(language: str) -> str:
    custom_order_fr: dict = {
        "Syntaxe PDF": 1,
        "Textes": 2,
        "Éléments graphiques*": 3,
        "Titres*": 4,
        "Tableaux*": 5,
        "Listes": 6,
        "En-têtes et pieds de pages": 7,
        "Notes et références*": 8,
        "Navigation": 9,
        "Annotations": 10,
        "Polices": 11,
    }

    custom_order_en: dict = {
        "PDF Syntax": 1,
        "Text": 2,
        "Graphics*": 3,
        "Headings*": 4,
        "Tables*": 5,
        "Lists": 6,
        "Page headers and footers": 7,
        "Notes and references*": 8,
        "Navigation": 9,
        "Annotations": 10,
        "Fonts": 11,
    }

    if language == "en":
        return custom_order_en
    return custom_order_fr


def compute_status(failed_check: int, passed_check: int) -> str:
    if failed_check > 0:
        return "FAILED"
    else:
        return "PASSED"


def filter_group_data_simplified(data_dict: dict, language: str = "en") -> dict:
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
    filtered_data["ruleStatus"] = filtered_data.apply(
        lambda row: compute_status(row["failedChecks"], row["passedChecks"]), axis=1
    )

    # filtered_data["clause"] = filtered_data.apply(
    #     lambda row: convert_clause_to_simplified(row), axis=1
    # )

    # filtered_data["description"] = filtered_data.apply(
    #     lambda row: custom_grouping_function(row, language), axis=1
    # )

    df_grouped_data = filtered_data
    df_grouped_data = df_grouped_data.groupby(["description"], as_index=False).agg(
        {"passedChecks": "sum", "failedChecks": "sum"}
    )
    df_grouped_data["passedChecks"] = df_grouped_data.apply(
        lambda row: replace_oassed_checks_with_dash(row["description"], row["passedChecks"]), axis=1
    )
    df_grouped_data["ruleStatus"] = df_grouped_data.apply(
        lambda row: compute_status(row["failedChecks"], row["passedChecks"]), axis=1
    )
    ## sort data
    df_grouped_data = df_grouped_data.sort_values(
        by=["description"],
        key=lambda x: x.map(custom_order_function(language)),
    )

    # prepare jinja2 values
    ## stats
    passed_checks_totals = df["passedChecks"].sum()
    failed_checks_totals = df["failedChecks"].sum()
    percent_total = "{:.2f}".format(
        passed_checks_totals / (passed_checks_totals + failed_checks_totals) * 100
    )

    ## rows
    my_dict = df_grouped_data.to_dict(orient="list")
    my_dict["passed_checks_totals"] = passed_checks_totals
    my_dict["failed_checks_totals"] = failed_checks_totals
    my_dict["failed_rules_totals"] = (
        (filtered_data["ruleStatus"].str.contains("FAILED")).astype("int").sum()
    )
    my_dict["passed_rules_totals"] = (
        (filtered_data["ruleStatus"].str.contains("PASSED")).astype("int").sum()
    )
    my_dict["percent_total"] = "{:.2f}".format(
        my_dict["passed_rules_totals"]
        / (my_dict["passed_rules_totals"] + my_dict["failed_rules_totals"])
        * 100
    )

    return my_dict
