# Сборка OCCT 7.8.1 как ядра для собственного CAD-приложения

Документ описывает **шаг конфигурации** дерева сборки OCCT: что включено, что
выключено и почему, какими точными командами это воспроизводится.

Всё измерено на этой машине. Каждое утверждение сопровождается командой, которая
его подтверждает.

---

## 1. Что за исходники

```
git -C C:/dev/freecad-kernel-fixes/occt log -1 --format='%H%n%d%n%ci%n%s'
```

```
bd2a789f15235755ce4d1a3b07379a2e062fdc2e
 (grafted, HEAD, tag: V7_8_1)
2024-03-31 23:05:22 +0100
Update version to 7.8.1
```

```
grep OCC_VERSION_COMPLETE C:/dev/freecad-kernel-fixes/occt/src/Standard/Standard_Version.hxx
#define OCC_VERSION_COMPLETE     "7.8.1"
```

**Это релизный тег V7_8_1, а не ветка разработки.** Клон поверхностный
(`grafted`, без полной истории), HEAD отсоединён на теге.

Это важно: ровно та же версия ядра, что внутри FreeCAD 1.1.1. Значит дефект
скругления у шва воспроизводится на этом самом коде, а не на «похожем».

Размер исходников — 333 МБ (`du -sm C:/dev/freecad-kernel-fixes/occt`; два замера подряд дали
одно и то же число — клонирование завершено). Рабочее дерево чистое:
`git -C C:/dev/freecad-kernel-fixes/occt status --porcelain` пусто.

---

## 2. Выбор модулей

Цель — **ядро, на котором можно писать приложение**: заголовки, import-библиотеки,
DLL. Не вьювер, не Draw, не тесты.

### Включено

| Модуль | Зачем |
|---|---|
| `FoundationClasses` | `TKernel`, `TKMath` — базис, без него не собирается ничего |
| `ModelingData` | `TKG2d TKG3d TKGeomBase TKBRep` — топология, поверхности, **pcurves и шов цилиндра** |
| `ModelingAlgorithms` | `TKFillet` (**здесь живёт скругление**), `TKBO`/`TKBool` (булевы и BOP-проверка), `TKPrim`, `TKShHealing`, `TKMesh` |

Транзитивное замыкание по `src/<TK>/EXTERNLIB` даёт **18 тулкитов**:

```
TKBO TKBRep TKBool TKFeat TKFillet TKG2d TKG3d TKGeomAlgo TKGeomBase
TKHLR TKMath TKMesh TKOffset TKPrim TKShHealing TKTopAlgo TKXMesh TKernel
```

Объём компиляции — **2161 файл** `.cxx`/`.c`.

### Выключено и что при этом теряется

| Модуль | Почему выключен | Что теряется |
|---|---|---|
| `Visualization` | Требует **FreeType**, которого на машине нет в пригодном для линковки виде | Нет `AIS_*`, `V3d_*`, `TKOpenGl` — рисовать на экране нечем. Для счётной части (скругление, объём, BOP) не нужен вообще |
| `ApplicationFramework` | OCAF-стек, расчётному ядру не нужен | Нет документа, undo/redo, атрибутов OCAF. Если захочется хранить дерево построения «как в FreeCAD» — модуль придётся включить |
| `DataExchange` | Тянет за собой FreeType, см. разбор ниже | **Нет импорта/экспорта STEP, IGES, STL, glTF.** Самая заметная потеря |
| `Draw` | Требует Tcl/Tk | Нет `DRAWEXE` — интерпретатора, в котором удобно отлаживать OCCT скриптами |
| `DETools` | Кодогенератор EXPRESS, нужен только разработчикам самого OCCT | Ничего практически значимого |
| samples, tests, Overview | Не код ядра | Примеры и doxygen-документация. Исходники остаются на диске, их можно читать глазами |

### Отдельно: сколько стоит DataExchange

Это не вопрос вкуса, это измерение. В OCCT 7.8 STEP-ридер переехал в `TKDESTEP`,
который по `EXTERNLIB` зависит от `TKXCAF`, а `TKXCAF` — от `TKV3d` и `TKService`:

```
cat C:/dev/freecad-kernel-fixes/occt/src/TKXCAF/EXTERNLIB
  ... TKService ... TKV3d ...

cat C:/dev/freecad-kernel-fixes/occt/src/TKService/EXTERNLIB
  ... CSF_FREETYPE ...
```

То есть **STEP в 7.8.1 нельзя взять «дёшево»**: он тащит ядро визуализации, вместе
с ним обязательную зависимость от FreeType, и вдобавок весь OCAF-стек
(`TKCDF TKLCAF TKCAF TKVCAF TKStd TKStdL TKBin* TKXml* TKTObj`).

Транзитивный замер обоих вариантов:

| Набор | Тулкитов | Файлов `.cxx`/`.c` | Сторонние библиотеки |
|---|---|---|---|
| Ядро (включено сейчас) | **18** | **2161** | нет |
| Ядро + `DataExchange` | **47** | **5403** | **FreeType** обязателен; RapidJSON/Draco опционально |

Рост объёма компиляции — **в 2.5 раза**.

FreeType на машине проверен и **непригоден**:

```
find "C:/Program Files/FreeCAD 1.1" -maxdepth 3 -iname 'freetype*'
  C:/Program Files/FreeCAD 1.1/bin/freetype.dll
  C:/Program Files/FreeCAD 1.1/lib/cmake/freetype
  C:/Program Files/FreeCAD 1.1/lib/pkgconfig/freetype2.pc

find "C:/Program Files/FreeCAD 1.1" -maxdepth 4 -iname 'freetype*.lib'  -> пусто
find "C:/Program Files/FreeCAD 1.1" -maxdepth 5 -name 'ft2build.h'      -> пусто
```

Есть только DLL. **Нет заголовков и нет import-библиотеки** — линковаться не с чем.

Поэтому зависимый модуль выключен, а не начата охота за библиотекой. Когда STEP
понадобится — порядок действий в §7.

---

## 3. Команда конфигурации

Скрипт: `build-scripts/configure-occt.ps1`. Запуск:

```powershell
powershell -ExecutionPolicy Bypass -File C:\dev\freecad-kernel-fixes\build-scripts\configure-occt.ps1
```

Он вызывает ровно это:

```
cmake.exe
  -S C:/dev/freecad-kernel-fixes/occt
  -B C:/dev/freecad-kernel-fixes/build/occt-release
  -G "Visual Studio 17 2022" -A x64
  -DBUILD_LIBRARY_TYPE=Shared
  -DBUILD_CPP_STANDARD=C++17
  -DINSTALL_DIR=C:/dev/freecad-kernel-fixes/install/occt-7.8.1
  -D3RDPARTY_DIR=
  -DBUILD_MODULE_FoundationClasses=ON
  -DBUILD_MODULE_ModelingData=ON
  -DBUILD_MODULE_ModelingAlgorithms=ON
  -DBUILD_MODULE_Visualization=OFF
  -DBUILD_MODULE_ApplicationFramework=OFF
  -DBUILD_MODULE_DataExchange=OFF
  -DBUILD_MODULE_Draw=OFF
  -DBUILD_MODULE_DETools=OFF
  -DBUILD_DOC_Overview=OFF -DBUILD_Inspector=OFF
  -DBUILD_SAMPLES_QT=OFF -DBUILD_SAMPLES_MFC=OFF
  -DBUILD_USE_PCH=OFF -DBUILD_WITH_DEBUG=OFF
  -DUSE_FREETYPE=OFF -DUSE_TK=OFF -DUSE_TCL=OFF
  -DUSE_OPENGL=OFF -DUSE_GLES2=OFF -DUSE_D3D=OFF -DUSE_VTK=OFF
  -DUSE_FREEIMAGE=OFF -DUSE_FFMPEG=OFF -DUSE_OPENVR=OFF
  -DUSE_RAPIDJSON=OFF -DUSE_DRACO=OFF -DUSE_TBB=OFF -DUSE_EIGEN=OFF
```

Сборка **вне исходников** — `C:/dev/freecad-kernel-fixes/occt` не изменяется.

Дерево сборки лежит в подкаталоге `build/occt-release`, а не прямо в `build/`,
потому что в `build/` уже работает другая команда (`build/implib`, `build/occt-inc` —
import-библиотеки, снятые с DLL, которые ставит FreeCAD). Их мы не трогаем.

### Результат конфигурации

```
-- Configuring done (28.5s)
-- Generating done (0.7s)
-- Build files have been written to: C:/dev/freecad-kernel-fixes/build/occt-release
=== CMAKE EXIT CODE: 0 ===
```

Выбранный инструментарий (из лога конфигурации):

* компилятор `MSVC 19.36.32532.0` →
  `VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64/cl.exe` (toolset v143)
* Windows SDK `10.0.22000.0`
* генератор `Visual Studio 17 2022`, платформа `x64`

**Ни одной сторонней библиотеки не искалось.** Это видно по тому, что переменные
`USE_FREETYPE`, `USE_TK`, `USE_OPENGL`, `USE_VTK`, `USE_RAPIDJSON` вообще
отсутствуют в `CMakeCache.txt`: OCCT их вычистил (`OCCT_CHECK_AND_UNSET`),
убедившись, что ни один включённый тулкит их не требует. Единственная оставшаяся
запись — `3RDPARTY_DIR:PATH=`, пустая.

Проверка сгенерированных целей:

```
find C:/dev/freecad-kernel-fixes/build/occt-release -name 'TK*.vcxproj' | wc -l
18
```

Ровно 18, совпадает с расчётом по `EXTERNLIB`. `TKService`, `TKV3d`, `TKXCAF`
в дереве отсутствуют.

Заголовки собраны в `C:/dev/freecad-kernel-fixes/build/occt-release/inc` — **3656 файлов**.

---

## 4. Проверка, что дерево действительно собирается

Конфигурация без сборки ничего не доказывает, поэтому собран один тулкит:

```powershell
cmake.exe --build C:/dev/freecad-kernel-fixes/build/occt-release --config Release --target TKernel --parallel 12
```

```
  TKernel.vcxproj -> C:\dev\freecad-kernel-fixes\build\occt-release\win64\vc14\bin\TKernel.dll
---- EXIT=0  elapsed=18.6 s ----
```

* скомпилировано 131 единица трансляции
* **0 ошибок, 0 предупреждений**
* получено:
  * `win64/vc14/bin/TKernel.dll` — 1 632 256 байт
  * `win64/vc14/lib/TKernel.lib` — 723 046 байт

То есть цепочка MSVC 14.36 + C++17 + `BUILD_LIBRARY_TYPE=Shared` работает и даёт
именно то, что нужно: DLL плюс import-библиотеку.

Грубая экстраполяция на полное ядро: 131 единица за 18,6 с на 12 ядрах ≈ 7 ед./с;
2161 единица — это порядка 5 минут чистой компиляции, плюс линковка тяжёлых
тулкитов (`TKBO`, `TKBool`, `TKGeomAlgo`) и ограничение параллелизма цепочкой
зависимостей. Ожидаемое время полной сборки — **десятки минут**, но это оценка,
а не измерение.

---

## 5. Место на диске

| Момент | Свободно на C: | Размер дерева сборки |
|---|---|---|
| До конфигурации | 30 ГБ | — |
| После конфигурации | 30 ГБ | 9 МБ |
| После сборки `TKernel` | 30 ГБ | 28 МБ |

Конфигурация практически ничего не стоит. Бюджет диска расходует полная сборка;
по доле `TKernel` (19 МБ на 131 единицу) на 2161 единицу ожидается порядка
нескольких сотен МБ — с запасом в пределах имеющихся 30 ГБ.

---

## 6. Оговорка про типы конфигурации

`-DCMAKE_CONFIGURATION_TYPES=Release` **не применяется**: OCCT перезаписывает эту
переменную принудительно в `CMakeLists.txt:7`

```
set (CMAKE_CONFIGURATION_TYPES Release Debug RelWithDebInfo CACHE INTERNAL "" FORCE)
```

Поэтому в `CMakeCache.txt` стоит `Release;Debug;RelWithDebInfo`. Практического
вреда нет: генератор многоконфигурационный, собирается только то, что явно
запрошено ключом `--config`. Debug не собирается и места не занимает, пока его
не попросить.

---

## 7. Как этим пользоваться дальше

### Полная сборка

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe' --build C:/dev/freecad-kernel-fixes/build/occt-release --config Release --parallel 12
```

### Установка (заголовки + `.lib` + `.dll` в одно дерево)

```powershell
& '...\cmake.exe' --build C:/dev/freecad-kernel-fixes/build/occt-release --config Release --target INSTALL
```

Разложится в `C:/dev/freecad-kernel-fixes/install/occt-7.8.1`:

* `inc/` — заголовки
* `win64/vc14/lib/` — import-библиотеки `.lib`
* `win64/vc14/bin/` — `.dll`

Именно на это дерево линкуется приложение.

### Переконфигурация

Конфигурация идемпотентна — скрипт можно просто запустить заново.

**Добавить STEP/IGES позже.** Нужен FreeType с заголовками и `.lib`, затем:

```powershell
& '...\cmake.exe' -S C:/dev/freecad-kernel-fixes/occt -B C:/dev/freecad-kernel-fixes/build/occt-release -DBUILD_MODULE_DataExchange=ON -DUSE_FREETYPE=ON -D3RDPARTY_FREETYPE_DIR=<путь>
```

Учитывать: это доберёт ещё 29 тулкитов (18 → 47), в 2,5 раза увеличит объём
компиляции и включит `TKService`/`TKV3d`. Делать отдельным заходом, померив
свободное место до и после.

**Начать с нуля.** Удалить `C:/dev/freecad-kernel-fixes/build/occt-release` целиком и
запустить скрипт заново. Исходники при этом не затрагиваются.

**Вернуть C++11** (как в официальных бинарниках OCCT): `-DBUILD_CPP_STANDARD=C++11`.
Здесь выбран C++17, потому что приложение будет писаться на C++17, и так
исключается расхождение по стандарту между ядром и приложением.

### Важно при запуске своего приложения

Собранные DLL лежат в `win64/vc14/bin`. Этот каталог должен быть в `PATH`
(или DLL — рядом с exe), иначе программа не стартует.

---

## Результат полной сборки (12.09.2026, 02:33–02:40)

### Команда

Запускалась из PowerShell, в фоне, отсоединённым процессом (`Start-Process
-WindowStyle Hidden`), лог писался в файл:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe' `
    --build C:/dev/freecad-kernel-fixes/build/occt-release --config Release --parallel 12
```

Флаги MSBuild (`/m:12`, `/v:minimal`) отдельно **не передавались**: `--parallel 12`
достаточно, а слэш-флаги ломаются, если запускать сборку через Bash-инструмент
(MSYS превращает `/m:12` в путь, MSBuild отвечает `error MSB1008`).

### Тайминги и итог

| Показатель | Значение | Чем измерено |
|---|---|---|
| Старт | 2026-09-12T02:33:32 | `build-all.status` |
| Финиш | 2026-09-12T02:39:43 | `build-all.status` |
| Стена | **371,53 с (6 мин 11,5 с)** | `Stopwatch` вокруг `cmake --build` |
| Код возврата | **0** | `EXIT 0` в `build-all.status` |
| `error C####` | 0 | `grep -c -E "error C[0-9]+"` по логу |
| `error LNK` | 0 | `grep -c "error LNK"` |
| `error MSB` | 0 | `grep -c "error MSB"` |
| warning | 0 | `grep -ci warning` |

`TKernel` к началу этого прогона уже был собран (проверка тулчейна, 18,6 с),
поэтому 371,53 с — это 17 тулкитов; полная сборка «с нуля» ≈ 390 с.

### Что получилось и где лежит

* **18 DLL** — `C:/dev/freecad-kernel-fixes/build/occt-release/win64/vc14/bin/` (29 МБ)
* **18 import-библиотек `.lib`** — `C:/dev/freecad-kernel-fixes/build/occt-release/win64/vc14/lib/` (18 МБ)
* **3656 заголовков** — `C:/dev/freecad-kernel-fixes/build/occt-release/inc/`

```
TKBO.dll       1950208    TKG3d.dll       878080    TKMesh.dll      602112
TKBRep.dll      860672    TKGeomAlgo.dll 3800064    TKOffset.dll   1866240
TKBool.dll     3449856    TKGeomBase.dll 3840512    TKPrim.dll      288768
TKFeat.dll     1059840    TKHLR.dll       892928    TKShHealing.dll 2478592
TKFillet.dll   2137600    TKMath.dll     1619968    TKTopAlgo.dll  2262016
TKG2d.dll       276480    TKXMesh.dll      12288    TKernel.dll    1632256
```

### Диск

| Момент | Свободно на C: | Чем измерено |
|---|---|---|
| до сборки | 30 ГБ | `df -h /c` → `30G` |
| через 3 мин сборки | 30257 МБ | `df -m /c` |
| после сборки | 29634 МБ | `df -m /c` |

Дерево сборки выросло с 28 МБ до **476 МБ** (`du -sm`), то есть сборка стоила
448 МБ. Порог остановки (5 ГБ) не приближался.

---

## Проверка: ядро действительно пригодно

Это не отчёт о сборке, а доказательство. `repro/kernel-smoke/kernel_smoke.cpp`
строит коробку, строит цилиндр, вычитает один из другого, скругляет обычное
ребро и печатает объём и валидность. Все объёмы известны аналитически заранее.

Валидность печатается **двумя** способами, и это принципиально: `BRepCheck_Analyzer`
— это то, что за кулисами дёргает `Shape.isValid()` во FreeCAD, а `BRepAlgoAPI_Check`
— BOP-проверка (мелкие рёбра + самопересечения). В дефекте, ради которого заведён
проект, они расходятся.

### Точная строка компиляции и линковки (работает на этой машине)

Сначала окружение — **без** `vcvars64.bat`, чтобы ничего не запускало `cmd.exe`:

```powershell
$MSVC   = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.36.32532'
$SDK    = 'C:\Program Files (x86)\Windows Kits\10'
$SDKVER = '10.0.22000.0'
$OCCT   = 'C:\dev\freecad-kernel-fixes\build\occt-release'

$env:INCLUDE = "$MSVC\include;$SDK\Include\$SDKVER\ucrt;$SDK\Include\$SDKVER\um;$SDK\Include\$SDKVER\shared"
$env:LIB     = "$MSVC\lib\x64;$SDK\Lib\$SDKVER\ucrt\x64;$SDK\Lib\$SDKVER\um\x64"
$env:PATH    = "$MSVC\bin\Hostx64\x64;$OCCT\win64\vc14\bin;$env:PATH"
```

Затем сама строка — ровно та, что отработала:

```
cl.exe /nologo /EHsc /std:c++17 /MD /O2 /W3
       /IC:\dev\freecad-kernel-fixes\build\occt-release\inc
       C:\dev\freecad-kernel-fixes\repro\kernel-smoke\kernel_smoke.cpp
       /Fo:C:\dev\freecad-kernel-fixes\build\kernel-smoke\
       /Fe:C:\dev\freecad-kernel-fixes\build\kernel-smoke\kernel_smoke.exe
       /link /LIBPATH:C:\dev\freecad-kernel-fixes\build\occt-release\win64\vc14\lib
       TKernel.lib TKMath.lib TKG2d.lib TKG3d.lib TKGeomBase.lib
       TKGeomAlgo.lib TKBRep.lib TKTopAlgo.lib TKPrim.lib TKBO.lib
       TKBool.lib TKShHealing.lib TKFillet.lib TKOffset.lib TKFeat.lib
       TKMesh.lib TKXMesh.lib TKHLR.lib
```

`cl EXIT=0, elapsed=1.51 s`. Всё это завёрнуто в
`build-scripts/build-kernel-smoke.ps1` — скрипт компилирует, линкует и запускает:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\dev\freecad-kernel-fixes\build-scripts\build-kernel-smoke.ps1
```

Важное про `/MD`: OCCT собран в Release с динамической CRT, приложение обязано
быть таким же. `/MT` даст две копии CRT и падение на первом же исключении OCCT.

### Что напечатала программа

```
OCCT linked into this binary: OCC_VERSION_COMPLETE = 7.8.1

box 40x30x20           volume =   24000.000000   expected =   24000.000000   delta = +3.638e-12
                       faces =   6  edges =  12  vertices =   8
                       BRepCheck_Analyzer.IsValid = true   BRepAlgoAPI_Check.IsValid = true

cylinder r6 h20        volume =    2261.946711   expected =    2261.946711   delta = +0.000e+00
                       faces =   3  edges =   3  vertices =   2
                       BRepCheck_Analyzer.IsValid = true   BRepAlgoAPI_Check.IsValid = true

box - cylinder         volume =   21738.053289   expected =   21738.053289   delta = +3.638e-12
                       faces =   7  edges =  15  vertices =  10
                       BRepCheck_Analyzer.IsValid = true   BRepAlgoAPI_Check.IsValid = true

fillet r3 on 1 edge    volume =   21699.424959   expected =   21699.424959   delta = +7.276e-12
                       faces =   8  edges =  18  vertices =  12
                       BRepCheck_Analyzer.IsValid = true   BRepAlgoAPI_Check.IsValid = true

fillet removed 38.628331 mm3 (analytic 38.628331 mm3)

RESULT: PASS (relative volume error 3.353e-16, tolerance 1e-9)
```

Скругление сняло 38,628331 мм³ при аналитических (9 − 2,25·π)·20 = 38,628331 мм³.
Объём считается адаптивным интегрированием (`BRepGProp::VolumeProperties(S, P, 1e-11)`),
достигнутая относительная погрешность — 4,7e-16, так что сходимость до 1e-12 мм³
это свойство ядра, а не слабый допуск.

### Что это доказывает

* Заголовки из `inc/` разрешаются, `.lib` линкуются, `.dll` грузятся.
* Программа запущена с `PATH`, где лежат **только** `...\occt-release\win64\vc14\bin`
  и `C:\Windows\System32` — и отработала с кодом 0. То есть используются
  свежесобранные DLL, а не чьи-то ещё. (`C:\Program Files\FreeCAD 1.1\bin`
  в машинном `PATH` вообще отсутствует — проверено.)
* `dumpbin /dependents` по exe: прямые импорты — `TKernel, TKMath, TKG3d, TKBRep,
  TKTopAlgo, TKPrim, TKBO, TKFillet`. Транзитивное замыкание по DLL — **13** из 18:
  добавляются `TKBool, TKG2d, TKGeomAlgo, TKGeomBase, TKShHealing`. Остальные пять
  (`TKFeat, TKHLR, TKMesh, TKOffset, TKXMesh`) этой программе не нужны, но собраны.

### Результат в файле

Программа принимает необязательный аргумент — путь, куда записать итоговую форму
в формате BREP: `C:\dev\freecad-kernel-fixes\build\kernel-smoke\kernel_smoke_result.brep`
(4758 байт, заголовок `CASCADE Topology V3`). Это удобно, чтобы потом открыть
результат во FreeCAD и сравнить глазами.

## После переезда папки (13 сентября 2026)

Проект переехал из `C:\dev\seamless` в `C:\dev\freecad-kernel-fixes`. Каталоги сборки CMake хранят
абсолютный путь в `CMakeCache.txt` (`CMAKE_CACHEFILE_DIR`), и с таким кешем CMake работать отказывается.
Лечится сбросом кеша и повторной конфигурацией; исходники трогать не нужно.

Проверено на дереве `build/occt-cond` (исходники `C:/dev/occt-cond` не переезжали):

```bash
B=/c/dev/freecad-kernel-fixes/build/occt-cond
mv "$B/CMakeCache.txt" "$B/CMakeCache.txt.old-path.bak"
rm -rf "$B/CMakeFiles"
powershell -ExecutionPolicy Bypass -File build-scripts/configure-occt-cond.ps1   # EXIT 0, 46.00 s
powershell -ExecutionPolicy Bypass -File build-scripts/build-occt-cond.ps1 -Target TKernel   # EXIT 0, 28.95 s, 0 ошибок
```

Остальные три дерева — `build/occt-release`, `build/occt-e9`, `build/occt-fix` — по-прежнему помнят
старый путь и перед следующим использованием требуют того же сброса своим скриптом конфигурации.
У `occt-release` исходники лежали в `C:/dev/seamless/occt`, теперь это `C:/dev/freecad-kernel-fixes/occt`.

Проверенная патченая библиотека, которую ставит `install-into-freecad.ps1`, лежит отдельной копией в
`build/bin-cond` и от пересборки не зависит: её md5 `4e89e519…` после этой проверки не изменился.
