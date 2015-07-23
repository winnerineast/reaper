import distutils
import importlib
import os
import sys
import types
import traceback

import attributes

from lib import utilities


class Attribute(object):
    def __init__(self, attribute):
        self.name = attribute.get('name', '')
        self.initial = attribute.get('initial', '').lower()
        self.weight = attribute.get('weight', 0.0)
        self.enabled = attribute.get('enabled', True)
        self.essential = attribute.get('essential', False)
        self.persist = attribute.get('persist', True)
        self.dependencies = attribute.get('dependencies', list())
        self.options = attribute.get('options', dict())
        self.reference = importlib.import_module('{0}.main'.format(self.name))

    def __getstate__(self):
        state = self.__dict__.copy()
        if isinstance(self.reference, types.ModuleType):
            state['reference'] = self.reference.__name__
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        if isinstance(self.reference, str):
            self.reference = importlib.import_module(
                '{0}.main'.format(self.name)
            )


class Attributes(object):
    def __init__(self, attributes, database, keystring=None):
        self.attributes = None
        self.database = database

        self._parse_attributes(attributes)
        self._parse_keystring(keystring)

    def global_init(self, samples):
        try:
            if not self._validate_dependencies():
                raise Exception(
                    'Missing dependencies must be installed to continue.'
                )

            self.database.connect()
            for attribute in self.attributes:
                if hasattr(attribute.reference, 'global_init'):
                    with self.database.cursor() as cursor:
                        attribute.reference.global_init(cursor, samples)
        finally:
            self.database.disconnect()

    def run(self, project_id, repository_root):
        invalidated = False
        score = 0
        rresults = dict()

        try:
            self.database.connect()

            repository_path = os.path.join(repository_root, str(project_id))
            repository_path = self._init_repository(
                project_id, repository_path
            )
            for attribute in self.attributes:
                rresults[attribute.name] = None

                if attribute.enabled:
                    with self.database.cursor() as cursor:
                        if hasattr(attribute.reference, 'init'):
                            attribute.reference.init(cursor)

                    with self.database.cursor() as cursor:
                        (bresult, rresult) = attribute.reference.run(
                            project_id, repository_path,
                            cursor, **attribute.options
                        )
                    rresults[attribute.name] = rresult

                    if not bresult and attribute.essential:
                        score = 0
                        invalidated = True

                    if not invalidated:
                        score += bresult * attribute.weight
        except:
            sys.stderr.write('Exception\n\n')
            sys.stderr.write('  Project ID   {0}\n'.format(project_id))
            extype, exvalue, extrace = sys.exc_info()
            traceback.print_exception(extype, exvalue, extrace)
        finally:
            self.database.disconnect()
            return (score, rresults)

    def get(self, name):
        for attribute in self.attributes:
            if attribute.name == name:
                return attribute

    def _init_repository(self, project_id, repository_home):
        repository_path = repository_home  # Default

        if not os.path.exists(repository_path):
            os.mkdir(repository_path)

        items = os.listdir(repository_path)
        if items:
            for item in os.listdir(repository_path):
                itempath = os.path.join(repository_path, item)
                if os.path.isdir(itempath):
                    repository_path = itempath
                    break
        else:
            url = self.database.get(
                'SELECT url FROM projects WHERE id = {0}'.format(
                    project_id
                )
            )
            if not url:
                raise ValueError('Invalid project ID {0}.'.format(project_id))
            url += '/tarball'

            sha = self.database.get(
                '''
                    SELECT c.sha
                    FROM project_commits pc
                        JOIN commits c ON c.id = pc.commit_id
                    WHERE pc.project_id = {0}
                    ORDER BY c.created_at DESC
                    LIMIT 1
                '''.format(project_id)
            )
            if sha:
                url += '/{0}'.format(sha)

            # TODO: Remove
            url += '?access_token=563ffe4afe38ca48404e441cf98223a87c4596ab'

            repository_path = utilities.download(url, repository_path)

        return repository_path

    def _parse_attributes(self, attributes):
        if attributes:
            self.attributes = list()
            for (identifier, attribute) in enumerate(attributes):
                self.attributes.append(Attribute(attribute))

    def _disable_attributes(self):
        for attribute in self.attributes:
            attribute.enabled = False

    def _disable_persistence(self):
        for attribute in self.attributes:
            attribute.persist = False

    def _parse_keystring(self, keystring):
        if keystring:
            # Clean the slate
            self._disable_attributes()
            self._disable_persistence()

            for key in keystring:
                attribute = next(
                    attribute
                    for attribute in self.attributes
                    if attribute.initial == key.lower()
                )
                attribute.enabled = True
                attribute.persist = key.isupper()

    def _validate_dependencies(self):
        valid = True
        for attribute in self.attributes:
            if attribute.enabled and attribute.dependencies:
                for dependency in attribute.dependencies:
                    if not distutils.spawn.find_executable(dependency):
                        sys.stderr.write(
                            '[{0}] Dependency {1} missing\n'.format(
                                attribute.name, dependency
                            )
                        )
                        valid = False
        return valid