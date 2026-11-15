# Licence texts

The full text of the licences that apply to parts of the downloads and ask for their text to travel with them: the GNU
and Mozilla licences, and the one Python is under. `tools/make_notices.py` appends them to `THIRD-PARTY-LICENSES.txt`,
which every download carries ([docs/dependencies.md](../../docs/dependencies.md#licences-in-the-downloads)).

They are the texts of the [SPDX License List](https://github.com/spdx/license-list-data), copied unchanged from commit
`31846481de7ea17d92f2f46fad76abe58b2e9bb0` (the `-only` file for each GNU licence: the text is the same as the
`-or-later` one). Don't edit them: a test (`tests/test_make_notices.py`) checks that each one still starts as the real
licence does.

| File | Licence | SPDX file | SHA-256 |
|---|---|---|---|
| `GPL-2.0.txt` | GNU General Public License, version 2 | `text/GPL-2.0-only.txt` | `aaf135472f81c5b4a0dca9367e5bb5e9750032b5bebe5442b36e4c0a47430df3` |
| `GPL-3.0.txt` | GNU General Public License, version 3 | `text/GPL-3.0-only.txt` | `fb981668c18a279e285fc4d83fba1e836cc84dd4daa73c9697d3cfd2d8aca6e0` |
| `LGPL-2.1.txt` | GNU Lesser General Public License, version 2.1 | `text/LGPL-2.1-only.txt` | `5749785c8bdefafcb5d798270ed0a967036fe2ca63dcedade1627565dfef81d2` |
| `LGPL-3.0.txt` | GNU Lesser General Public License, version 3 | `text/LGPL-3.0-only.txt` | `996af0513df21f7496288951c41428a03c174e9e4a9d63665c57d670f845ccb1` |
| `MPL-2.0.txt` | Mozilla Public License, version 2.0 | `text/MPL-2.0.txt` | `66a3107d5ad6a058aab753eaac2047ccb2ed0e39465dd0fe5844da3e300d5172` |
| `Python-2.0.txt` | Python Software Foundation License, version 2 | `text/Python-2.0.txt` | `893c2bafbb8133f7aa97e1f79a3ee3241ebca7025f56278e9e1f72bb98592f9d` |

To check one, run `shasum -a 256 packaging/licenses/GPL-2.0.txt` and compare the result with the table.
