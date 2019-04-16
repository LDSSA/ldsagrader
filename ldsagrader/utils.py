import hashlib
import os

import nbformat
import nbconvert
from nbgrader import utils
from traitlets.config import Config


def find_notebook(codename):
    spec, lu = codename.split('/')
    for spec_path in os.listdir():
        if spec_path.startswith(spec):
            break

    else:
        raise RuntimeError("Specialization directory not found")

    for lu_path in os.listdir(spec_path):
        if lu_path.startswith(lu):
            break

    else:
        raise RuntimeError("Learning Unit directory not found")

    return os.path.join(spec_path, lu_path, "Exercise notebook.ipynb")


def calculate_checksum(nb):
    m = hashlib.sha256()
    for cell in nb.cells:
        if utils.is_grade(cell):
            grade_id = cell.metadata.nbgrader['grade_id']
            checksum = utils.compute_checksum(cell)
            m.update(grade_id.encode('utf-8'))
            m.update(checksum.encode('utf-8'))

    return m.hexdigest()


def grade(nb):
    total_score = 0
    max_total_score = 0
    for cell in nb.cells:
        if utils.is_grade(cell):
            score, max_score = utils.determine_grade(cell)
            total_score += score
            max_total_score += max_score

    return total_score, max_total_score


def is_valid(nb, checksum):
    return calculate_checksum(nb) == checksum


def execute(notebook, timeout=None, allow_errors=True):
    c = Config()
    c.NotebookExporter.preprocessors = [
        'nbconvert.preprocessors.ClearOutputPreprocessor',
        'nbconvert.preprocessors.ExecutePreprocessor',
    ]
    c.ExecutePreprocessor.allow_errors = allow_errors
    if timeout:
        c.ExecutePreprocessor.timeout = timeout

    exporter = nbconvert.NotebookExporter(config=c)
    notebook, _ = exporter.from_notebook_node(notebook)

    return nbformat.reads(notebook, as_version=nbformat.NO_CONVERT)


def clear(notebook):
    c = Config()
    c.NotebookExporter.preprocessors = [
        'nbconvert.preprocessors.ClearOutputPreprocessor',
        'nbgrader.preprocessors.ClearSolutions',
    ]
    exporter = nbconvert.NotebookExporter(config=c)
    notebook, _ = exporter.from_notebook_node(notebook)

    return nbformat.reads(notebook, as_version=nbformat.NO_CONVERT)
