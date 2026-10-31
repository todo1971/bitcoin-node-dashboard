# Languages

[Deutsch](../TRANSLATIONS.md) | [English documentation](../../README.en.md#documentation)

Since 1.18.0, German and English are available in the UI. The selector appears
below the dashboard and administration headers. The browser saves the selection
as `dashboard-language`; German is the default. Changing language reloads the
page and preserves the selected tab.

The UTF-8 files `static/locales/de.json` and `static/locales/en.json` use the
same German source strings as keys. English values translate complete text or
known parts of dynamic messages. The longest matching phrase wins; word
boundaries protect identifiers. Only local language files are loaded.

Labels, known status messages, help text and the glossary are translated.
Unknown server-side messages remain German. Original logs, input values, secrets
and technical identifiers are not translated. Date and number formats follow
the selected language. If the English catalog cannot be loaded, a notice appears
and the German UI remains usable.

Add new UI texts to both catalogs. `python tools/check_languages.py` lists
static strings without an individual catalog entry, including technical labels
intentionally left unchanged. Additional languages also require entries in the
selector and the URL allowlist in `app.py`.

The normal dashboard updater copies the full `static/` directory, including
catalogs. No additional runtime packages are required.

Check with `python -m unittest discover -s tests -v`. The optional browser test
`node tools/test_languages.cjs` requires Playwright as a development tool.
Set `QA_BROWSER=msedge` to use an existing Edge installation. It checks
language switching, persistence, live texts, word boundaries and unchanged logs
and form values.

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
