import json
import re
table = """
| Package name (maintainer) | Releases |
|---------------------------|----------|
"""
with open('../lsp_maintainers.sublime-settings') as user_file:
	file_contents = user_file.read()
	settings = json.loads(file_contents)

	for p in settings["packages"]:
		href = str(p["details"])
		name = p["name"]
		maintainer = re.sub(r"\/.+", "", href.replace("https://github.com/", ""))
		if maintainer != "sublimelsp":
			name += f" (<a href='{href}'>{maintainer}</a>)"
		releases = ", ".join([r["sublime_text"] for r in p["releases"]]) if "releases" in p else ""
		table+= f"| {name}     | {releases}   |\n"

print(table)
