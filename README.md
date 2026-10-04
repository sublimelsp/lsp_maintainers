
This plugin helps setup a sublime project containing all LSP-plugins.

Why?

Should help when doing breaking changes to see what plugins are affected.

Commands:

`Preferences: LSP Maintainers Settings` - configure what LSP-* will be included in the project.

`LSP Maintainers: Clone Projects` - will clone the specified LSP-* plugins in the sublime package directory.

`LSP Maintainers: Open Projects` - will open the those LSP-* plugins in the current window.

## Type-check all packages

The `scripts/checkout-repos.py` script downloads the latest Sublime Text build for macOS and the latest release of each
package into the `repositories` directory. The type check uses the Python modules of that Sublime Text build. The script
deletes and clones each package again on every run.

```sh
python3 scripts/checkout-repos.py
```

After cloning, the script collects the libraries that the packages depend on. It reads the `dependencies.json` file of
each package in `repositories` and writes the libraries to `repositories/requirements-packages.txt`. It pins each
library to the version that Package Control provides for the Python version of the type check
(`tool.pyright.pythonVersion` in `repositories/pyproject.toml`). If PyPI does not have that version (for example
`lsp_utils`), the requirement points to the wheel of the Package Control release. It does not write libraries that are
checked out in `repositories` or that have stubs in `repositories/stubs`.

Options:

- `--exclude NAME` - do not clone the package `NAME`. You can use this option more than one time.
- `--preferred-branch BRANCH` - clone the branch `BRANCH` of each package. If a package does not have that branch, the
  script clones its latest release.
- `--local NAME=PATH` - do not clone the package `NAME` and instead export the current commit (`HEAD`) of the local git
  repository `PATH` in its place. Uncommitted changes are not exported. You can use this option more than one time.
  For example, to type-check all packages with the current branch of your LSP checkout:

  ```sh
  python3 scripts/checkout-repos.py --local LSP=../LSP
  ```

  `NAME` can also be a dependency of the [LSP repository](https://github.com/sublimelsp/repository) (for example
  `lsp_utils`). Then the type check uses the local export in place of the wheel from `requirements-packages.txt`. When
  you run the script again without `--local` for that dependency, the script removes the export.

- `--no-collect-dependencies` - do not collect the libraries. Use this option if you add or replace packages in
  `repositories` after the checkout. Then collect the libraries after that change:

  ```sh
  python3 scripts/collect-dependencies.py
  ```

Then type-check all packages:

```sh
cd repositories
uv sync
uv pip install -r requirements-packages.txt
uv run basedpyright
```


| Package name (maintainer) | Releases(tags) |
|---------------------------|----------|
| Chialisp ([cameroncooper](https://github.com/cameroncooper/sublime-chialisp))     | >=4000   |
| LSP     | 3154 - 4069(3154-), >=4070(4070-)   |
| LSP-anakin     |    |
| LSP-angular     | 3154 - 3999(st3-), >=4000   |
| LSP-astro     | >=4070   |
| LSP-aurelia ([LetsZiggy](https://github.com/LetsZiggy/LSP-aurelia))     |    |
| LSP-basedpyright     |    |
| LSP-bash     | 3154 - 3999(st3-), >=4000   |
| LSP-Bicep     | >=4070   |
| LSP-biome     | >=4070   |
| LSP-bitbake     |    |
| LSP-clangd     | >=4070   |
| LSP-cmake     |    |
| LSP-copilot     | >=4126   |
| LSP-cspell     | >=4126   |
| LSP-css     | 3154 - 4147(st3-), >=4148   |
| LSP-Dart     | >=4070   |
| LSP-Deno     | >=4070   |
| LSP-dockerfile     | 3154 - 3999(st3-), >=4000   |
| LSP-elixir     | 3154 - 3999(st3-), >=4000   |
| LSP-elm     | 3154 - 3999(st3-), >=4000   |
| LSP-eslint     | 3154 - 3999(st3-), >=4000   |
| LSP-esphome     | >=4148   |
| LSP-file-watcher-chokidar     | >=4070   |
| LSP-file-watcher-rust     | >=4148   |
| LSP-flow     | >=4070   |
| LSP-gnols ([jdkato](https://github.com/jdkato/LSP-gnols))     | >=4070   |
| LSP-gopls     | >=4070   |
| LSP-Grammarly     | >=4070   |
| LSP-graphql     | 3154 - 3999(st3-), >=4000   |
| LSP-html     | 3154 - 4147(st3-), >=4148   |
| LSP-intelephense     | 3154 - 3999(st3-), >=4000   |
| LSP-jdtls     | >=4070   |
| LSP-json     | 3154 - 4147(st3-), >=4148   |
| LSP-julia     | >=4095   |
| LSP-kotlin     | >=4070   |
| LSP-lean ([LexouDuck](https://github.com/LexouDuck/SublimeText-LSP-Lean))     | >=4070   |
| LSP-lemminx     | 3154 - 4069(st3-), >=4070   |
| LSP-leo     | >=4070   |
| LSP-ltex-ls     | >=4070   |
| LSP-ltex-ls-plus     | >=4070   |
| LSP-lua     | >=4070   |
| LSP-marksman     | >=4070   |
| LSP-metals ([scalameta](https://github.com/scalameta/metals-sublime))     | 3154 - 3999(st3-), >=4000   |
| LSP-nimlangserver     |    |
| LSP-OmniSharp     | >=4070   |
| LSP-PowerShellEditorServices     | >=4070   |
| LSP-prisma ([Sublime-Instincts](https://github.com/Sublime-Instincts/LSP-prisma))     | >=4126   |
| LSP-promql ([prometheus-community](https://github.com/prometheus-community/sublimelsp-promql))     | 3154 - 4069   |
| LSP-pylsp     | 3154 - 3999(st3-), >=4000   |
| LSP-pyproject     | >=4148   |
| LSP-pyright     | 3154 - 4147(st3-), >=4148   |
| LSP-pyvoice ([PythonVoiceCodingPlugin](https://github.com/PythonVoiceCodingPlugin/LSP-pyvoice))     | >=4070   |
| LSP-R     | >=4070   |
| LSP-ruff     | 3154 - 3999(st3-), >=4000   |
| LSP-rust-analyzer     | >=4070   |
| LSP-serenata     | 3154 - 3999   |
| LSP-some-sass     | >=4169   |
| LSP-SonarLint     |    |
| LSP-SourceKit     | >=4070   |
| LSP-stylelint     | 3154 - 3999(st3-), >=4000   |
| LSP-svelte     | 3154 - 3999(st3-), >=4000   |
| LSP-tailwindcss     | 3154 - 3999(st3-), >=4000   |
| LSP-taplo     | >=4070   |
| LSP-terraform     | >=4070   |
| LSP-TexLab     | >=4070   |
| LSP-Tinymist     |    |
| LSP-tsgo     | >=4148   |
| LSP-twiggy     | >=4169   |
| LSP-ty     | >=4132   |
| LSP-typescript     | 3154 - 3999(st3-), >=4000   |
| LSP-vale-ls ([errata-ai](https://github.com/errata-ai/LSP-vale-ls))     | >=4070   |
| LSP-vetur     | 3154 - 3999(st3-), >=4000   |
| LSP-VHDL-ls ([martinbarez](https://github.com/martinbarez/LSP-VHDL-ls))     | >=4070   |
| LSP-volar     | 3154 - 4147(st3-), >=4148   |
| LSP-vue     | 3154 - 3999(st3-), >=4000   |
| LSP-wren-lsp     | >=4070   |
| LSP-yaml     | 3154 - 4147(st3-), >=4148   |
| lsp_utils     | 3000 - 4069(st3-v), >=4070   |
| WolframLanguage ([WolframResearch](https://github.com/WolframResearch/Sublime-WolframLanguage))     | >=3103   |
