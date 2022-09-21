import os
import sublime
import sublime_plugin
import subprocess
import threading


class CloneLspProjectsCommand(sublime_plugin.WindowCommand):
    def run(self):
        t = threading.Thread(target=clone, args=(self.window,))
        t.start()

def clone(window: sublime.Window):
    packages_path = sublime.packages_path()
    variables = window.extract_variables()
    projects = sublime.load_settings("lsp_maintainers.sublime-settings").get('projects')

    for project in projects:
        already_exist = os.path.exists(os.path.join(packages_path, project['name']))
        if already_exist:
            print('Project {} already exist'.format(project['name']))
            continue
        cmd = project['setup_command'].split(" ")
        cmd = sublime.expand_variables(cmd, variables)
        print('Running setup command for {}:\n{}'.format(project['name'], cmd))
        window.status_message('Setting up {}.'.format(project['name']))
        run_command(cmd)

    sublime.message_dialog('LSP maintainer: Cloning is done.')


class OpenLspProjectsCommand(sublime_plugin.WindowCommand):
    def run(self):
        packages_path = sublime.packages_path()
        project_data = self.window.project_data() or {}
        folders = project_data.get('folders') or []
        projects = sublime.load_settings("lsp_maintainers.sublime-settings").get('projects')

        for project in projects:
            plugin_path = os.path.join(packages_path, project['name'])
            folders.append({"path": plugin_path})
        self.window.set_project_data({
            'folders': folders
        })

def run_command(cmd):
    p = subprocess.Popen(cmd,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output, _stderr = p.communicate()
    return output.decode('utf-8')