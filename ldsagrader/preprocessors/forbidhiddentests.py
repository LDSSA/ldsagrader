from traitlets import Unicode

from nbgrader.preprocessors import NbGraderPreprocessor


class ForbidHiddenTests(NbGraderPreprocessor):

    begin_test_delimeter = Unicode(
        "BEGIN HIDDEN TESTS",
        help="The delimiter marking the beginning of hidden tests cases",
    ).tag(config=True)

    end_test_delimeter = Unicode(
        "END HIDDEN TESTS", help="The delimiter marking the end of hidden tests cases"
    ).tag(config=True)

    def _detect_hidden_test_region(self, cell):
        # pull out the cell input/source
        lines = cell.source.split("\n")

        for line in lines:
            # begin the test area
            if self.begin_test_delimeter in line or self.end_test_delimeter in line:
                raise RuntimeError("Encountered hidden test region")

    def preprocess_cell(self, cell, resources, cell_index):
        # detect hidden test regions
        self._detect_hidden_test_region(cell)
        return cell, resources
