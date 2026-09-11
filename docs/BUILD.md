# Сборка OCCT 7.8.1 как ядра для собственного CAD-приложения

Документ описывает **шаг конфигурации** дерева сборки OCCT: что включено, что
выключено и почему, какими точными командами это воспроизводится.

Всё измерено на этой машине. Каждое утверждение сопровождается командой, которая
его подтверждает.

---

## 1. Что за исходники

```
git -C C:/dev/seamless/occt log -1 --format='%H%n%d%n%ci%n%s'
```

```
bd2a789f15235755ce4d1a3b07379a2e062fdc2e
 (grafted, HEAD, tag: V7_8_1)
2024-03-31 23:05:22 +0100
Update version to 7.8.1
```

```
grep OCC_VERSION_COMPLETE C:/dev/seamless/occt/src/Standard/Standard_Version.hxx
#define OCC_VERSION_COMPLETE     "7.8.1"
```

**Это релизный тег V7_8_1, а не ветка разработки.** Клон поверхностный
(`grafted`, без полной истории), HEAD отсоединён на теге.

Это важно: ровно та же версия ядра, что внутри FreeCAD 1.1.1. Значит дефект
скругления у шва воспроизводится на этом самом коде, а не на «похожем».

Размер исходников — 333 МБ (`du -sm C:/dev/seamless/occt`; два замера подряд дали
одно и то же число — клонирование завершено). Рабочее дерево чистое:
`git -C C:/dev/seamless/occt status --porcelain` пусто.

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
cat C:/dev/seamless/occt/src/TKXCAF/EXTERNLIB
  ... TKService ... TKV3d ...

cat C:/dev/seamless/occt/src/TKService/EXTERNLIB
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
powershell -ExecutionPolicy Bypass -File C:\dev\seamless\build-scripts\configure-occt.ps1
```

Он вызывает ровно это:

```
cmake.exe
  -S C:/dev/seamless/occt
  -B C:/dev/seamless/build/occt-release
  -G "Visual Studio 17 2022" -A x64
  -DBUILD_LIBRARY_TYPE=Shared
  -DBUILD_CPP_STANDARD=C++17
  -DINSTALL_DIR=C:/dev/seamless/install/occt-7.8.1
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

Сборка **вне исходников** — `C:/dev/seamless/occt` не изменяется.

Дерево сборки лежит в подкаталоге `build/occt-release`, а не прямо в `build/`,
потому что в `build/` уже работает другая команда (`build/implib`, `build/occt-inc` —
import-библиотеки, снятые с DLL, которые ставит FreeCAD). Их мы не трогаем.

### Результат конфигурации

```
-- Configuring done (28.5s)
-- Generating done (0.7s)
-- Build files have been written to: C:/dev/seamless/build/occt-release
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
find C:/dev/seamless/build/occt-release -name 'TK*.vcxproj' | wc -l
18
```

Ровно 18, совпадает с расчётом по `EXTERNLIB`. `TKService`, `TKV3d`, `TKXCAF`
в дереве отсутствуют.

Заголовки собраны в `C:/dev/seamless/build/occt-release/inc` — **3656 файлов**.

---

## 4. Проверка, что дерево действительно собирается

Конфигурация без сборки ничего не доказывает, поэтому собран один тулкит:

```powershell
cmake.exe --build C:/dev/seamless/build/occt-release --config Release --target TKernel --parallel 12
```

```
  TKernel.vcxproj -> C:\dev\seamless\build\occt-release\win64\vc14\bin\TKernel.dll
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
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe' --build C:/dev/seamless/build/occt-release --config Release --parallel 12
```

### Установка (заголовки + `.lib` + `.dll` в одно дерево)

```powershell
& '...\cmake.exe' --build C:/dev/seamless/build/occt-release --config Release --target INSTALL
```

Разложится в `C:/dev/seamless/install/occt-7.8.1`:

* `inc/` — заголовки
* `win64/vc14/lib/` — import-библиотеки `.lib`
* `win64/vc14/bin/` — `.dll`

Именно на это дерево линкуется приложение.

### Переконфигурация

Конфигурация идемпотентна — скрипт можно просто запустить заново.

**Добавить STEP/IGES позже.** Нужен FreeType с заголовками и `.lib`, затем:

```powershell
& '...\cmake.exe' -S C:/dev/seamless/occt -B C:/dev/seamless/build/occt-release -DBUILD_MODULE_DataExchange=ON -DUSE_FREETYPE=ON -D3RDPARTY_FREETYPE_DIR=<путь>
```

Учитывать: это доберёт ещё 29 тулкитов (18 → 47), в 2,5 раза увеличит объём
компиляции и включит `TKService`/`TKV3d`. Делать отдельным заходом, померив
свободное место до и после.

**Начать с нуля.** Удалить `C:/dev/seamless/build/occt-release` целиком и
запустить скрипт заново. Исходники при этом не затрагиваются.

**Вернуть C++11** (как в официальных бинарниках OCCT): `-DBUILD_CPP_STANDARD=C++11`.
Здесь выбран C++17, потому что приложение будет писаться на C++17, и так
исключается расхождение по стандарту между ядром и приложением.

### Важно при запуске своего приложения

Собранные DLL лежат в `win64/vc14/bin`. Этот каталог должен быть в `PATH`
(или DLL — рядом с exe), иначе программа не стартует.
