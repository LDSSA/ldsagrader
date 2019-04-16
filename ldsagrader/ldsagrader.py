import io
import os
import sys
from urllib.parse import urljoin

import click
import nbformat
import requests

from . import utils


config = {
    'token': os.environ.get('TOKEN'),
    'grading_url': os.environ.get('GRADING_url'),
    'checksum_url': os.environ.get('CHECKSUM_URL'),
}


@click.group()
def main():
    pass


@main.group()
def checksum():
    pass


# noinspection PyShadowingNames
@checksum.command('digest')
@click.argument('notebook', type=click.Path(exists=True))
def checksum_digest(notebook):
    """
    Output grading cell hashes
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    print(utils.calculate_checksum(notebook))


# noinspection PyShadowingNames
@checksum.command('validate')
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--checksum', type=str, required=True)
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
@notebook.command('validate')
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--checksum', required=True)
@click.option('--timeout', type=int, default=None)
def notebook_validate(notebook, checksum, timeout):
    """
    Validate notebook hashes and grade
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)

    if not utils.is_valid(notebook, checksum):
        print("Checksum mismatch! (a)")
        sys.exit(1)

    print("Executing notebook...")
    notebook = utils.execute(notebook, timeout, allow_errors=False)

    if not utils.is_valid(notebook, checksum):
        print("Checksum mismatch! (b)")
        sys.exit(1)

    print("Grading notebook...")
    notebook = nbformat.reads(notebook, as_version=nbformat.NO_CONVERT)
    total_score, max_score = utils.grade(notebook)

    if round(max_score, 5) != 20:
        print("Max score doesn't add to 20")
        sys.exit(1)

    print(f"Score: {total_score}/{max_score}")
    if total_score < max_score:
        print("Total score lower than max score")
        sys.exit(1)

    print("Notebook OK")


# noinspection PyShadowingNames
@notebook.command('grade')
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--checksum', required=True, type=click.Path(exists=True))
@click.option('--timeout', type=int, default=None)
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

    notebook = nbformat.reads(notebook, as_version=nbformat.NO_CONVERT)
    total_score, max_score = utils.grade(notebook)
    print(f"Score: {total_score}/{max_score}")


# noinspection PyShadowingNames
@notebook.command('execute')
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--timeout', type=int, default=None)
@click.option('--output', type=str)
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
@notebook.command('clear')
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--output', type=str)
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


# noinspection PyShadowingNames
@academy.command('grade')
@click.option('--timeout', type=int, default=None)
@click.option('--codename', type=str, required=True)
@click.option('--gh-handle', type=str, required=True)
def academy_grade(codename, gh_handle, timeout):
    """
    Update notebook metadata in db
    """
    try:
        notebook_path = utils.find_notebook(codename)
        notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

        print("Fetching checksums...")
        response = requests.get(
            urljoin(config['checksum_url'], codename),
            headers={'Authorization': config['token']},
        )
        response.raise_for_status()
        checksum = response.json()['checksum']

        print("Validating notebook...")
        if not utils.is_valid(notebook, checksum):
            print("Checksum mismatch! (a)")
            requests.post(
                urljoin(config['grading_url'], gh_handle),
                headers={'Authorization': config['token']},
                json={'score': None, 'status': 'out-of-date'},
            )
            sys.exit(0)

        print("Executing notebook...")
        notebook = utils.execute(notebook, timeout)

        if not utils.is_valid(notebook, checksum):
            print("Checksum mismatch! (b)")
            requests.post(
                urljoin(config['grading_url'], gh_handle),
                headers={'Authorization': config['token']},
                json={'score': 0, 'status': 'out-of-date'},
            )
            sys.exit(0)

        print("Grading notebook...")
        notebook = nbformat.reads(notebook, as_version=nbformat.NO_CONVERT)
        total_score, max_score = utils.grade(notebook)
        print(f"Score: {total_score}/{max_score}")

        print("Posting results...")
        fp = io.StringIO()
        nbformat.write(notebook, fp)
        response = requests.post(
            urljoin(config['grading_url'], gh_handle),
            headers={'Authorization': config['token']},
            json={'score': total_score, 'status': 'graded'},
            files={
                'file': ('notebook.ipynb', fp, 'application/x-ipynb+json')
            },
        )
        response.raise_for_status()

    except Exception:
        response = requests.post(
            urljoin(config['grading_url'], gh_handle),
            headers={'Authorization': config['token']},
            json={'score': None, 'status': 'failed'},
        )
        response.raise_for_status()


# noinspection PyShadowingNames
@academy.command('update')
@click.option('--codename', type=str, required=True)
def academy_update(codename):
    """
    Update notebook metadata in db
    """
    notebook_path = utils.find_notebook(codename)
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)

    print("Posting checksums...")
    checksum = utils.calculate_checksum(notebook)
    response = requests.get(
        urljoin(config['checksum_url'], codename),
        headers={'Authorization': config['token']},
        json={
            'checksum': checksum,
        }
    )
    response.raise_for_status()


# noinspection PyShadowingNames
@academy.command('clear')
@click.option('--codename', type=str, required=True)
def academy_clear(codename):
    """
    Replace exercise notebook with student version
    """
    notebook_path = utils.find_notebook(codename)
    notebook = nbformat.read(notebook_path, as_version=nbformat.NO_CONVERT)
    print("Clearing notebook...")
    notebook = utils.clear(notebook)
    print("Writing notebook...")
    nbformat.write(notebook, notebook_path)


if __name__ == '__main__':
    main()
