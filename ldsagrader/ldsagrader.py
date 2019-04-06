import json
import sys

import click
import nbconvert
import nbformat
from traitlets.config import Config

from . import utils


@click.group()
def main():
    pass


@main.command()
@click.argument('notebook', type=click.Path(exists=True))
def checksums(notebook):
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    checksums = utils.calculate_checksums(notebook)
    print(json.dumps(checksums, indent=4))


@main.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--checksums', type=click.Path(exists=True))
def validate(notebook, checksums):
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    with open(checksums) as fp:
        checksums = json.load(fp)

    if utils.is_valid(notebook, checksums):
        print("Notebook passed.")

    else:
        print("Notebook failed!!")
        sys.exit(1)


@main.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--checksums', required=True, type=click.Path(exists=True))
@click.option('--timeout', type=int, default=None)
def grade(notebook, checksums, timeout):
    notebook = nbformat.read(notebook, as_version=nbformat.NO_CONVERT)
    with open(checksums) as fp:
        checksums = json.load(fp)

    c = Config()
    c.NotebookExporter.preprocessors = [
        'nbconvert.preprocessors.ClearOutputPreprocessor',
        'nbconvert.preprocessors.ExecutePreprocessor',
    ]
    c.ExecutePreprocessor.allow_errors = True
    if timeout:
        c.ExecutePreprocessor.timeout = timeout

    print("Executing notebook...")
    exporter = nbconvert.NotebookExporter(config=c)
    notebook, resources = exporter.from_notebook_node(notebook)

    print("Grading notebook...")
    notebook = nbformat.reads(notebook, as_version=nbformat.NO_CONVERT)
    if utils.is_valid(notebook, checksums):
        total_score, max_score = utils.grade(notebook)
        print(f"Score: {total_score}/{max_score}")

    else:
        print("Notebook failed!!")
        sys.exit(1)


if __name__ == '__main__':
    main()
