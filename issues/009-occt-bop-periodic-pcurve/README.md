# 009 — булева операция молча теряет инструмент, если грань периодической поверхности шире периода

**Чей:** OCCT, `BOPTools_AlgoTools2D::AdjustPCurveOnSurf` (TKBO). Код тот же в 7.8.1 и в текущем master
(`src/ModelingAlgorithms/TKBO/BOPTools/BOPTools_AlgoTools2D.cxx`, проверено 14 сентября 2026).

**Статус:** исправлено — патч в одну строку (`patches/0001-...`), проверен отдельной программой, внутри
частной копии FreeCAD 1.1.1 и регрессионным набором булевых; есть установка с откатом. **В установку
владельца не ставился** — нужно его согласие и закрытый FreeCAD. Второй дефект, найденный по дороге (грань
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

## 10. Что не сделано

- В установку владельца не ставилось.
- Грань на 5.27 периода после Refine (раздел 6) — не исправлена, причина не найдена.
- Тесты OCCT (DRAW) не прогонялись; отчёт в OCCT не написан.
- Разница 0.57 мм³ с Fusion на патченом ядре не объяснена.

## 11. Как повторить

```
powershell -ExecutionPolicy Bypass -File build-scripts\build-occt-bo.ps1 -Target TKBO
powershell -ExecutionPolicy Bypass -File build-scripts\build-repro.ps1
# сток / патч:
PATH=C:\dev\freecad-kernel-fixes\install\occt-fix\win64\vc14\bin;%PATH%  build\periodic-pcurve\periodic_pcurve.exe
PATH=C:\dev\freecad-kernel-fixes\build\occt-bo\win64\vc14\bin;C:\dev\freecad-kernel-fixes\install\occt-fix\win64\vc14\bin;%PATH%  build\periodic-pcurve\periodic_pcurve.exe
powershell -ExecutionPolicy Bypass -File build-scripts\install-into-freecad.ps1 -Action status -FreeCADDir C:\dev\fc-gap2\bo
```
