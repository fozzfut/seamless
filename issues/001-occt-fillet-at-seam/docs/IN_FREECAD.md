# Скругление Edge9 внутри FreeCAD владельца

Документ закрывает пробел, названный в `docs/DECISION.md` (шаг 2) и оставленный
открытым в `docs/REAL_PART.md`: всё доказательство патча до сих пор жило в чистом
OCCT — `BRepFilletAPI_MakeFillet` вызывался напрямую, минуя FreeCAD. Здесь тот же
случай проходит **через `PartDesign::Fillet` FreeCAD 1.1.1**, то есть ровно тем
путём, которым пользуется владелец, и дополнительно — через команду `HD_Fillet`
воркбенча HybridDesign.

Дата измерений: 12 сентября 2026 года.
Рядом с каждым числом стоит команда, которая его получила. Ни одно число не
перенесено из прошлых документов: всё измерено заново, на двух копиях установки
FreeCAD, отличающихся ровно одним файлом.

---

## 0. Ответ

**Да. В самом FreeCAD, через `PartDesign::Fillet`, Edge9 скругляется на всех
восьми измеренных радиусах — и через `HD_Fillet` воркбенча тоже.**

| | сток | патч | идеал |
|---|---|---|---|
| объём при r = 1.0 | 6053.9129 | **5455.2125** | 5455.2135 |
| изменение объёма | **+597.3323** (скругление ДОБАВИЛО материал) | **−1.3681** | −1.367147 |
| `isValid()` | false | **true** | — |
| `Shape.check(True)` | Self-intersecting wire x2, Unorientable shape x2 | **clean** | — |
| r = 0.5 | **НЕ ВЕРНУЛСЯ**, убит на 310.1 с (`exit=124`) | **0.046 с**, clean | — |
| r = 0.25 | снято 0.0222 вместо 0.0854 (в 3.85 раза меньше) при `isValid = true`, 262 ошибки BOP | **−0.0855**, clean | −0.085447 |

Все три отказа, которые владелец видел своими глазами, исчезли: рост объёма,
полоса зависания и тихая потеря материала.

Оригинальная установка `C:\Program Files\FreeCAD 1.1` не изменялась ни разу:
всё делалось на двух её копиях.

---

## 1. Почему подменён ровно один файл, и чем это доказано

FreeCAD 1.1.1 собран против **OCCT 7.8.1** — той же версии, из которой собраны
наши ядра:

```
$ "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" occver.py
FC ['1', '1', '1', '20260414 (Git shallow)', ...]
OCC_VER 7.8.1
```

Отсюда гипотеза: достаточно подменить `TKFillet.dll`. Она не принималась на веру,
а проверена `dumpbin` в обе стороны.

**(а) Список зависимостей совпадает точно.** У нашего `TKFillet.dll` и у
фрикадовского — один и тот же набор из 18 DLL (11 модулей OCCT плюс CRT):

```
$ dumpbin -dependents C:/dev/freecad-kernel-fixes/build/bin-cond/TKFillet.dll
$ dumpbin -dependents "C:/Program Files/FreeCAD 1.1/bin/TKFillet.dll"
    -> оба: TKBO TKBRep TKBool TKG2d TKG3d TKGeomAlgo TKGeomBase TKMath
            TKShHealing TKTopAlgo TKernel + KERNEL32 MSVCP140 VCRUNTIME140(_1)
            + api-ms-win-crt-{heap,math,runtime}
```

**(б) Всё, что наш `TKFillet.dll` импортирует, фрикадовские DLL экспортируют.**
1065 импортов из 11 модулей OCCT, ноль неразрешённых:

| модуль | импортов | экспортов у FreeCAD | не найдено |
|---|---|---|---|
| TKBO | 1 | 966 | 0 |
| TKBRep | 138 | 927 | 0 |
| TKBool | 88 | 2714 | 0 |
| TKG2d | 101 | 672 | 0 |
| TKG3d | 250 | 1617 | 0 |
| TKGeomAlgo | 146 | 3280 | 0 |
| TKGeomBase | 162 | 2798 | 0 |
| TKMath | 90 | 1885 | 0 |
| TKShHealing | 3 | 1209 | 0 |
| TKTopAlgo | 48 | 1873 | 0 |
| TKernel | 38 | 1709 | 0 |
| **итого** | **1065** | — | **0** |

**(в) Всё, что FreeCAD берёт из `TKFillet.dll`, наш файл экспортирует.**
Просканированы все 1708 бинарников установки; `TKFillet.dll` упоминают 13 —
он сам и 12 потребителей:

```
bin/gmsh.dll, bin/TKOffset.dll, lib/Part.pyd
bin/Lib/site-packages/OCC/Core/_{Blend,BlendFunc,BRepBlend,BRepFilletAPI,
    ChFi2d,ChFi3d,ChFiDS,ChFiKPart,FilletSurf}.pyd
```

Объединение символов, которые эти 12 потребителей импортируют из `TKFillet.dll`,
— **586**, и все 586 есть у нас. Более того, таблицы экспорта совпадают целиком:

```
exports: ours=1380 freecad=1380
in FreeCAD's TKFillet but NOT in ours: 0
in ours but NOT in FreeCAD's: 0
CONSUMER_IMPORTS_MISSING_FROM_OURS = 0
```

**Вывод: подмены `TKFillet.dll` достаточно, ничего другого совпадать не обязано.**
Это не предположение — это две пустые разности множеств.

---

## 2. Копии, md5 до и после, проверка запуска

Свободное место измерено до копирования: **27 ГБ** при установке **2.2 ГБ**
(`df -h /c`, `du -sh`). Порог остановки 5 ГБ не достигнут: после двух копий
осталось 22 ГБ.

```
$ robocopy "C:\Program Files\FreeCAD 1.1" "C:\dev\fc-gap2\patched" /E ...
$ robocopy "C:\Program Files\FreeCAD 1.1" "C:\dev\fc-gap2\stock"   /E ...
   Dirs : 2683 скопировано, Files : 30405 скопировано, FAILED : 0   (обе копии)
   ROBOCOPY_EXIT=1   <- у robocopy 1 означает «файлы скопированы»; ошибка это >= 8
```

Число файлов сверено с оригиналом: 30405 / 30405 / 30405.

**Запуск проверен ДО подмены** — обе копии живы:

```
$ C:/dev/fc-gap2/patched/bin/FreeCADCmd.exe --version
FreeCAD 1.1.1 Revision: 20260414 (Git shallow)     EXIT=0
$ C:/dev/fc-gap2/stock/bin/FreeCADCmd.exe --version
FreeCAD 1.1.1 Revision: 20260414 (Git shallow)     EXIT=0
```

**md5 единственного заменённого файла, до и после:**

| файл | md5 | что это |
|---|---|---|
| `patched/bin/TKFillet.dll` **до** | `6d9915afa227e9bff7c0c2cc29806cd3` | родной файл FreeCAD |
| `patched/bin/TKFillet.dll` **после** | `4e89e519f8a7ec7f7ed7f2b198d60275` | наш `build/bin-cond/TKFillet.dll` |
| `stock/bin/TKFillet.dll` (не трогали) | `6d9915afa227e9bff7c0c2cc29806cd3` | родной файл FreeCAD |
| `C:\Program Files\...\TKFillet.dll` | `6d9915afa227e9bff7c0c2cc29806cd3` | оригинал, не изменялся |

Резервная копия родного файла лежит в `C:\dev\fc-gap2\TKFillet.dll.freecad-orig.bak`
(md5 `6d9915af...`), так что подмена обратима одним `cp`.

**Запуск проверен ПОСЛЕ подмены:**

```
$ C:/dev/fc-gap2/patched/bin/FreeCADCmd.exe --version
FreeCAD 1.1.1 Revision: 20260414 (Git shallow)     EXIT=0
$ C:/dev/fc-gap2/patched/bin/FreeCADCmd.exe smoke2.py
OCC_VERSION 7.8.1
BOX_FILLET ok valid=True vol=997.853982                EXIT=0
```

997.853982 — это ровно `1000 − (1 − π/4)·1²·10`, то есть чужая DLL не просто
загрузилась, а считает правильно.

**Соседние подсистемы не поехали.** `TKOffset.dll` линкуется с `TKFillet.dll` и
НЕ заменялся; проверено, что он и фаски работают одинаково на обоих ядрах:

```
makeThickness:   valid=True vol=424.000000 solids=1
makeOffsetShape: valid=True vol=1698.436570
makeFillet r=2 на всех рёбрах куба: valid=True vol=907.704993 faces=26
makeChamfer d=1 на всех рёбрах куба: valid=True vol=945.333333 faces=26
$ diff out/tkoffset-patched.txt out/tkoffset-stock.txt  -> IDENTICAL
```

---

## 3. `PartDesign::Fillet` на Edge9: патч против стока, внутри FreeCAD

Драйвер — уже существовавший `repro/python/07_user_part_fillet.py`, ничего в нём
не менялось. Он копирует `.FCStd` и открывает **копию**; оригинал детали не
открывается никогда. Edge9 берётся на вершине тела (`Body.Tip = Fillet001`) —
это та самая фикстура, что записана в `docs/MEASUREMENTS.md` §5.2:

```
  seam Edge3 on Face1 (Cylinder) (24.9999, 19.3478, 10.0000) -> (18.6360, 19.3478, 3.6360)
  Edge9: Part::GeomLine length = 6.370619  (24.9999, 19.3478, 10.0000) -> (24.9999, 25.7184, 10.0000)
  distance(Edge9, nearest seam) = 0.000000000 mm
```

База: `faces=11 edges=28 volume=5456.580614 isValid=True`, одинаково на обоих
ядрах. **Каждый радиус — свой процесс со своим дедлайном 310 с**, иначе полосу
зависания не измерить:

```
SEAMLESS_RADIUS=<r> SEAMLESS_EDGE=Edge9 \
  timeout -k 5 310 C:/dev/fc-gap2/<patched|stock>/bin/FreeCADCmd.exe \
  repro/python/07_user_part_fillet.py
```

| r, мм | идеал ΔV | **сток** ΔV | isValid | `check(True)` стока | exit/время | **патч** ΔV | isValid | `check(True)` | exit/время |
|---|---|---|---|---|---|---|---|---|---|
| 0.10 | −0.013671 | −5598.8787 | false | Self-intersecting wire x2, Unorientable shape x2 | 0 / 1.2 с | **−0.0137** | true | **clean** | 0 / 1.4 с |
| 0.25 | −0.085447 | −0.0222 | **true** | SelfIntersect: Vertex x244, Edge x3, Face x1; TooSmallEdge x14 | 0 / 1.2 с | **−0.0855** | true | **clean** | 0 / 1.2 с |
| 0.45 | −0.276847 | −856.8413 | false | Self-intersecting wire x2, Unorientable shape x2 | 0 / 1.2 с | **−0.2769** | true | **clean** | 0 / 1.4 с |
| 0.50 | −0.341787 | **НЕ ВЕРНУЛСЯ** | — | — | **124 / 310.1 с** | **−0.3419** | true | **clean** | 0 / 1.4 с |
| 0.55 | −0.413562 | **НЕ ВЕРНУЛСЯ** | — | — | **124 / 310.1 с** | **−0.4137** | true | **clean** | 0 / 1.2 с |
| 0.60 | −0.492173 | +642.9480 | false | Self-intersecting wire x2, Unorientable shape x2 | 0 / 1.2 с | **−0.4923** | true | **clean** | 0 / 1.3 с |
| 0.75 | −0.769020 | +619.1511 | false | Self-intersecting wire x2, Unorientable shape x2 | 0 / 1.1 с | **−0.7693** | true | **clean** | 0 / 1.3 с |
| 1.00 | −1.367147 | +597.3323 | false | Self-intersecting wire x2, Unorientable shape x2 | 0 / 1.3 с | **−1.3681** | true | **clean** | 0 / 1.3 с |

В колонке `check(True)` стока приведены только содержательные записи; полная
строка, которую печатает OCCT, для всех «Self-intersecting wire» случаев такова:
`No error x2, Self-intersecting wire x2, Unorientable shape x2` — «No error»
проверяльщик выводит сам, это не наша редактура.

Столбец «сток» **совпал со снятым ранее** `docs/MEASUREMENTS.md` §5.3 во всех
восьми строках — то есть контроль воспроизводится, и сравнение честное: обе
колонки сняты в одном и том же FreeCAD, одним и тем же скриптом, в один заход.

Топология результата на стоке при r ≥ 0.60 отличается: `faces=12 edges=30`
против `faces=12 edges=32` на патче на всех восьми радиусах.

`recompute()` на патче: 0.035–0.046 с. На стоке там, где он вообще возвращается:
0.023–0.063 с. То есть **патч не «медленнее и правильнее», он в том же классе
скорости** — а на 0.5 и 0.55 разница между 0.04 с и «никогда».

Сходимость к аналитике на патче — 0.001 мм3 и лучше на всех радиусах; остаток
объясняется тем, что скругление слегка выходит за концы ребра по касательной.
Независимая перекрёстная проверка: чистый OCCT дал при r = 1.0 объём
5455.212690 (`docs/REAL_PART.md`), FreeCAD даёт 5455.212548 — **расхождение
1.4·10⁻⁴ мм3** между двумя совершенно разными путями к одному ядру.

---

## 4. Полоса зависания: как выглядит изнутри FreeCAD

На стоке `doc.recompute()` не возвращается. Последняя строка обоих убитых
прогонов:

```
D. PartDesign::Fillet r = 0.5000 on Edge9
  about to recompute -- if nothing follows this line, the kernel never returned
```

Процесс жив и **считает**: замер на середине прогона показал 307.9 с
процессорного времени у `C:\dev\fc-gap2\stock\bin\FreeCADCmd.exe` — это не
дедлок, а бесплодный счёт. Убит внешним дедлайном, `exit=124`, wall 310.1 с.
На патче тот же радиус — 0.046 с.

Практический вывод остаётся прежним и теперь подтверждён в FreeCAD: **внутри
процесса прервать это нечем.** Дедлайн обязан быть снаружи.

---

## 5. Путь воркбенча: `HD_Fillet`

`HD_Fillet` — честный алиас стоковой команды `PartDesign_Fillet` с
предполётной проверкой (`commands.py:1321`):

```python
reg(Alias("HD_Fillet", "PartDesign_Fillet", "Fillet", accel="F", before=seam_before_fillet))
```

Проверено на патченой копии; воркбенч подхватывается сам, из
`%APPDATA%\FreeCAD\v1-1\Mod\HybridDesign` (симлинк на репозиторий владельца;
md5 `seam.py` с обеих сторон совпал, это один и тот же файл).

### 5.1. Что говорит предполётная проверка

```
=== PRE-FLIGHT plan_for_edge(Body, 'Edge9', 1.000)  [0.013 s] ===
  needed   = True
  possible = True
  face     = Face1
  d        = 0.000000000 mm
  d/r      = 0.000000
  blocked  = True   (d <= 1.00*r)
  tight    = True   (d <  1.25*r)
  seam     = Seam(Edge3 on Face1, Cylinder)
  turn     = +86.947 deg
```

Владелец увидел бы диалог «Fillet» с этим текстом и тремя кнопками
(`Move the seam, then fillet` / `Fillet anyway` / `Cancel`):

> The seam of Face1 ends 0.000000 mm from the end of Edge9. A 1.000 mm fillet
> needs more than 1.000 mm there: at d <= r OCCT removes about 2.15x the right
> material and still reports success. Turning the profile circle by +86.947 deg
> moves the seam and no material.

### 5.2. Ветка «Fillet anyway» — то есть просто стоковое скругление

Шов НЕ двигается, дальше работает обычный `PartDesign::Fillet`:

| r | ядро | recompute | State | isValid | ΔV | идеал | `check(True)` | exit/время |
|---|---|---|---|---|---|---|---|---|
| 1.00 | **патч** | 0.044 с | `['Up-to-date']` | **true** | **−1.368067** | −1.367147 | **clean** | 0 / 0.9 с |
| 1.00 | сток | 0.045 с | `['Up-to-date']` | false | **+597.332322** | −1.367147 | Self-intersecting wire x2, Unorientable shape x2 | 0 / 1.1 с |
| 0.50 | **патч** | 0.038 с | `['Up-to-date']` | **true** | **−0.341862** | −0.341787 | **clean** | 0 / 0.8 с |
| 0.50 | сток | **НЕ ВЕРНУЛСЯ** | — | — | — | — | — | **124 / 310.2 с** |
| 0.25 | **патч** | 0.034 с | `['Up-to-date']` | **true** | **−0.085470** | −0.085447 | **clean** | 0 / 0.8 с |
| 0.25 | сток | 0.045 с | `['Up-to-date']` | **true** | −0.022220 | −0.085447 | 248 × SelfIntersect + 14 × TooSmallEdge = **262 ошибки** | 0 / 1.0 с |

Строка «сток, r = 0.25» — тот самый тихий отказ: `State = ['Up-to-date']`,
`isValid = true`, тело на вид целое, а снято в **3.85 раза** меньше нужного.

### 5.3. Ветка «Move the seam, then fillet» — тоже работает

На патченом ядре она отрабатывает штатно:

```
move_seam ok=True  [0.438 s]
  Seam of Face1 turned +86.947 deg (AngleXU -0.000 -> 86.947 deg on Sketch001);
  clearance 0.000000 -> 10.901995 mm; 10.90 x the 1.000 mm radius;
  1 reference(s) re-bound: Fillet001 Edge24->Edge25;
  material unchanged (mutual cut 0.000e+00 / 0.000e+00 mm3).
  Edge9 re-bound to Edge10 (0.000e+00 mm)
fillet after the move: recompute 0.032 s State=['Up-to-date']
  isValid=True volume=5455.212602 delta=-1.368064  check(True) = clean
```

**Оба ответа дают один и тот же результат:** −1.368064 после переноса шва против
−1.368067 без переноса — разница 3·10⁻⁶ мм3.

---

## 6. Находка для владельца воркбенча

Это не баг воркбенча и не то, что здесь надо чинить, — это то, что владельцу
HybridDesign придётся решить, если патченое ядро станет нормой.

**Предполётная проверка чисто геометрическая: она никогда не спрашивает ядро.**
`edge_meets_seam()` считает расстояние от конца шва до конца ребра и сравнивает
его с радиусом. Геометрия детали от патча не меняется, поэтому проверка выдаёт
**побайтово тот же вердикт на обоих ядрах**: `d = 0.000000000`, `blocked = True`,
`turn = +86.947 deg` — снято и на патче, и на стоке.

Значит, на патченом ядре пользователь получает диалог, чьё центральное
утверждение больше не соответствует действительности:

> «A 1.000 mm fillet needs more than 1.000 mm there»

— измерено, что не нужно: при `d = 0.0` и r = 1.0 скругление даёт −1.368067 мм3
против идеальных −1.367147 и проходит `check(True)` начисто.

Цена ненужного совета не нулевая. Если пользователь согласится на
«Move the seam, then fillet», воркбенч:

* повернёт окружность профиля в **его собственном эскизе** `Sketch001` на +86.947°;
* перепривяжет ссылку чужой фичи: `Fillet001` `Edge24` → `Edge25`;
* переименует выбранное ребро `Edge9` → `Edge10`;
* потратит 0.438 с

— чтобы получить −1.368064 вместо −1.368067, то есть ничего.

Что с этим делать — решать владельцу воркбенча. Возможные направления (ни одно
здесь не реализовано и не проверено): определять версию ядра и молчать на
патченом; понизить порог `CRITICAL`; сделать проверку не «до», а «после» —
запускать скругление и смотреть на `check(True)`, предлагая перенос шва только
когда результат действительно грязный.

Отдельно стоит заметить: константа `STOCK_FILLET_RADIUS = 1.0` (`commands.py:1088`)
— это предположение о радиусе, которого воркбенч на момент предполёта ещё не
знает, потому что диалог радиуса открывается позже. На стоке это было безопасно
в сторону перестраховки; на патче оно просто добавляет ложных срабатываний.

---

## 7. Тесты воркбенча: буквальные коды возврата

Все прогоны — против **патченой** копии. Репозиторий HybridDesign только
читался; ни одной команды `git` в нём не выполнялось.

### 7.1. Headless (`tests/run_tests.py`), патч и сток

```
$ timeout -k 5 1800 C:/dev/fc-gap2/patched/bin/FreeCADCmd.exe .../tests/run_tests.py
HD-TESTS: ran=701 failures=0 errors=0 skipped=0 -> OK
HEADLESS_PATCHED_EXIT=0   wall=70.5s   (Ran 701 tests in 69.248s)

$ timeout -k 5 1800 C:/dev/fc-gap2/stock/bin/FreeCADCmd.exe .../tests/run_tests.py
HD-TESTS: ran=701 failures=0 errors=0 skipped=0 -> OK
HEADLESS_STOCK_EXIT=0     wall=68.6s   (Ran 701 tests in 67.890s)
```

Результат одинаковый — патч ничего в собственном наборе воркбенча не сдвинул.

### 7.2. GUI-наборы, патченая копия

Запускались штатным раннером воркбенча, которому просто указан другой FreeCAD:

```
powershell -File tests/gui/run_smoke.ps1 -Module <m> \
  -FreeCAD "C:\dev\fc-gap2\patched\bin\FreeCAD.exe" -Offscreen
```

Раннер сам определил, что установленная копия разрешается в этот же репозиторий,
и поэтому **не** передавал `-M` (иначе `InitGui.py` выполнился бы дважды и все
наборы упали бы с кодом 2 — это описано в самом раннере).

| набор | exit | тестов | итог | время |
|---|---|---|---|---|
| smoke_gui | **0** | 27 | OK | 15.9 с |
| seam_gui | **0** | 11 | OK | 13.7 с |
| ribbon_gui | **0** | 24 | OK | 56.2 с |
| interaction_gui | **0** | 19 | OK | 32.0 с |
| acceptance_gui | **0** | 14 | OK | 14.8 с |
| move_gui | **0** | 13 | OK | 12.7 с |
| nesting_gui | **0** | 6 | OK | 12.7 с |
| reparent_gui | **0** | 32 | OK | 24.1 с |
| panel_targets_gui | **0** | 22 | OK | 12.7 с |
| plane_angle_gui | **0** | 3 | OK | 12.6 с |
| press_pull_gui | **0** | 4 | OK | 11.6 с |
| subassembly_gui | **0** | 24 | OK | 19.0 с |
| linear_stage_gui | **0** | 6 | OK | 16.9 с |
| **итого** | **все 0** | **205** | **все OK** | ~4.3 мин |

Итог по всем прогонам этого документа: 701 headless-теста на патче, 701 на стоке,
205 GUI-тестов на патче — **ни одного падения, все коды возврата 0**.

---

## 8. Что НЕ измерено и в чём оговорки

1. **GUI-наборы гонялись в `-Offscreen`.** У этой платформы нет OpenGL, значит
   3D-вид не создаётся. То, что по-настоящему требует 3D-вида, этими прогонами
   не покрыто — так написано в самом раннере воркбенча, и это ограничение не наше.
2. **GUI-наборы на стоке не гонялись.** Сравнивать было не с чем по времени;
   headless-набор, прогнанный на обоих ядрах, дал одинаковый результат, и это
   единственное сравнение GUI-стороны, которое здесь есть.
3. **Границы полосы зависания не уточнялись.** Измерено, что 0.45 возвращается,
   0.5 и 0.55 — нет, 0.60 возвращается. Каждая точка внутри полосы стоит 310 с.
4. **Проверен один пользовательский случай — Edge9 на этой детали.** Более
   широкое покрытие живёт в прогонах собственных наборов OCCT
   (`docs/REGRESSION.md`), не здесь.
5. **Подменялась только `TKFillet.dll`.** Доказано, что этого достаточно по
   символам (§1), и что соседние подсистемы считают одинаково (§2), но полного
   прогона всех модулей FreeCAD против патченой копии не делалось — кроме 906
   тестов воркбенча.
6. **Побочный эффект в репозитории воркбенча.** Прогон `acceptance_gui` перезаписал
   один файл кэша байт-кода —
   `tests/gui/__pycache__/acceptance_gui.cpython-311.pyc` (он существовал и раньше,
   Python пересобрал его как устаревший). Ни один исходный файл не изменён,
   `git` в том репозитории не запускался. Остальные 12 наборов не тронули ничего.

---

## 9. Как повторить

```bash
# 1. копии (проверить место: нужно ~4.4 ГБ на две)
robocopy "C:\Program Files\FreeCAD 1.1" "C:\dev\fc-gap2\patched" /E /MT:8
robocopy "C:\Program Files\FreeCAD 1.1" "C:\dev\fc-gap2\stock"   /E /MT:8
C:/dev/fc-gap2/patched/bin/FreeCADCmd.exe --version    # ДО подмены, ждём 0

# 2. подмена одного файла
cp C:/dev/fc-gap2/patched/bin/TKFillet.dll C:/dev/fc-gap2/TKFillet.dll.freecad-orig.bak
cp C:/dev/freecad-kernel-fixes/build/bin-cond/TKFillet.dll C:/dev/fc-gap2/patched/bin/TKFillet.dll
md5sum C:/dev/fc-gap2/patched/bin/TKFillet.dll   # 4e89e519f8a7ec7f7ed7f2b198d60275
C:/dev/fc-gap2/patched/bin/FreeCADCmd.exe --version    # ПОСЛЕ подмены, ждём 0

# 3. развёртка по радиусам, отдельный процесс и дедлайн на каждый
for R in 1.0 0.5 0.25 0.10 0.45 0.55 0.60 0.75; do
  SEAMLESS_RADIUS=$R SEAMLESS_EDGE=Edge9 SEAMLESS_PART=<копия .FCStd> \
  timeout -k 5 310 C:/dev/fc-gap2/patched/bin/FreeCADCmd.exe \
    repro/python/07_user_part_fillet.py
done

# 4. наборы воркбенча
C:/dev/fc-gap2/patched/bin/FreeCADCmd.exe <HybridDesign>/tests/run_tests.py
powershell -File <HybridDesign>/tests/gui/run_smoke.ps1 -Module smoke_gui \
  -FreeCAD "C:\dev\fc-gap2\patched\bin\FreeCAD.exe" -Offscreen
```

Откат — один `cp` из `.bak`. Оригинальная установка не участвует.
