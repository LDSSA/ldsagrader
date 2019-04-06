from nbgrader import utils


def calculate_checksums(nb):
    checksums = {}
    for cell in nb.cells:
        if utils.is_grade(cell):
            grade_id = cell.metadata.nbgrader['grade_id']
            checksum = utils.compute_checksum(cell)
            checksums[grade_id] = checksum

    return checksums


def grade(nb):
    total_score = 0
    max_total_score = 0
    for cell in nb.cells:
        if utils.is_grade(cell):
            score, max_score = utils.determine_grade(cell)
            total_score += score
            max_total_score += max_score

    return total_score, max_total_score


def is_valid(nb, checksums):
    for cell in nb.cells:
        if utils.is_grade(cell):
            grade_id = cell.metadata.nbgrader['grade_id']
            try:
                old_checksum = checksums[grade_id]
            except KeyError:
                raise RuntimeError('Unknow grade_id found `%s`', grade_id)

            if old_checksum != utils.compute_checksum(cell):
                raise RuntimeError('Checksum for grade cell `%s` changed',
                                   grade_id)
    return True
