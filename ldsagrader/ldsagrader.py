import io
import os
import sys

import click
import nbformat
import requests
from requests import HTTPError

from . import utils


config = {
    "token": os.environ.get("LDSA_TOKEN"),
    "grading_url": os.environ.get("LDSA_GRADING_URL"),
    "checksum_url": os.environ.get("LDSA_CHECKSUM_URL"),
    "hackathon_url": os.environ.get("LDSA_HACKATHON_URL"),
}


@click.group()
def main():
    pass


@main.group()
def checksum():
    pass


# noinspection PyShadowingNames
@checksum.command("digest")
@click.argument("notebook", type=click.Path(exists=True))
def checksum_digest(notebook):
    """
    Output grading cell hashes
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    print(utils.calculate_checksum(notebook))


# noinspection PyShadowingNames
@checksum.command("validate")
@click.argument("notebook", type=click.Path(exists=True))
@click.option("--checksum", type=str, required=True)
def checksum_validate(notebook, checksum):
    """
    Validate hashes against notebook
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    if utils.is_valid(notebook, checksum):
        print("Match")

    else:
        print("Checksum mismatch!")
        sys.exit(1)


@main.group()
def notebook():
    pass


# noinspection PyShadowingNames
@notebook.command("validate")
@click.argument("notebook", type=click.Path(exists=True))
@click.option("--checksum", required=False)
@click.option("--timeout", type=int, default=None)
def notebook_validate(notebook, checksum, timeout):
    """
    Validate notebook hashes and grade
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)

    if checksum:
        if not utils.is_valid(notebook, checksum):
            print("Checksum mismatch! (a)")
            sys.exit(1)

    print("Executing notebook...")
    notebook = utils.execute(notebook, timeout, allow_errors=False)

    if checksum:
        if not utils.is_valid(notebook, checksum):
            print("Checksum mismatch! (b)")
            sys.exit(1)

    print("Grading notebook...")
    total_score, max_score = utils.grade(notebook)

    if round(max_score, 5) != 20:
        print("Max score doesn't add to 20")
        sys.exit(1)

    print(f"Score: {total_score}/{max_score}")
    if total_score < max_score:
        print("Total score lower than max score")
        sys.exit(1)

    print("Clearing notebook...")
    utils.clear(notebook)

    print("Notebook OK")


# noinspection PyShadowingNames
@notebook.command("grade")
@click.argument("notebook", type=click.Path(exists=True))
@click.option("--checksum", required=True, type=click.Path(exists=True))
@click.option("--timeout", type=int, default=None)
def notebook_grade(notebook, checksum, timeout):
    """
    Grade notebook running validations
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)

    if not utils.is_valid(notebook, checksum):
        print("Checksum mismatch! (a)")
        sys.exit(1)

    print("Executing notebook...")
    notebook = utils.execute(notebook, timeout)

    print("Grading notebook...")
    if not utils.is_valid(notebook, checksum):
        print("Checksum mismatch! (b)")
        sys.exit(1)

    total_score, max_score = utils.grade(notebook)
    print(f"Score: {total_score}/{max_score}")


# noinspection PyShadowingNames
@notebook.command("execute")
@click.argument("notebook", type=click.Path(exists=True))
@click.option("--timeout", type=int, default=None)
@click.option("--output", type=str)
def notebook_execute(notebook, timeout, output):
    """
    Execute notebook and output results to file
    """
    notebook_path = notebook
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)
    print("Executing notebook...")
    notebook = utils.execute(notebook, timeout)
    print("Writing notebook...")
    if output:
        notebook_path = output
    nbformat.write(notebook, notebook_path)


# noinspection PyShadowingNames
@notebook.command("clear")
@click.argument("notebook", type=click.Path(exists=True))
@click.option("--output", type=str)
def notebook_clear(notebook, output):
    """
    Create student version of notebook
    """
    notebook_path = notebook
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)
    print("Clearing notebook...")
    notebook = utils.clear(notebook)
    print("Writing notebook...")
    if output:
        notebook_path = output
    nbformat.write(notebook, notebook_path)


@main.group()
def academy():
    pass


# noinspection PyShadowingNames,PyBroadException
@academy.command("grade")
@click.option("--timeout", type=int, default=None)
@click.option("--codename", type=str, required=True)
@click.option("--username", type=str, required=True)
def academy_grade(codename, username, timeout):
    """
    Update notebook metadata in db
    """
    print("Starting")
    try:
        notebook_path = utils.find_exercise_nb(codename)
        head, _ = os.path.split(notebook_path)
        notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

        print("Fetching checksum...")
        response = requests.get(
            config["checksum_url"].format(codename=codename),
            headers={"Authorization": f"Token {config['token']}"},
        )
        try:
            response.raise_for_status()
        except HTTPError:
            print(response.content)
            raise
        checksum = response.json()["checksum"]

        # Mark as grading
        response = requests.put(
            config["grading_url"].format(username=username, codename=codename),
            headers={"Authorization": f"Token {config['token']}"},
            json={
                "status": "grading",
                "score": None,
                "notebook": None,
                "message": "",
            },
        )
        try:
            response.raise_for_status()
        except HTTPError:
            print(response.content)
            raise

        print("Validating notebook...")
        if not utils.is_valid(notebook, checksum):
            print("Checksum mismatch! (a)")
            response = requests.put(
                config["grading_url"].format(username=username, codename=codename),
                headers={"Authorization": f"Token {config['token']}"},
                json={
                    "status": "checksum-failed",
                    "score": None,
                    "notebook": None,
                    "message": "",
                },
            )
            try:
                response.raise_for_status()
            except HTTPError:
                print(response.content)
                raise
            sys.exit(1)

        print("Executing notebook...")
        if head:
            cwd = os.getcwd()
            os.chdir(head)
        notebook = utils.execute(notebook, timeout)
        if head:
            os.chdir(cwd)

        if not utils.is_valid(notebook, checksum):
            print("Checksum mismatch! (b)")
            response = requests.put(
                config["grading_url"].format(username=username, codename=codename),
                headers={"Authorization": f"Token {config['token']}"},
                json={
                    "status": "checksum-failed",
                    "score": None,
                    "notebook": None,
                    "message": "",
                },
            )
            try:
                response.raise_for_status()
            except HTTPError:
                print(response.content)
                raise
            sys.exit(1)

        print("Grading notebook...")
        total_score, max_score = utils.grade(notebook)
        print(f"Score: {total_score}/{max_score}")

        print("Posting results...")
        fp = io.StringIO()
        nbformat.write(notebook, fp)
        fp.seek(0)
        response = requests.put(
            config["grading_url"].format(username=username, codename=codename),
            headers={"Authorization": f"Token {config['token']}"},
            data={
                "status": "graded",
                "score": total_score,
                "message": "",
            },
            files={"notebook": ("notebook.ipynb", fp, "application/x-ipynb+json")},
        )
        try:
            response.raise_for_status()
        except HTTPError:
            print(response.content)
            raise

    except Exception as exc:
        response = requests.put(
            config["grading_url"].format(username=username, codename=codename),
            headers={"Authorization": f"Token {config['token']}"},
            json={
                "status": "failed",
                "score": None,
                "notebook": None,
                "message": f"Unhandled exception {str(exc)}",
            },
        )
        response.raise_for_status()
        raise


# noinspection PyShadowingNames
@academy.command("validate")
@click.option("--timeout", type=int, default=None)
@click.option("--codename", type=str, required=True)
@click.option("--checksum", is_flag=True)
def academy_validate(codename, timeout, checksum):
    """
    Validate notebook hashes and grade
    """
    notebook_path = utils.find_exercise_nb(codename)
    head, _ = os.path.split(notebook_path)
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

    if checksum:
        print("Fetching checksum...")
        response = requests.get(
            config["checksum_url"].format(codename=codename),
            headers={"Authorization": f"Token {config['token']}"},
        )
        try:
            response.raise_for_status()
        except HTTPError:
            print(response.content)
            raise
        db_checksum = response.json()["checksum"]

        print("Validating notebook...")
        if not utils.is_valid(notebook, db_checksum):
            print("Checksum mismatch! (a)")
            sys.exit(1)

    print("Executing notebook...")
    if head:
        cwd = os.getcwd()
        os.chdir(head)
    notebook = utils.execute(notebook, timeout, allow_errors=False)
    if head:
        os.chdir(cwd)

    if checksum:
        if not utils.is_valid(notebook, db_checksum):
            print("Checksum mismatch! (b)")
            sys.exit(1)

    print("Grading notebook...")
    total_score, max_score = utils.grade(notebook)
    print(f"Score: {total_score}/{max_score}")

    if round(max_score, 5) != 20:
        print("Max score doesn't add to 20")
        sys.exit(1)

    if total_score < max_score:
        print("Total score lower than max score")
        sys.exit(1)

    print("Clearing notebook...")
    utils.clear(notebook)

    print("Notebook OK")


# noinspection PyShadowingNames
@academy.command("update")
@click.option("--codename", type=str, required=True)
def academy_update(codename):
    """
    Update notebook metadata in db
    """
    notebook_path = utils.find_exercise_nb(codename)
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

    print("Posting checksums...")
    checksum = utils.calculate_checksum(notebook)
    response = requests.patch(
        config["checksum_url"].format(codename=codename),
        headers={"Authorization": f"Token {config['token']}"},
        json={"checksum": checksum},
    )
    try:
        response.raise_for_status()
    except HTTPError:
        print(response.content)
        raise


# noinspection PyShadowingNames
@academy.command("clear")
@click.option("--codename", type=str, required=True)
def academy_clear(codename):
    """
    Replace exercise notebook with student version
    """
    notebook_path = utils.find_exercise_nb(codename)
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)
    print("Clearing notebook...")
    notebook = utils.clear(notebook)
    print("Writing notebook...")
    nbformat.write(notebook, notebook_path)


@academy.command("execute")
@click.option("--timeout", type=int, default=None)
@click.option("--codename", type=str, required=True)
def academy_execute(codename, timeout):
    """
    Run
    """
    notebook_path = utils.find_exercise_nb(codename)
    head, _ = os.path.split(notebook_path)
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

    print("Executing notebook...")
    if head:
        cwd = os.getcwd()
        os.chdir(head)
    notebook = utils.execute(notebook, timeout)
    if head:
        os.chdir(cwd)

    print("Grading notebook...")
    total_score, max_score = utils.grade(notebook)
    print(f"Score: {total_score}/{max_score}")

    nbformat.write(notebook, notebook_path)


# noinspection PyShadowingNames
@academy.command("verify")
@click.option("--timeout", type=int, default=None)
@click.option("--codename", type=str, required=True)
def verify(codename, timeout):
    """
    Validate notebook hashes and grade
    """
    notebook_path = utils.find_exercise_nb(codename)
    head, _ = os.path.split(notebook_path)
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

    print("Executing notebook...")
    if head:
        cwd = os.getcwd()
        os.chdir(head)
    notebook = utils.execute(notebook, timeout, allow_errors=False)
    if head:
        os.chdir(cwd)

    print("Clearing notebook...")
    utils.clear(notebook)

    print("Notebook OK")


@main.group()
def hackathon():
    pass


# noinspection PyShadowingNames
@hackathon.command("update")
@click.option("--codename", type=str, required=True)
def hackathon_update(codename):
    """
    Update hackathon script and data
    """
    hackathon_path = os.path.join(utils.find_path(codename), "portal")
    script_file = os.path.join(hackathon_path, "score.py")
    data_file = os.path.join(hackathon_path, "data")

    print("Posting hackathon...")
    files = {
        "script_file": open(script_file, "rb"),
        "data_file": open(data_file, "rb"),
    }
    response = requests.put(
        config["hackathon_url"].format(codename=codename),
        headers={"Authorization": f"Token {config['token']}"},
        files=files,
    )
    try:
        response.raise_for_status()
    except HTTPError:
        print(response.content)
        raise


@main.group()
def portal():
    pass


# noinspection PyShadowingNames,PyBroadException
@portal.command("grade")
@click.option("--timeout", type=int, default=None)
@click.option("--notebook_path", type=str, required=True)
@click.option("--grading_url", type=str, required=True)
@click.option("--checksum_url", type=str, required=True)
@click.option("--token", type=str, required=True)
def portal_grade(notebook_path, grading_url, checksum_url, token=None, timeout=None):
    """
    Update notebook metadata in db
    """
    print("Starting")
    try:
        head, _ = os.path.split(notebook_path)
        notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

        print("Fetching checksum...")
        response = requests.get(
            checksum_url,
            headers={"Authorization": f"Token {token}"},
        )
        try:
            response.raise_for_status()
        except HTTPError:
            print(response.content)
            raise
        checksum = response.json()["checksum"]

        # Mark as grading
        print("Mark as grading...")
        response = requests.put(
            grading_url,
            headers={"Authorization": f"Token {token}"},
            json={
                "status": "grading",
                "score": None,
                "notebook": None,
                "message": "",
            },
        )
        try:
            response.raise_for_status()
        except HTTPError:
            print(response.content)
            raise

        print("Validating notebook...")
        if not utils.is_valid(notebook, checksum):
            print("Checksum mismatch! (a)")
            response = requests.put(
                grading_url,
                headers={"Authorization": f"Token {token}"},
                json={
                    "status": "checksum-failed",
                    "score": None,
                    "notebook": None,
                    "message": "",
                },
            )
            try:
                response.raise_for_status()
            except HTTPError:
                print(response.content)
                raise
            sys.exit(1)

        print("Executing notebook...")
        if head:
            cwd = os.getcwd()
            os.chdir(head)
        notebook = utils.execute(notebook, timeout)
        if head:
            os.chdir(cwd)

        if not utils.is_valid(notebook, checksum):
            print("Checksum mismatch! (b)")
            response = requests.put(
                grading_url,
                headers={"Authorization": f"Token {token}"},
                json={
                    "status": "checksum-failed",
                    "score": None,
                    "notebook": None,
                    "message": "",
                },
            )
            try:
                response.raise_for_status()
            except HTTPError:
                print(response.content)
                raise
            sys.exit(1)

        print("Grading notebook...")
        total_score, max_score = utils.grade(notebook)
        print(f"Score: {total_score}/{max_score}")

        print("Posting results...")
        fp = io.StringIO()
        nbformat.write(notebook, fp)
        fp.seek(0)
        response = requests.put(
            grading_url,
            headers={"Authorization": f"Token {token}"},
            data={
                "status": "graded",
                "score": total_score,
                "message": "",
            },
            files={"notebook": ("notebook.ipynb", fp, "application/x-ipynb+json")},
        )
        try:
            response.raise_for_status()
        except HTTPError:
            print(response.content)
            raise

    except Exception as exc:
        response = requests.put(
            grading_url,
            headers={"Authorization": f"Token {token}"},
            json={
                "status": "failed",
                "score": None,
                "notebook": None,
                "message": f"Unhandled exception {str(exc)}",
            },
        )
        response.raise_for_status()
        raise


# noinspection PyShadowingNames
@portal.command("validate")
@click.option("--notebook_path", type=str, required=True)
@click.option("--timeout", type=int, default=None)
def portal_validate(notebook_path, timeout):
    """
    Validate notebook hashes and grade
    """
    head, _ = os.path.split(notebook_path)
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

    print("Executing notebook...")
    if head:
        cwd = os.getcwd()
        os.chdir(head)
    notebook = utils.execute(notebook, timeout, allow_errors=False)
    if head:
        os.chdir(cwd)

    print("Grading notebook...")
    total_score, max_score = utils.grade(notebook)
    print(f"Score: {total_score}/{max_score}")

    if round(max_score, 5) != 20:
        print("Max score doesn't add to 20")
        sys.exit(1)

    if total_score < max_score:
        print("Total score lower than max score")
        sys.exit(1)

    print("Clearing notebook...")
    utils.clear(notebook)

    print("Notebook OK")


# noinspection PyShadowingNames
@portal.command("update")
@click.option("--notebook_path", type=str, required=True)
@click.option("--checksum_url", type=str, required=True)
@click.option("--token", type=str, required=True)
def portal_update(notebook_path, checksum_url, token):
    """
    Update notebook metadata in db
    """
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

    print("Posting checksums...")
    checksum = utils.calculate_checksum(notebook)
    response = requests.patch(
        checksum_url,
        headers={"Authorization": f"Token {token}"},
        json={"checksum": checksum},
    )
    try:
        response.raise_for_status()
    except HTTPError:
        print(response.content)
        raise


if __name__ == "__main__":
    main()
