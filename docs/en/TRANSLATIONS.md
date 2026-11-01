# Languages

[Deutsch](../TRANSLATIONS.md) | [English documentation](../../README.en.md#documentation)

Since 1.19.0, six UI languages are available; German and English were introduced
in 1.18.0. The selector appears
below the dashboard and administration headers. The browser saves the selection
as `dashboard-language`; German is the default. Changing language reloads the
page and preserves the selected tab.

| Language | Catalog | Number/date locale |
|---|---|---|
| Deutsch | `de.json` | `de-DE` |
| English | `en.json` | `en-GB` |
| Español | `es.json` | `es-ES` |
| Português (Brasil) | `pt-BR.json` | `pt-BR` |
| 简体中文 | `zh-Hans.json` | `zh-CN` |
| Русский | `ru.json` | `ru-RU` |

The UTF-8 files under `static/locales/` each contain the same complete set of
298 German source strings as keys. Translated values cover complete text or
known parts of dynamic messages. The longest matching phrase wins; word
boundaries protect identifiers. Only local language files are loaded.

Labels, known status messages, help text and the glossary are translated.
Unknown server-side messages remain German. Original logs, input values, secrets
and technical identifiers are not translated. Date and number formats follow
the selected language. If a catalog cannot be loaded, a notice in that language appears
and the German UI remains usable.

Add new UI texts to all six catalogs. `python tools/check_languages.py` lists
static strings without an individual catalog entry, including technical labels
intentionally left unchanged. Additional languages also require entries in the
selector and the URL allowlist in `app.py`.

The normal dashboard updater copies the full `static/` directory, including
catalogs. No additional runtime packages are required.

Check with `python -m unittest discover -s tests -v`. The optional browser test
`node tools/test_languages.cjs` requires Playwright as a development tool.
Set `QA_BROWSER=msedge` to use an existing Edge installation. It checks
all six languages: switching, persistence and retained tabs, live text, complete
update confirmations, word boundaries, desktop/mobile layouts and unchanged logs
and form values. Invalid stored languages and missing catalogs are also checked.
Set `QA_SCREENSHOT_DIR` for optional screenshots. Chinese and Cyrillic rendering
were also inspected visually. The observer marks its own text changes to avoid
translating a translation again.

Project documentation remains in German and English. The four additional
languages cover the UI, admin notices and glossary. Japanese and Traditional
Chinese are not included. Terminology improvements can be submitted as pull
requests against the corresponding catalog.

## Documentation languages

Since 1.18.1, [README.en.md](../../README.en.md),
[CHANGELOG.en.md](../../CHANGELOG.en.md) and this `docs/en/` directory contain
English editions alongside all German documentation. Each page links to its
counterpart. Both changelogs include every historical version.

When changing documentation, update both editions in the same change.
Keep commands, configuration keys, paths and historical version dates aligned.

Normal updates copy all English pages under `docs/en/`. To also install the
two English files in the project root, update the root helper once through
bootstrap from the verified 1.18.1 release. Both files are available directly
on GitHub regardless of the locally installed helper version.
