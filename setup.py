import sys, glob, os
import shutil
import libreosteoweb

version = libreosteoweb.__version__


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def remove_useless_files(directory, keepfiles_list, keepdir_list):
    keep_path_list = []
    for root, directories, files in os.walk(directory):
        for d in directories:
            if d in keepdir_list or root in keep_path_list:
                keep_path_list.append(os.path.join(root, d))
        for f in files:
            if root not in keep_path_list and f not in keepfiles_list:
                os.remove(os.path.join(root, f))
        for d in directories:
            if os.path.join(root, d) not in keep_path_list:
                shutil.rmtree(os.path.join(root, d))


def execute_cmd_context(cmd):
    from subprocess import run
    run("activate;"+cmd, shell=True, env=os.environ.copy())

def collectstatic():
    print("Collect static")
    cmd="python manage.py collectstatic --no-input"
    execute_cmd_context(cmd)

def compress():
    print("Compress css/js")
    cmd = "python manage.py compress --force"
    execute_cmd_context(cmd)

def compilejsi18n():
    print("Compile JsI18n")
    cmd = "python manage.py compilejsi18n"
    execute_cmd_context(cmd)

def get_zipcodes():
    print("Retrieve ZipCode dataset")
    execute_cmd_context("python manage.py import_zipcodes --download-only")


def purge_static():
    purge_dir = ['components']
    keep_path = ['components/webshim']
    to_remove_list = []
    # For each dir in purge dir from static :
    # delete each files
    for root, directories, files in os.walk('static'):
        for p in purge_dir:
            for d in directories:
                if root == os.path.join('static', p):
                    for a in keep_path:
                        if d not in os.path.split(a):
                            shutil.rmtree(os.path.join(root, d))


# Build on Windows.
#
# usage :
#     python setup.py build_exe
#
if sys.platform in ['win32']:

    # before all of things : collectstatic
    collectstatic()

    compilejsi18n()

    compress()

    get_zipcodes()

    from cx_Freeze import setup, Executable
    import zipfile
    # GUI applications require a different base on Windows (the default is for a
    # console application).
    base = 'Console'
    import os.path
    PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))
    os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl',
                                             'tcl8.6')
    os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')
    import compressor

    def get_djangolocale():
        os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                              "Libreosteo.settings.standalone")
        import django
        directory = os.path.join(django.__path__[0], 'conf', 'locale')
        return [(directory, 'django/conf/locale')]

    def add_jaraco_files():
        import jaraco
        directory = os.path.join(jaraco.__path__[0], 'text')
        zipf = zipfile.ZipFile('build/exe.%s-%s/lib/library.zip' % (get_platform_identifier(), sys.winver[0:3]), "a")
        zipf.write(os.path.join(directory, 'Lorem ipsum.txt'), os.path.join('jaraco', 'text', 'Lorem ipsum.txt'))
        zipf.close()

    def get_platform_identifier():
        platform_identifier = sys.platform
        if os.environ['PROCESSOR_ARCHITECTURE'].lower() == 'amd64':
            platform_identifier = 'win-%s' % os.environ['PROCESSOR_ARCHITECTURE'].lower()
        return platform_identifier


    def compressor_path(t):
        (c, c1) = t
        return (c, c1.replace(compressor.__path__[0] + os.sep, ''))

    def get_compressor_templates():
        directory = os.path.join(compressor.__path__[0], 'templates')
        list_files = get_filepaths(directory)
        return list(map(compressor_path, list_files))

    def get_filepaths(directory, pyc_only=False):
        """
        This function will generate the file names in a directory
        tree by walking the tree either top-down or bottom-up. For each
        directory in the tree rooted at directory top (including top itself),
        it yields a 3-tuple (dirpath, dirnames, filenames).
        """
        file_paths = []  # List which will store all of the full filepaths.

        # Walk the tree.
        for root, directories, files in os.walk(directory):
            for filename in files:
                if pyc_only and not filename.endswith('.pyc'):
                    continue
                # Join the two strings in order to form the full filepath.
                filepath = os.path.join(root, filename)
                file_paths.append((filepath, filepath))  # Add it to the list.
            for d in directories:
                rec_d = os.path.join(root, d)
                file_paths + get_filepaths(rec_d)

        return file_paths  # Self-explanatory.

    def include_migration_files(directory):
        """
        This function will generate the include from the list of python
        migration files in the directory
        """
        migration_files = []
        for root, directories, files in os.walk(directory):
            for filename in files:
                if (filename.endswith('.py')
                    ) and not (filename.startswith('__')):
                    migration_files.append(
                        directory.replace('/', '.') + '.' +
                        filename[0:len(filename) - 3])
        return migration_files

    from cx_Freeze import setup, Executable
    copyDependentFiles = True
    includes = [
        'cherrypy',
        'win32serviceutil',
        'win32service',
        'win32event',
        'servicemanager',
        'win32timezone',
        'django.template.loader_tags',
        'django.core.management',
        'Libreosteo',
        'Libreosteo.urls',
        'Libreosteo.settings',
        'Libreosteo.wsgi',
        'Libreosteo.zip_loader',
        'libreosteoweb.admin',
        'libreosteoweb.middleware',
        'libreosteoweb.management',
        'libreosteoweb.models',
        'libreosteoweb.search_indexes',
        'libreosteoweb.api',
        'libreosteoweb.apps',
        'libreosteoweb.templatetags.invoice_extras',
        'email.mime.image',
        "rcssmin",
        "rjsmin",
        "jaraco.text"
    ]
    migrations = [
        'libreosteoweb.migrations', "django.contrib.admin.migrations",
        "django.contrib.auth.migrations",
        "django.contrib.contenttypes.migrations",
        "django.contrib.sessions.migrations"
    ]

    include_files = get_filepaths('media') + get_filepaths(
        'locale') + [('zipcode_dataset.json', 'zipcode_dataset')]
    extra_includes = get_filepaths(
        'templates') + get_compressor_templates() + get_filepaths('static') 
    packages = [
        "os",
        "django",
        #"htmlentitydefs",
        #"HTMLParser",
        #"Cookie",
        'http',
        "gettext",
        'html',
        "rest_framework",
        "haystack",
        "sqlite3",
        "statici18n",
        "email",
        "Libreosteo",
        "compressor",
        "libreosteoweb",
        "pkg_resources._vendor",
        "django_filters",
        "jaraco",
        "zipcode_lookup",
        "django.core.management.commands",
        "zipcode_lookup.management.commands",
        "libreosteoweb.management.commands",
        "protected_media"
    ]
    in_zip_packages = includes + [
        '_markerlib', 'appconf', 'backports', 'cheroot', 'compiler',
        'compressor', 'ctypes', 'distutils', 'django_filters', 'email',
        'encodings', 'haystack', 'importlib', 'json', 'logging',
        'more_itertools', 'multiprocessing', 'pkg_resources', 'pydoc_data',
        'rest_framework', 'rest_framework_csv', 'sqlite3', 'sqlparse',
        'statici18n', 'tempora', 'test', 'unittest', 'whoosh', 'wsgiref'
        'xml'
    ]
    build_exe_options = {
        "packages": packages,
        "includes": includes + migrations,
        "include_files": include_files + extra_includes,
        "zip_includes" : extra_includes,
        "excludes": ['cStringIO', 'tcl', 'Tkinter'],
        "no_compress" : False,
        "optimize": 2,
        "zip_include_packages": in_zip_packages,
        "zip_exclude_packages": ['libreosteoweb'],
        "include_msvcr": True
    }

    setup(name="LibreOsteo",
          version=version,
          description="LibreOsteo, suite for osteopaths",
          options={"build_exe": build_exe_options},
          executables=[
              Executable("winserver.py",
                         base=base,
                         targetName="LibreOsteo.exe"),
              Executable("manage.py", base=base, targetName="manager.exe"),
              Executable("application.py",
                         base=base,
                         targetName="launcher.exe")
          ])

    # Create a web shorcut link
    build_dir = glob.glob('build/exe.%s-%s' % (get_platform_identifier(), sys.winver[:3]))
    for b in build_dir:
        shortlink = open(b + "/LibreOsteo.url", "w")
        shortlink.write("[InternetShortcut]\n")
        shortlink.write("URL=http://localhost:8085/\n")
        shortlink.write("\n")
        shortlink.write("\n")

        ##Remove useless locales
        remove_useless_files(b + "/django/conf/locale", [],
                             ["fr", "en"])
        remove_useless_files(b + "lib/django/conf/locale", [], ['fr', 'en'])
        remove_useless_files(
            b + "/static/components/angular-i18n", [
                "angular-locale_en.js", "angular-locale_en-us.js",
                "angular-locale_fr.js", "angular-locale_fr-fr.js"
            ], [])

    ## Patch django migration loader
    from patch import patch_django_loader_pyc
    print("Platform identifier : %s" % get_platform_identifier())
    patch_django_loader_pyc('build/exe.%s-%s/' % (get_platform_identifier(), sys.winver[:3]))

    # Restore file for jaraco
    add_jaraco_files()

#### MACOS X build
#
# Usage:
#        python setup.py py2app

if sys.platform in ['darwin']:
    from setuptools import setup

    # before all of things : collectstatic
    collectstatic()

    compilejsi18n()

    compress()

    APP = ['server.py']

    DATA_FILES = ['static', 'locale', 'templates']

    OPTIONS = {
        'argv_emulation':
        True,
        'includes': [
            #    'HTMLParser',
        ],
        'packages': [
            "django",
            "Libreosteo",
            "libreosteoweb",
            "zipcode_lookup",
            "rest_framework",
            "haystack",
            "sqlite3",
            "statici18n",
            "email",
            "compressor",
            "django_filters",
            "protected_media",
        ],
        'plist': {
            'LSBackgroundOnly': True,
            'LSUIElement': False,
            'CFBundleIdentifier': 'org.libreosteo.macos.libreosteo.service',
            'CFBundleGetInfoString': 'LibreOsteoService',
            'CFBundleDisplayName': 'LibreOsteoService',
            'CFBundleName': 'LibreOsteoService',
            'CFBundleShortVersionString': version,
            'CFBundleVersion': version,
        },
        'extra_scripts': ['application.py', 'manage.py'],
        'optimize':
        True,
        'iconfile':
        'libreosteoweb/static/images/favicon.icns',
    }
    setup(
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app'],
    )
    remove_useless_files(
        "build/exe.win32-2.7/static/bower_components/angular-i18n", [
            "angular-locale_en.js", "angular-locale_en-us.js",
            "angular-locale_fr.js", "angular-locale_fr-fr.js"
        ], [])
elif sys.platform not in ['win32']:

    # before all of things : collectstatic
    collectstatic()

    compilejsi18n()

    compress()

    from cx_Freeze import setup, Executable
    # GUI applications require a different base on Windows (the default is for a
    # console application).
    base = 'Console'

    def get_djangolocale():
        os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                              "Libreosteo.settings.standalone")
        import django
        directory = os.path.join(django.__path__[0], 'conf', 'locale')
        return [(directory, 'django/conf/locale')]

    def get_compressor_templates():
        import compressor
        directory = os.path.join(compressor.__path__[0], 'templates')
        list_files = get_filepaths(directory)
        return map(
            lambda c: (c, c.replace(compressor.__path__[0] + os.sep, '')),
            list_files)

    def get_filepaths(directory):
        """
        This function will generate the file names in a directory
        tree by walking the tree either top-down or bottom-up. For each
        directory in the tree rooted at directory top (including top itself),
        it yields a 3-tuple (dirpath, dirnames, filenames).
        """
        file_paths = []  # List which will store all of the full filepaths.

        # Walk the tree.
        for root, directories, files in os.walk(directory):
            for filename in files:
                # Join the two strings in order to form the full filepath.
                filepath = os.path.join(root, filename)
                file_paths.append(filepath)  # Add it to the list.

        return file_paths  # Self-explanatory.

    def include_migration_files(directory):
        """
        This function will generate the include from the list of python
        migration files in the directory
        """
        migration_files = []
        for root, directories, files in os.walk(directory):
            for filename in files:
                if (filename.endswith('.py')
                    ) and not (filename.startswith('__')):
                    migration_files.append(
                        directory.replace('/', '.') + '.' +
                        filename[0:len(filename) - 3])
        return migration_files

    from cx_Freeze import setup, Executable
    copyDependentFiles = True
    includes = [
        'cherrypy',
        'django.template.loader_tags',
        'django.core.management',
        'Libreosteo',
        'Libreosteo.urls',
        'Libreosteo.settings',
        'Libreosteo.wsgi',
        'Libreosteo.zip_loader',
        'libreosteoweb',
        'libreosteoweb.admin',
        'libreosteoweb.middleware',
        'libreosteoweb.models',
        'libreosteoweb.search_indexes',
        'libreosteoweb.api',
        'libreosteoweb.apps',
        'libreosteoweb.templatetags.invoice_extras',
        'email.mime.image',
        "django.contrib.admin.migrations.0001_initial",
        "django.contrib.auth.migrations.0001_initial",
        "django.contrib.auth.migrations.0002_alter_permission_name_max_length",
        "django.contrib.auth.migrations.0003_alter_user_email_max_length",
        "django.contrib.auth.migrations.0004_alter_user_username_opts",
        "django.contrib.auth.migrations.0005_alter_user_last_login_null",
        "django.contrib.auth.migrations.0006_require_contenttypes_0002",
        "django.contrib.contenttypes.migrations.0001_initial",
        "django.contrib.contenttypes.migrations.0002_remove_content_type_name",
        "django.contrib.sessions.migrations.0001_initial",
        "rcssmin",
        "rjsmin",
    ] + include_migration_files('libreosteoweb/migrations')

    include_files = get_filepaths('static') + get_filepaths(
        'locale') + get_djangolocale() + get_filepaths('media')
    zip_includes = get_filepaths('templates') + get_compressor_templates()
    packages = [
        "os",
        "django",
        "htmlentitydefs",
        "HTMLParser",
        "Cookie",
        "rest_framework",
        "haystack",
        "sqlite3",
        "statici18n",
        "email",
        "Libreosteo",
        "compressor",
    ]
    namespace_packages = ["jaraco"]
    build_exe_options = {
        "packages": packages,
        "includes": includes,
        #"include_files": include_files,
        "zip_includes": zip_includes + include_files,
        "excludes": ['cStringIO', 'tcl', 'Tkinter'],
        #"compressed" : True,
        #"create_shared_zip": True,
        #"append_script_to_exe": True,
        #"include_in_shared_zip" : True,
        "optimize": 2,
        "namespace_packages": namespace_packages,
        "zip_include_packages": ["*"],
        "zip_exclude_packages": [],
    }

    setup(name="libreosteo",
          version=version,
          description="LibreOsteo, suite for osteopaths",
          options={"build_exe": build_exe_options},
          executables=[
              Executable("server.py", base=base, targetName="libreosteo"),
              Executable("manager.py", base=base)
          ])
