# 009 — булева операция молча теряет инструмент, если грань периодической поверхности шире периода

**Чей:** OCCT, `BOPTools_AlgoTools2D::AdjustPCurveOnSurf` (TKBO). Код тот же в 7.8.1 и в текущем master
(`src/ModelingAlgorithms/TKBO/BOPTools/BOPTools_AlgoTools2D.cxx`, проверено 14 сентября 2026).

**Статус:** исправлено — патч в одну строку (`patches/0001-...`), проверен отдельной программой, внутри
частной копии FreeCAD 1.1.1 и регрессионным набором булевых; есть установка с откатом. **Установлен у
владельца 15 сентября 2026**: `C:\Program Files\FreeCAD 1.1\bin\TKBO.dll` md5 `6e31e0e1…`, сток рядом в
`TKBO.dll.stock-5983229e.bak`, `-Action status` — FIXED (раздел 9). Второй дефект, найденный по дороге (грань
на 5.27 периода после Refine), патчем не лечится — раздел 6.

## 1. Симптом

Файл владельца: блок Body1 (63836.861405 мм³) и Body3 на импортированном из STEP переходнике с резьбой
(26376.580902 мм³). Fusion 360 режет ту же пару в 53675.014796 + 0.461340 мм³.

FreeCAD 1.1.1 (сток, OCCT 7.8.1), мировые формы:

```
Part.cut    63836.810044, solids [63836.345993, 0.46132]
Part.common 0.000000, 0 solids
Part.fuse   63836.809441
cut+common-base -0.0514 ; base+tool-common-fuse 26376.6329
PartDesign::Boolean Cut: Body1 63836.374266 + 0.461306, state Up-to-date, isValid True
```

Инструмент пропадает целиком, ошибок нет, `isValid()` чист. Параметры BOP ничего не меняют: fuzzy 0.001 и
0.02, NonDestructive, Glue shift, OBB, `ShapeUpgrade_ShapeDivideContinuity` C1/C2,
`ShapeUpgrade_ShapeDivideAngle` 180/90 (форма становится невалидной), `ShapeUpgrade_ShapeDivideClosed`.

## 2. Причина

26 граней инструмента; у 10 из них — полосы резьбы на цилиндрах, конус и периодический B-сплайн — UV-границы
(`BRepTools::UVBounds`) шире периода 2π: pcurve винтовых рёбер выходят за линию шва на 8.8e-6 … 6.3e-5 рад.

```
Face2 Cylinder 2.499e-05   Face3 Cylinder 2.554e-05   Face4 Cylinder 3.798e-05   Face7 Cylinder 4.628e-05
Face8 Cylinder 2.554e-05   Face9 Cylinder 8.814e-06   Face14 Cone 6.307e-05      Face18 BSplineSurface 5.892e-05
Face19 Cylinder 1.618e-05  Face24 Cylinder 3.768e-05
```

В общем слиянии (`BOPAlgo_Builder`) плоскость x = −25 блока режет полосу Face4 (домен u ∈ [−3.141606,
3.141617]) по двум линиям u = ±0.761. Одна секущая получила pcurve u = **5.52202** вместо −0.76116; у Face2
(домен [3.14158, 9.42479]) одна секущая получила u = **0.761161** вместо 7.04444. Петли в 2D рвутся,
площади кусков не сходятся (Face4 51.2545 → 70.6713 + 19.4180; Face7, 8, 9, 19 так же; конус 732.58 →
1231.69), классификация граней переворачивается, и строитель тел выбрасывает инструмент.

Место в коде:

```cpp
// b. compute du again using clarified value of u2
GeomInt::AdjustPeriodic(u2, UMin, UMax, aUPeriod, u2, du, 0.);   // u2 перезаписан уже сдвинутым
...
u = u2 + du;                                                     // сдвиг учтён второй раз
if ((UMax - UMin - 2*aDelta) > aUPeriod) {                       // только для грани шире периода
  if ((u > (UMin + aDelta + aUPeriod)) || (u < (UMax - aDelta - aUPeriod))) {
    aClassifier.Perform(aF, gp_Pnt2d(u, v), aDelta);             // точка вне грани -> OUT
    if (Status == TopAbs_OUT) du += ... ? -aUPeriod : aUPeriod;  // du обнуляется
```

Face4, секущая с u2 = 5.52202 (пересечение плоскости с цилиндром даёт u в [0, 2π)): `AdjustPeriodic` даёт
u2 = −0.76116 и du = −2π; проверка берёт u = u2 + du = −7.0444 < UMax − P, классификатор отвечает OUT, du
возвращается к 0, pcurve остаётся на 5.52202. Грань не шире периода — блок не выполняется, поэтому стоковый
цилиндр (домен ровно [0, 2π]) не страдает.

## 3. Исправление

`patches/0001-BOPTools-AdjustPCurveOnSurf-shift-counted-once.patch`: сдвинутое значение пишется в отдельную
переменную, `u2` остаётся исходным, проверка видит u = u2 + du — ровно сдвинутую точку.

Сборка: `build-scripts/build-occt-bo.ps1 -Target TKBO` (дерево `build/occt-bo`, исходники
`C:/dev/freecad-kernel-fixes/occt`, конфигурация дефекта 001). Первая сборка с зависимостями — дольше 590 с,
досборка TKBO — 63.5 с. TKBO.dll: md5 `6e31e0e103877eccec25efacd1c602a1`; сток FreeCAD 1.1.1 —
`5983229eb2b6b80ca25019007d2a6c01`.

## 4. Совместимость с FreeCAD 1.1.1

`dumpbin /exports` и `/imports` (MSVC 14.36.32532):

- экспорт: 966 имён у патченой и 966 у FreeCAD, различий 0;
- импорт из OCCT: 892 символа из 10 модулей (TKPrim 2, TKShHealing 8, TKTopAlgo 58, TKGeomAlgo 90, TKBRep
  167, TKGeomBase 84, TKG3d 253, TKG2d 75, TKMath 63, TKernel 92), неразрешённых в DLL самого FreeCAD — 0;
- список зависимых DLL совпадает со стоковым (те же 10 модулей OCCT + CRT).

## 5. Внутри FreeCAD

Копия `C:\dev\fc-gap2\bo` — жёсткие ссылки на `fc-gap2\patched` (30405 файлов), `bin\TKBO.dll` заменён
настоящим файлом. `fc-gap2\patched` повторяет установку владельца: там и в `C:\Program Files\FreeCAD 1.1`
одинаковый TKFillet.dll дефекта 001 (md5 `4e89e519…`), так что копия отличается от его FreeCAD **только
TKBO.dll**. Каждый прогон — FreeCADCmd с копиями user.cfg/system.cfg, копия файла владельца.

| | сток (`Program Files`) | патч (`fc-gap2\bo`) |
|---|---|---|
| `Part.cut` мировых форм | 63836.810044 [63836.345993, 0.46132], 0.54 с | **53676.049478 [53675.579598, 0.46132]**, 0.71 с |
| `Part.common` | 0.000000, 0 тел | 10160.743705, 1 тело |
| `Part.fuse` | 63836.809441 | 80051.704123 |
| cut+common−base / base+tool−common−fuse | −0.0514 / 26376.6329 | −0.0682 / 0.9945 |
| типы граней результата `Part.cut` | BSpline 1, Cylinder 8, Plane 18 | BSpline 19, Cone 2, Cylinder 27, Plane 17 |
| `combine.combine` HybridDesign | отказ KernelFailure за 2.29 с | проверка пары проходит, **Cut неверный** 63836.374266 + 0.461306 (раздел 6) |
| `PartDesign::Boolean` через биндер, Refine по настройке (RefineModel = 1) | 63836.374266 + 0.461306 | 63836.374266 + 0.461306 (раздел 6) |
| то же, биндер Refine = False, Boolean.Refine = False | — | **53675.589949 + 0.461306**, 0.48 с |
| то же, биндер Refine = False, Boolean.Refine = True | — | 53675.674824 + 0.461306, 0.66 с |

Разница с Fusion на патченом ядре: 53675.580 против 53675.015 (0.57 мм³, 1.1e-5 относительно) и 0.46132
против 0.46134; источник не выяснен (интегрирование объёма B-сплайновых граней не проверялось).

## 6. Что патч НЕ лечит: грань на 5.27 периода после Refine

С включённой настройкой RefineModel биндер уточняет инструмент (`UnifySameDomain`): полосы резьбы одного
цилиндра сливаются в одну грань шириной 5.271718 периода (21 грань вместо 26). На такой форме и патченое
ядро даёт common 0 и cut 63836.839507 [63836.375694, 0.46132]; `tool.removeSplitter()` на мировых формах
воспроизводит то же. Разница с разделом 2 в том, что грань шире периода не на 1e-5, а в пять раз: какую копию
периода выбирать, классификатор по середине кривой решить не может. Причина в коде не найдена — измерено.
Для воркбенча отсюда вывод: инструмент с такими гранями нельзя уточнять перед булевой операцией.

## 7. Синтетическое воспроизведение (без данных владельца)

`repro/cpp/periodic_pcurve.cpp`: цилиндр R15 × 10 из `BRepPrimAPI_MakeCylinder`, боковая грань точно
переведена в домен [−π, π] (рамка поверхности повёрнута на π, все pcurve сдвинуты на −π; тело валидно,
7068.583471 мм³), pcurve верхней окружности продлена за шов на 2e-5 рад с каждой стороны (допуск ребра 1e-3).
Ящик (−30, −30, −5)–(30, 8, 15): грань y = 8 пересекает бок в u = −2.5791 и −0.5625, пересечение выдаёт их
как 3.7041 и 5.7207 — обе нужно сдвигать. Точный common на чистом цилиндре 5815.084489 (аналитика та же).

```
сток TKBO:    cut 45600 (1)  common 0 (0)            fuse 46853.4991   |common-exact| 5815.084489  BROKEN
патч TKBO:    cut 39784.91549 (1)  common 5815.084504 (1)  fuse 46853.4991  |common-exact| 1.5e-05  FIXED
```

`fixtures/periodic_overshoot_cylinder.brep` (1256 байт) — этот инструмент, записанный программой.
`repro/python/verify_periodic_pcurve.py` — то же внутри FreeCAD: в `C:\Program Files\FreeCAD 1.1` (сток)
`PERIODIC-PCURVE: BROKEN` (cut 45600.000000, common 0.000000), в `fc-gap2\bo` — `FIXED` (common 5815.084504).

## 8. Регрессии

Одни и те же 22 булевы операции Part в стоковом FreeCAD и в `fc-gap2\bo` дали **совпадающие до шестого
знака** объёмы, числа тел и `isValid`: ящик с цилиндром (cut/common), пересекающиеся цилиндры (fuse/cut),
сфера (common/cut), `toNurbs`-цилиндр, конус, тор, цилиндр с доменом [π, 3π] в пяти положениях (cut/common),
винтовая пружина `makePipeShell` (cut/common). Набор тестов OCCT (DRAW) не прогонялся.

## 9. Установка

FreeCAD закрыт, PowerShell от администратора:

```
powershell -ExecutionPolicy Bypass -File C:\dev\freecad-kernel-fixes\issues\009-occt-bop-periodic-pcurve\build-scripts\install-into-freecad.ps1 -Action apply
```

Меняется один файл: `C:\Program Files\FreeCAD 1.1\bin\TKBO.dll` (сток `5983229e…` → патч `6e31e0e1…`),
рядом кладётся `TKBO.dll.stock-5983229e.bak`. Скрипт отказывается от неизвестных md5, от запущенного из этой
папки FreeCAD и от папки без права записи; после замены запускает проверку (раздел 7, дедлайн 120 с) и при
любом ответе, кроме FIXED, возвращает сток. `-Action revert` возвращает сток из резервной копии, `-Action
status` только проверяет.

Проверено на копии (`-FreeCADDir C:\dev\fc-gap2\bo`): status — сток, BROKEN; apply — FIXED; revert — BROKEN;
apply — FIXED; каждая проверка около 1 с. Копия оставлена патченой.

**Ошибка проверки (исправлена 15 сентября 2026).** На машине владельца `$env:TEMP` — короткий путь 8.3
(`C:\Users\B72A~1\...`: имя пользователя кириллическое, а FreeCAD кириллический путь не открывает, поэтому копии
настроек лежат по короткому пути). `Remove-Item` отвергает такой путь завершающей ошибкой «Объект по указанному пути
C:\Users\B72A~1 не существует», и `-ErrorAction SilentlyContinue` её не глушит: при `$ErrorActionPreference = "Stop"`
скрипт обрывался до вердикта. Теперь каталог копий удаляет `[IO.Directory]::Delete` в try/catch. Проверено без
повышения прав на установке владельца: `-Action status` печатает TKBO `6e31e0e1…` (patched), резервную копию
`5983229e…` и `PERIODIC-PCURVE: FIXED` (cut 39784.915488, common 5815.084504, |common-exact| 0.000015).

### Если TKBO.dll держат зависшие процессы FreeCAD

Загруженную DLL нельзя перезаписать, а `-Action apply` отказывается, пока FreeCAD запущен из этой папки. У владельца
15 сентября 2026 DLL держали зависшие процессы FreeCAD, которые не удавалось завершить. Windows разрешает
ПЕРЕИМЕНОВАТЬ загруженную DLL на том же томе — процессы сохраняют отображение старого файла. Сработала замена через
переименование, из PowerShell от администратора:

```
powershell -ExecutionPolicy Bypass -File C:\dev\freecad-kernel-fixes\issues\009-occt-bop-periodic-pcurve\build-scripts\install-009-rename.ps1
```

`build-scripts/install-009-rename.ps1` проверяет md5 обеих DLL, переименовывает стоковую в
`TKBO.dll.stock-5983229e.bak` (от существующей копии отказывается), копирует на её место проверенную сборку и
запускает `install-into-freecad.ps1 -Action status`; при любом ответе, кроме FIXED, и при сбое самой проверки
возвращает сток. Журнал — `build/install-009-rename.log`. У владельца первый запуск дошёл до проверки и оборвался:
ошибка 8.3 выше, а в Windows PowerShell 5.1 stderr дочерней команды, перенаправленный `2>&1` при
`$ErrorActionPreference = "Stop"`, выбрасывается как ошибка. Патченая DLL осталась на месте, журнал кончается
`EXIT 1` без вердикта; вердикт получен отдельным запуском исправленного `-Action status` — FIXED. В скрипте проверка
теперь идёт со своим `ErrorActionPreference`, её код выхода и вывод пишутся в журнал. Исправленный скрипт не
перезапускался: DLL уже патченая, и он отказывается заменять не стоковую.

## 10. Что не сделано

- Грань на 5.27 периода после Refine (раздел 6) — не исправлена, причина не найдена.
- Тесты OCCT (DRAW) не прогонялись; отчёт в OCCT не написан.
- Разница 0.57 мм³ с Fusion на патченом ядре не объяснена.
- Фазз (раздел 11.3) нашёл то, что патч не лечит: конус в домене [−π, π] под произвольно повёрнутым ящиком режется
  неверно на обоих ядрах уже ровно на периоде (0.08–0.12 %), а при расширении на патченом ядре — до 2.5 %; и две
  случайные пары, одинаково неверные на обоих ядрах. Не исследовано.

## 11. Регрессионное тестирование (Regression testing), 15 сентября 2026

Две установки FreeCAD 1.1.1, которые различаются ТОЛЬКО TKBO.dll (сравнены все 660 файлов `bin`): **патч** —
`C:\Program Files\FreeCAD 1.1`, установка владельца (TKBO `6e31e0e1…`); **сток** — `C:\dev\fc-gap2\patched` (TKBO
`5983229e…`). TKFillet в обеих один и тот же, `4e89e519…` дефекта 001. Каждый FreeCADCmd — с копиями user.cfg и
system.cfg (`-u`, `-s`), своим TEMP и дедлайном. Скрипты — `tests/`; геометрия генерируется в них самих, данных
владельца нет. Выходные файлы — `C:\dev\freecad-kernel-fixes\build\regression-009` (в репозиторий не входят).

```
powershell -ExecutionPolicy Bypass -File tests\run_regression.ps1 -FreeCADDir "C:\Program Files\FreeCAD 1.1" -Out <выход>\patched\<шаг> -Steps suites -Suites TestPartApp
powershell -ExecutionPolicy Bypass -File tests\run_regression.ps1 -FreeCADDir C:\dev\fc-gap2\patched -Out <выход>\stock\<шаг> -Steps suites -Suites TestPartApp
  (так же -Suites TestPartDesignApp, TestSketcherApp, TestOpenSCADApp, TestArch, TestDraft, TestTechDrawApp, TestCAMApp;
   -Steps fuzz; -Steps python,cpp)
"C:\Program Files\FreeCAD 1.1\bin\python.exe" tests\compare_suites.py <выход>\stock <выход>\patched
"C:\Program Files\FreeCAD 1.1\bin\python.exe" tests\compare_fuzz.py <выход>\stock\fuzz\fuzz.jsonl <выход>\patched\fuzz\fuzz.jsonl
```

### 11.1 Наборы тестов FreeCAD (`FreeCADCmd -t <набор>`)

| набор | сток | патч |
|---|---|---|
| TestPartApp | Ran 131, OK | Ran 131, OK |
| TestPartDesignApp | Ran 168, OK | Ran 168, OK |
| TestSketcherApp | Ran 32, OK (skipped=1) | Ran 32, OK (skipped=1) |
| TestOpenSCADApp | Ran 26, FAILED (errors=20) | Ran 26, FAILED (errors=20), те же 20 |
| TestArch (BIM) | Ran 88, OK | Ran 88, OK |
| TestDraft | Ran 69, OK | Ran 69, OK |
| TestTechDrawApp | Ran 7, OK | Ran 7, OK |
| TestCAMApp | Ran 731, FAILED (failures=1, skipped=6) | Ran 731, FAILED (failures=1, skipped=6), тот же тест |

`compare_suites.py` сравнивает строку «Ran N», итоговую строку и имена упавших тестов из заголовков `FAIL:`/`ERROR:`:
**SUITES-VERDICT: SAME (0 of 8 suite(s) differ)**. Все 20 ошибок TestOpenSCADApp — `OpenSCAD executable unavailable`
(программы OpenSCAD на машине нет); падение TestCAMApp — `test_linuxcnc_serialize`, формат числа (`D6.000` вместо
`D6.00`). Первый прогон TestCAMApp шёл при шести параллельных процессах: на стоке он встал на
`TestToolBitShapeSvgIcon.test_to_bytes` и был убит через 520 с, на патче прошёл за 88 с с тем же падением; повтор на
обоих ядрах одновременно — 731 тест за 123.0 и 123.2 с, результат в таблице. Наборы с булевыми операциями выбраны из
`Test*App.py` и `Test*.py` в `Mod`; TestFemApp, TestMaterialsApp, TestSurfaceApp, TestAddonManagerApp не запускались.

### 11.2 Воспроизведения дефекта

| | сток | патч |
|---|---|---|
| C++ `build\periodic-pcurve\periodic_pcurve.exe`, первым в PATH — `bin` установки | cut 45600, common 0 (0 тел), \|common−exact\| 5815.084489 — **BROKEN** | cut 39784.91549, common 5815.084504, \|common−exact\| 1.48e-05 — **FIXED** |
| Python `repro/python/verify_periodic_pcurve.py` (побайтная копия, md5 `0d6c434e…`) | cut 45600.000000, common 0.000000, \|box+tool−common−fuse\| 5815.084374 — **BROKEN** | cut 39784.915488, common 5815.084504, \|common−exact\| 0.000015 — **FIXED** |

### 11.3 Фазз булевых операций (`tests/boolean_fuzz.py`, seed 9009)

По 1752 записи на каждом ядре (93.4 с сток, 92.1 с патч):

- 600 — 150 случайных пар примитивов (ящик, цилиндр, конус, сфера, тор; случайные размеры, положения и повороты)
  × Cut, Common, Fuse, Section;
- 1152 — инструмент с периодической гранью, расширенной в BREP-тексте: цилиндр и конус, повёрнутые на полпериода
  (домен [−π, π], как у владельца), и B-сплайновый цилиндр (`toNurbs`), сдвинутый на период; ширина сверх периода
  0, 1e-6, 4.75e-6, 1e-5, 4.27e-5, 6.14e-5, 1e-4, 1e-3 рад; против 12 оснований (ящик или цилиндр, половина
  повёрнута только вокруг оси инструмента) × 4 операции. Эталон — та же операция с чистым примитивом в том же прогоне.

Совпали 1521 запись, различаются **231, и во всех 231 сток неверен**. Ни одной записи, верной на стоке и неверной на
патче: **FUZZ-VERDICT: PASS**. Различия только у повёрнутых на полпериода цилиндра (105) и конуса (126) и только в
Cut, Common и Fuse; случайные пары, B-сплайн и все сечения на двух ядрах совпадают.

| почему неверен сток | записей | патч верен | патч неверен |
|---|---|---|---|
| результат не проходит `isValid()` (объём часто совпадает с эталоном) | 126 | 120 | 6 |
| не то число тел (0 или 2 вместо 1) | 49 | 43 | 6 |
| Cut, Common и Fuse не сходятся (включение-исключение), сток дальше эталона на 10.3–181 % | 49 | 42 | 7 |
| все три сходятся, но дальше эталона на 68.4 % | 7 | 7 | 0 |

Там, где патч верен, он отличается от эталона не больше чем на 0.113 % (это изменение самого инструмента при
расширении, разрешено судьёй). Там, где патч неверен (19 записей), — это один случай: конус и ящик, повёрнутый
произвольно (основание 5). Сток отклоняется на 27.7–100 %, патч — на 0.08–2.5 %. Тот же конус с тем же ящиком
ровно на периоде (расширение 0) оба ядра режут одинаково неверно: cut 7356.557392 при эталоне 7365.447533, common
2050.759839 при 2049.129886, fuse 13494.006731 при 13506.818460; при 1e-6 патч даёт то же (cut 7356.556739), при
1e-5…1e-4 — до 2.5 %. Это второй, не исследованный дефект; патч убирает грубую ошибку, но не его.

Одинаково неверны на обоих ядрах 9 записей, к патчу не относятся: пара random-039 (Common пустой, Fuse 2965.096604
без инструмента, |Vb+Vt−common−fuse| 1697.42), пара random-127 (Fuse расходится на 121.721 мм³) и три записи конуса
ровно на периоде из абзаца выше. Итог по всем записям: сток — верно 1362, неверно 240 (validity 126, solids 49,
consistency 55, deviation 10), не судится 150 (сечения случайных пар); патч — верно 1574, неверно 28 (consistency 18,
deviation 10), не судится 150.

Судья (`compare_fuzz.py`, правила в его docstring) считает запись неверной, если результат невалиден при валидном
эталоне, если не совпало число тел, если Cut, Common и Fuse пары расходятся больше чем на 1e-3 от V(base) + V(tool),
или если результат дальше эталона больше чем на 1e-4 плюс 10 объёмов полосы, которую добавляет расширение; для
B-сплайна оба порога 1e-2. Пороги взяты из этого же прогона: случайные пары сходятся с медианой 5.2e-8, 98 % ниже
8.6e-5 (выше только random-039 и random-127: 0.36 и 0.038); B-сплайн на обоих ядрах расходится до 0.0074 (ровно на
периоде 0.0046) — OCCT грубо интегрирует объём B-сплайна; расширенный цилиндр на патче уходит от эталона до 7.54
полос. От порогов вердикт не зависит: каждая из 231 различающихся записей на стоке либо невалидна, либо с другим
числом тел, либо дальше эталона не меньше чем на 10 %.

### 11.4 HybridDesign на обоих ядрах

Воркбенч проверяет то, что верно на каждом ядре (HybridDesign 9935c6e, проба
`pcurve_repair.kernel_mishandles_wide_periodic_faces()`): патч — `HD-TESTS: ran=1225 failures=0 errors=0 skipped=0 ->
OK`, все 27 GUI-наборов offscreen `EXIT CODE: 0`; сток TKBO (`fc-gap2\patched`) — `ran=1225 failures=0 errors=0
skipped=1 -> OK`, imports_gui `EXIT CODE: 0`; сток TKBO и TKFillet (`fc-gap2\stock`) — `ran=1225 failures=0 errors=0
skipped=1 -> OK`, imports_gui `EXIT CODE: 0`.

## 12. Как повторить

```
powershell -ExecutionPolicy Bypass -File build-scripts\build-occt-bo.ps1 -Target TKBO
powershell -ExecutionPolicy Bypass -File build-scripts\build-repro.ps1
# сток / патч:
PATH=C:\dev\freecad-kernel-fixes\install\occt-fix\win64\vc14\bin;%PATH%  build\periodic-pcurve\periodic_pcurve.exe
PATH=C:\dev\freecad-kernel-fixes\build\occt-bo\win64\vc14\bin;C:\dev\freecad-kernel-fixes\install\occt-fix\win64\vc14\bin;%PATH%  build\periodic-pcurve\periodic_pcurve.exe
powershell -ExecutionPolicy Bypass -File build-scripts\install-into-freecad.ps1 -Action status -FreeCADDir C:\dev\fc-gap2\bo
```
