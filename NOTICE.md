# Data notices

The bundled New Testament text is the Russian Synodal Translation (1876,
electronic 1956 edition). It is generated from
[`seven1m/open-bibles`](https://github.com/seven1m/open-bibles), where the
Russian Synodal source is marked **Public Domain**.

The initial daily-reference pool is derived from the references-only dataset in
[`SuyangLiuPaul/YsWords`](https://github.com/SuyangLiuPaul/YsWords). The source
describes those entries as references only; the verse text is always read from
the bundled Synodal corpus. The plan is supplemented with short, manually
selected New Testament ranges, and Revelation 22:21 is reserved for the final
day of the cycle.

Run `python scripts/build_bible_data.py` to reproduce the generated JSON files.
