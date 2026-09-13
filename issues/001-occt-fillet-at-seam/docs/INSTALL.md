# Как поставить исправление шва в свой FreeCAD и как его убрать

Дата: 13 сентября 2026. Проверено полным циклом на копии установки
`C:\dev\fc-gap2\stock`; оригинал `C:\Program Files\FreeCAD 1.1` при проверке не трогался.

## Что меняется

Ровно один файл: `bin\TKFillet.dll`. Почему этого достаточно, доказано в `docs/IN_FREECAD.md`,
раздел 1: все 1065 импортов патченой библиотеки экспортируются модулями самого FreeCAD, все 586
символов, которые 12 потребителей в установке берут из `TKFillet`, есть у патченой, таблицы
экспорта совпадают целиком (1380 = 1380).

| | md5 |
|---|---|
| родной `TKFillet.dll` FreeCAD 1.1.1 (сборка 20260414) | `6d9915afa227e9bff7c0c2cc29806cd3` |
| патченый (`V7_8_1` + `patches/0002`, `build/bin-cond`) | `4e89e519f8a7ec7f7ed7f2b198d60275` |

## Три команды

Для настоящей установки PowerShell нужно запустить **от имени администратора** — запись в
`C:\Program Files` иначе запрещена, и скрипт сразу скажет об этом, ничего не тронув.
FreeCAD перед установкой лучше закрыть: открытый процесс держит библиотеку.

```powershell
cd C:\dev\freecad-kernel-fixes
powershell -ExecutionPolicy Bypass -File build-scripts\install-into-freecad.ps1 -Action status
powershell -ExecutionPolicy Bypass -File build-scripts\install-into-freecad.ps1 -Action apply
powershell -ExecutionPolicy Bypass -File build-scripts\install-into-freecad.ps1 -Action revert
```

По умолчанию цель — `C:\Program Files\FreeCAD 1.1`; другая установка задаётся
`-FreeCADDir "<путь>"`.

## Что скрипт делает сам

- **Проверяет, что меняет.** Заменяет только родной файл FreeCAD 1.1.1 и ставит только проверенную
  сборку — обе по md5. Неизвестную сборку с любой стороны отказывается трогать.
- **Делает резервную копию** рядом: `bin\TKFillet.dll.stock-6d9915af.bak`, и проверяет её md5.
- **Спрашивает само ядро**, а не верит файлу: запускает `build-scripts\verify-seam-fillet.py`
  через `FreeCADCmd` (дедлайн 120 с) — ту же минимальную пару, на которой дефект был доказан.
- **Сам откатывается**, если после установки ядро не ответило `FIXED`.

## Как это выглядело на копии (дословный вывод)

```
===== status
TKFillet:    6d9915afa227e9bff7c0c2cc29806cd3  (stock)
  control (seam far away): correct  valid=True bop=clean removed=1.368076 ideal=1.367173
  edge ending on the seam: WRONG  valid=False bop=DIRTY removed=-374.970181 ideal=1.367173
SEAM-FILLET: STOCK
===== apply
applied; checking the kernel:
  edge ending on the seam: correct  valid=True bop=clean removed=1.368075 ideal=1.367173
SEAM-FILLET: FIXED
===== revert
reverted; checking the kernel:
  edge ending on the seam: WRONG  valid=False bop=DIRTY removed=-374.970181 ideal=1.367173
SEAM-FILLET: STOCK
===== итоговый md5 копии:
6d9915afa227e9bff7c0c2cc29806cd3
```

## Проверить руками, без скрипта

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe" C:\dev\freecad-kernel-fixes\build-scripts\verify-seam-fillet.py
Get-Content C:\dev\freecad-kernel-fixes\build-scripts\verify-seam-fillet.txt
```

Последняя строка — `SEAM-FILLET: FIXED` или `SEAM-FILLET: STOCK`.

## Что изменится в HybridDesign

Пре-флайт команды Fillet спрашивает ядро той же пробой (один раз за сеанс, 12–18 мс). На
патченом ядре он молча пропускает обычное скругление; на стоковом — по-прежнему предупреждает про
шов и предлагает его отвести. Команда «Move Seam» остаётся доступной в обоих случаях.

## Чем рискуете

- **Проверено:** ваша деталь (Edge9) на восьми радиусах через `PartDesign::Fillet` и через
  `HD_Fillet`; собственные наборы OCCT на 2122 исполненных случаях без единого изменения статуса;
  701 headless-тест и 13 GUI-наборов верстака на патченой копии.
- **Не проверено:** 943 случая набора OCCT, данные для которых не публикуются; всё, что требует
  настоящего 3D-вида (наборы шли без OpenGL); другие верстаки FreeCAD, кроме того, что они
  используют скругления через ту же библиотеку.
- **Обновление FreeCAD** (например, до 1.1.3) заменит `TKFillet.dll` родным. Скрипт это увидит:
  `status` покажет другой md5, а `apply` откажется ставить сборку 7.8.1 поверх неизвестной версии.
  Для новой версии FreeCAD патч надо пересобрать против её OCCT.
