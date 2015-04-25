import utilities
from attributes.unit_test.discoverer import TestDiscoverer

LANGUAGE = 'Java'


class JavaTestDiscoverer(TestDiscoverer):
    def __init__(self):
        self.frameworks = [
            self.__junit__
        ]

    def __junit__(self, path):
        proportion = -1

        if utilities.search('junit', path, include=['pom.xml']):
            files = utilities.search(
                'import (org.junit|junit.framework)',
                path, include=['*.java']
            )

            if files:
                # SLOC of source code
                sloc_code = utilities.get_loc(path)

                # SLOC of test code
                sloc_test = utilities.get_loc(path, files=files)

                if LANGUAGE in sloc_code and LANGUAGE in sloc_test:
                    proportion = (
                        sloc_test[LANGUAGE]['sloc'] /
                        sloc_code[LANGUAGE]['sloc']
                    )

        return proportion