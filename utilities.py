import os
import shlex
import subprocess


def get_loc(path, only=None):
    """Return the lines-of-code for each language.

    cloc (http://cloc.sourceforge.net/) is used to compute the metrics. The
    method merely parses the output from cloc to return a Python-friendly
    data structure.

    Parameters
    ----------
    path : string
        An absolute path to the source code.
    only : list, optional
        The name(s) of director(y/ies) that must only be included when
        counting the lines-of-code.

    Returns
    -------
    sloc : dictionary
        Dictionary keyed by language with a dictionary containing the metrics
        as the value. The metric dictionary is keyed by 'cloc' for
        comment-lines-of-code and 'sloc' for source-lines-of-code.
    """
    if not (os.path.exists(path) or os.path.isdir(path)):
        raise Exception('%s is an invalid path.' % path)

    sloc = None

    command = 'cloc . --csv'
    if only:
        _only = '(' + '|'.join(only) + ')'
        command = command + ' --match-d=%s --csv' % shlex.quote(_only)

    process = subprocess.Popen(
        command, cwd=path, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    (out, err) = [x.decode() for x in process.communicate()]

    lines = [line for line in out.split('\n') if len(line.strip('\n')) != 0]
    index = -1
    for _index, _line in enumerate(lines):
        if 'files,' in _line:
            index = _index
            break

    if index != -1:
        sloc = dict()
        for _index in range(index + 1, len(lines)):
            components = lines[_index].split(',')
            sloc[components[1]] = {
                'cloc': int(components[3]),
                'sloc': int(components[4])
            }

    return sloc


def search(pattern, path, recursive=True, whole=False, include=None):
    """Search for the presence of a pattern in file.

    grep (http://www.gnu.org/software/grep/manual/grep.html) is used to
    recursively search for the pattern in all files within a specified path.

    Parameters
    ----------
    pattern : string
        A non-empty regular expression to match.
    path : string
        An absolute path to the location where the search is to be performed.
    recursive : bool
        Indicates if the pattern matching should be done recursively on all
        files contained in the location identified by path.
    whole : bool
        Indicates if the pattern matching should use whole word matching.
    include : list, optional
        A list of patterns that specify the files to search.

    Returns
    -------
    bool
        True if the pattern was found, else False.
    """
    if not (os.path.exists(path) or os.path.isdir(path)):
        raise Exception('%s is an invalid path.' % path)

    if not pattern:
        raise Exception('Parameter pattern cannot be emtpy.')

    is_present = False

    command = 'grep -c'
    if recursive:
        command += ' -r'
    if whole:
        command += ' -w'
    if include:
        command += ' --include '
        command += ' --include '.join(shlex.quote(i) for i in include)

    command += ' '
    command += shlex.quote(pattern)

    try:
        subprocess.check_call(
            command, cwd=path, shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        is_present = True
    except subprocess.CalledProcessError as error:
        if error.returncode != 1:
            raise error

    return is_present
