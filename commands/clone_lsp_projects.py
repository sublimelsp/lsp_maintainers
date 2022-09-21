import sublime_plugin
import sublime

class CloneLspProjectsCommand(sublime_plugin.WindowCommand):
    def run(self):
        print('ovde', sublime.packages_path())