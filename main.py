from __future__ import annotations

import os
import subprocess
import threading

import sublime
import sublime_plugin

from .scripts.utils import get_all_packages

ST_VERSION = int(sublime.version())


class CloneLspProjectsCommand(sublime_plugin.WindowCommand):
    def run(self):
        t = threading.Thread(target=clone, args=(self.window,))
        t.start()

def clone(window: sublime.Window):
    packages_path = sublime.packages_path()
    variables = window.extract_variables()

    for package in get_all_packages(ST_VERSION):
        already_exist = os.path.exists(os.path.join(packages_path, package['name']))
        if already_exist:
            print('Project {} already exist'.format(package['name']))
            continue
        ssh_repo_link = package['details'].replace("https://github.com/", "git@github.com:") + ".git"
        setup_command = ["git", "clone", ssh_repo_link, f"${{packages}}/{package['name']}"]
        cmd = sublime.expand_variables(setup_command, variables)
        print('Running setup command for {}:\n{}'.format(package['name'], cmd))
        window.status_message('Setting up {}.'.format(package['name']))
        run_command(cmd)

    sublime.message_dialog('LSP maintainer: Cloning is done.')


class OpenLspProjectsCommand(sublime_plugin.WindowCommand):
    def run(self):
        packages_path = sublime.packages_path()
        project_data = self.window.project_data() or {}
        folders = project_data.get('folders') or []

        for package in get_all_packages(ST_VERSION):
            package_path = os.path.join(packages_path, package['name'])
            folders.append({"path": package_path})
        self.window.set_project_data({
            'folders': folders
        })


def run_command(cmd, cwd=None):
    p = subprocess.Popen(cmd,
                         cwd=cwd,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output, _stderr = p.communicate()
    return output.decode('utf-8')
