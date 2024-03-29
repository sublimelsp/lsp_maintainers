# getting started

Here are some puppeter scripts that will be run on 19 April.

> [!NOTE]
> I used Node v20.11.0

Run `npm install`.

Run `node ./merge-prs.js` it will:
- open the browser
- ask for credentials to login to github
- merge all PRs for LSP and LSP-pacakges.
- delete feat/py38 branches after the merge

