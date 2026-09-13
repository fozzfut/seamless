# freecad-kernel-fixes

Defects found in the geometry kernel under FreeCAD — Open CASCADE Technology and FreeCAD's own
Part/PartDesign layer — each measured, reproduced from a script, and fixed where a fix is proven.
Documents are in Russian; code, patches and scripts are in English.

Дефекты геометрического ядра под FreeCAD — в самом Open CASCADE Technology и в слое Part/PartDesign
FreeCAD. Каждый измерен, воспроизводится скриптом и исправлен там, где исправление доказано.

## Каталог

| № | Дефект | Чей | Статус |
|---|---|---|---|
| [001](issues/001-occt-fillet-at-seam) | Скругление ребра, упирающегося в шов цилиндра, даёт мусор или зависает | OCCT, `ChFi3d` | **исправлено** — патч в одну строку, проверен в OCCT и внутри FreeCAD, есть установка и черновик отчёта в OCCT |
| [002](issues/002-freecad-makethread-turns) | `Part.makeThread` выдаёт 0.2690 витка из 32, объём отрицательный с 8 витков | FreeCAD, Part | измерено |
| [003](issues/003-partdesign-additivehelix) | `AdditiveHelix`: невалидный инструмент при `2h == pitch`, потеря сердцевины выше 1.20 при `Up-to-date` | FreeCAD, PartDesign | измерено |
| [004](issues/004-makehelix-length) | `makeHelix`: `Shape.Length` врёт начиная примерно с 50 витков | не определено | измерено |
| [005](issues/005-thread-fuse) | Приваривание 32-витковой резьбы: 41 с, объём отрицательный | не определено, вероятно OCCT | измерено один раз |
| [006](issues/006-partdesign-false-invalid-message) | «Base feature's TopoShape is invalid» при чистой базе | FreeCAD, PartDesign | измерено |
| [007](issues/007-partdesign-boolean-placed-target) | `Boolean` не учитывает размещение цели: Cut не режет, Fuse даёт два солида, всё `Up-to-date` | FreeCAD, PartDesign | измерено |

Статусы строгие: «исправлено» — только с доказанным патчем и прогоном регрессий; «измерено» —
симптом воспроизводится скриптом, причина в коде не найдена; «не определено» — неизвестно даже,
в каком слое дефект.

## Структура

```
issues/NNN-<слой>-<суть>/
  README.md        симптом, замеры, чей дефект, статус, что не сделано
  repro/           скрипты воспроизведения (каждый печатает свои замеры и завершается)
  docs/ patches/   разбор и исправление — когда до них дошло
common/
  python/seamlib.py  общие функции скриптов
  README.md          что общее: проверка check(True), где лежит сборка OCCT
```

## Окружение, на котором всё измерено

FreeCAD 1.1.1 (сборка 20260414), OCCT 7.8.1, Qt 6.8.3, Python 3.11, Windows. Скрипты Python
запускаются через `"<FreeCAD>/bin/FreeCADCmd.exe" <скрипт>`; у каждого, где возможно зависание
ядра, свой дедлайн — для дефекта 001 это не теория, стоковое ядро не возвращается по 300 с.

## Как добавить дефект

1. Скрипт в `issues/NNN-.../repro/`, который воспроизводит симптом с нуля и печатает числа.
2. `README.md` дефекта: симптом с выводом скрипта, чей он и почему так решено, статус, что не сделано.
3. Строка в каталоге выше. Статус «исправлено» — только после патча и прогона регрессий.

## Лицензия

GNU LGPL 2.1 (`LICENSE`) с исключением Open CASCADE (`OCCT_LGPL_EXCEPTION.txt`) — те же условия,
что у OCCT. Патчи являются изменениями OCCT и FreeCAD, поэтому других условий для них быть не может;
эти же условия позволяют предложить исправления в апстрим.
