import json
import sys

import click
import nbconvert
import nbformat
from traitlets.config import Config

from . import utils


def execute(notebook, timeout=None, allow_errors=True):
    c = Config()
    c.NotebookExporter.preprocessors = [
        'nbconvert.preprocessors.ClearOutputPreprocessor',
        'nbconvert.preprocessors.ExecutePreprocessor',
    ]
    c.ExecutePreprocessor.allow_errors = allow_errors
    if timeout:
        c.ExecutePreprocessor.timeout = timeout

    print("Executing notebook...")
    exporter = nbconvert.NotebookExporter(config=c)
    notebook, resources = exporter.from_notebook_node(notebook)

    return notebook


@click.group()
def main():
    pass


@main.group()
def checksum():
    pass


@checksum.command('digest')
@click.argument('notebook', type=click.Path(exists=True))
def checksum_digest(notebook):
    """
    Output grading cell hashes
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    checksums = utils.calculate_checksums(notebook)
    print(json.dumps(checksums, indent=4))


@checksum.command('validate')
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--checksums', type=click.Path(exists=True))
def checksum_validate(notebook, checksums):
    """
    Validate hashes against notebook
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    with open(checksums) as fp:
        checksums = json.load(fp)

    if utils.is_valid(notebook, checksums):
        print("Notebook passed.")

    else:
        print("Notebook failed!!")
        sys.exit(1)


@main.group()
def notebook():
    pass


@notebook.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--checksums', required=True, type=click.Path(exists=True))
@click.option('--timeout', type=int, default=None)
def notebook_validate(notebook, checksums, timeout):
    """
    Validate notebook hashes and grade
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    with open(checksums) as fp:
        checksums = json.load(fp)

    notebook = execute(notebook, timeout, allow_errors=False)

    print("Grading notebook...")
    notebook = nbformat.reads(notebook, as_version=nbformat.NO_CONVERT)
    if utils.is_valid(notebook, checksums):
        total_score, max_score = utils.grade(notebook)
        print(f"Score: {total_score}/{max_score}")
        if total_score < max_score:
            print("Notebook failed!!")
            sys.exit(1)

    else:
        print("Notebook failed!!")
        sys.exit(1)


@notebook.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--checksums', required=True, type=click.Path(exists=True))
@click.option('--timeout', type=int, default=None)
def notebook_grade(notebook, checksums, timeout):
    """
    Grade notebook running validations
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    with open(checksums) as fp:
        checksums = json.load(fp)

    notebook = execute(notebook, timeout)

    print("Grading notebook...")
    notebook = nbformat.reads(notebook, as_version=nbformat.NO_CONVERT)
    if utils.is_valid(notebook, checksums):
        total_score, max_score = utils.grade(notebook)
        print(f"Score: {total_score}/{max_score}")

    else:
        print("Notebook failed!!")
        sys.exit(1)


@notebook.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--timeout', type=int, default=None)
@click.option('--output', type=str, required=True)
def notebook_execute(notebook, timeout, output):
    """
    Execute notebook and output results to file
    """
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    notebook = execute(notebook, timeout)
    nbformat.write(notebook, output)


@notebook.command()
def notebook_assign():
    """
    Create student version of notebook
    """
    pass


@main.group()
def academy():
    pass


@academy.command()
def academy_update():
    """
    Update notebook metadata in db
    """
    pass


if __name__ == '__main__':
    main()
