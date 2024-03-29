# run `python ./generate-table.py`
import json
import re
table = """
| Package name (maintainer) | Releases(tags) |
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

		def format_release(release):
			text = release['sublime_text']
			if isinstance(release['tags'], str):
				text += f"({release['tags']})"
			return text

		releases = ", ".join([format_release(r) for r in p["releases"]]) if "releases" in p else ""
		table+= f"| {name}     | {releases}   |\n"

print(table)
