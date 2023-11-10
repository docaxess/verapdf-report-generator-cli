import os
import subprocess
from pathlib import Path
from io import BytesIO
import datetime
from tempfile import TemporaryDirectory, NamedTemporaryFile
from io import BytesIO
import mimetypes


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


def run_checker_from_byte_file(file_byte: BytesIO) -> str | None:
    with TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "input.pdf")
        with open(file_path, "wb") as f:
            f.write(file_byte.getbuffer())

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
                file_path,
            ],
            cwd="app/infrastructure/pdf_checker/service/verapdf",
            capture_output=True,
            text=True,
        )
        output = str(completed_process.stdout)

    return output
