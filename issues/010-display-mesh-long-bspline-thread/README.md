# 010 — сборка открывается 55 с вместо 2.5 с: сетка отображения винта ШВП при Angular Deflection 6.4°

**Чей:** FreeCAD, `ViewProviderPartExt::setupCoinGeometry` (`src/Mod/Part/Gui/ViewProviderExt.cpp:1080-1110`
в 1.1.1) задаёт параметры сетки; стоимость создаёт OCCT `BRepMesh` (контроль отклонения поверхности,
`IMeshTools_Parameters::ControlSurfaceDeflection`). Это не ошибка результата, а ловушка производительности:
форма и сетка верны, но строятся в 20-70 раз дольше, чем нужно для заданной линейной точности.

**Статус:** измерено. Обход без патчей (вернуть 28.5°) проверен на файле владельца. Экспериментальный
`ControlSurfaceDeflection=false` проверен внутри частной копии FreeCAD 1.1.1 (`C:\dev\fc-perf`) через
пересобранный `TKMesh.dll` с переключателем по переменной окружения. FreeCAD не пересобирался, так что
предлагаемое изменение `ViewProviderExt.cpp` само не собрано. У владельца ничего не установлено.

## 1. Симптом

Файл владельца `VR6-350-new.FCStd` (132 объекта, 58 `Part::Feature` из STEP, 13.2 МБ BRep). FreeCAD 1.1.1,
OCCT 7.8.1, Windows 11, Ryzen 5 5600U (6 ядер / 12 потоков), Qt offscreen, HybridDesign загружен:

| Замер | Время |
|---|---|
| `App.openDocument` без GUI | 0.63 с (повтор 0.30-0.33 с) |
| `doc.recompute()` после открытия | 0.002 с |
| открытие в GUI (Gui-документ, провайдеры вида, сетки) | **55.4 / 48.8 / 55.4 с** |
| то же, копия файла с Angular Deflection 28.5° | **2.58 / 2.49 с** (3.51 с во время скачивания) |

В `GuiDocument.xml` у всех 58 тел сохранено `AngularDeflection = 6.4` (в `user.cfg` владельца
`Mod/Part/MeshAngularDeflection = 6.4`, стандарт FreeCAD 28.5). Настройка действует только на новые
объекты; уже сохранённые файлы открываются со своим значением.

## 2. Где время

Повтор `updateVisual` у каждого видимого тела через его же триггер (изменение `AngularDeflection`,
`ViewProviderExt.cpp:951`), `repro/python/gui_open.py` с `PERF_TESS=1`:

| | сохранённые 6.4° | 28.5° |
|---|---|---|
| все 56 видимых тел | 57.5 с (повтор 51.0 с) | 1.54 с |
| `Part__Feature014` «SFU1605-400 Ball Screw» | **53.3 с** (повтор 47.0 с) | 0.84 с |
| следующее по стоимости (`Part__Feature019`) | 0.80 с | 0.14 с |

Одно тело — 93 % времени открытия. Его 172 грани: 151 цилиндр, 7 плоскостей, 2 конуса, 2 тора и
**10 B-сплайновых граней резьбы: степень 3×2 (или 1×2), 4×1305 полюсов, 2×653 узла**. Покадрово,
однопоточно (`repro/python/faces_mesh.py`, `MeshPart.meshFromShape` = `BRepMesh_IncrementalMesh` с тем же
прогибом 0.6349 мм, который `Part::Tools::getDeflection` даёт для габарита тела):

| грань | площадь, мм² | 28.5°: с / треуг. | 10°: с | 6.4°: с / треуг. |
|---|---|---|---|---|
| 170 (B-сплайн 4×1305) | 1419.8 | 0.587 / 20 130 | 11.90 | **46.50** / 390 647 |
| 156 | 11437.7 | 0.187 / 6 004 | 6.91 | 18.22 / 172 831 |
| 154 | 497.1 | 0.234 / 10 112 | 4.64 | 10.27 / 111 222 |
| 168 | 488.4 | 0.254 / 10 868 | 4.39 | 9.13 / 108 953 |
| 155, 157 | 287 | 0.13 / ~5 400 | 2.2-2.4 | 5.9 / ~73 000 |
| всё тело одним вызовом | — | 1.82 / 75 506 | 33.57 / 514 490 | 95.24 / 1 008 762 |

`BRepMesh` распараллеливает по граням (`InParallel = true` у FreeCAD), поэтому нижняя граница времени —
самая дорогая грань: 46.5 с одной грани против 53 с всего тела в GUI. Время растёт быстрее числа
треугольников: грань 170 — в 19.4 раза больше треугольников и в 79 раз дольше.

## 3. Какой параметр стоит времени

`repro/cpp/mesh_params.cpp`, тот же вызов, что у FreeCAD (`Relative=false`, `InParallel=true`,
`AllowQualityDecrease=true`, перед каждым прогоном `BRepTools::Clean(shape, true)`), библиотеки OCCT из
`C:\Program Files\FreeCAD 1.1\bin`. Ошибка хорды — расстояние от центра треугольника до поверхности в
UV-центре (каждый 7-й треугольник), прогиб-цель 0.6349 мм (`results/mesh_params_quality_whole.txt`):

| конфигурация | время, с | треугольники | ошибка хорды max / средняя, мм |
|---|---|---|---|
| сохранённые 6.4° (как у FreeCAD) | 45.85 | 1 008 762 | 0.125 / 0.0029 |
| 10° | 13.03 | 514 490 | 0.119 / 0.0044 |
| 15° | 5.62 | 272 186 | 0.348 / 0.0087 |
| 28.5° (стандарт) | 0.63 | 75 510 | 0.493 / 0.0404 |
| **6.4°, `ControlSurfaceDeflection = false`** | **4.01** | 210 486 | 0.380 / 0.0156 |
| 15°, `ControlSurfaceDeflection = false` | 0.75 | 96 144 | 0.489 / 0.0252 |
| 28.5°, `ControlSurfaceDeflection = false` | 0.29 | 50 054 | 0.419 / 0.0582 |
| 6.4°, `AngleInterior = 28.5°` | 14.35 | 488 260 | 0.360 / 0.0059 |
| 6.4°, Delabella (`CSF_MeshAlgo`) | 86.19 | 960 060 | — |

Первый прогон сохранённых 6.4° в той же программе дал 101.05 с (`results/mesh_params_whole_first_run.txt`),
второй — 45.85 с; причина разброса не найдена, соотношения внутри одного прогона устойчивы. Delabella в
GUI тоже медленнее: 88.9 с против 55.4 с.

Все варианты укладываются в заданный прогиб 0.635 мм. 6.4° делает сетку в 5 раз точнее, чем просит
линейный допуск, и это стоит 72× времени против 28.5°.

## 4. Проверка внутри FreeCAD

Частная копия `C:\dev\fc-perf` (robocopy `C:\Program Files\FreeCAD 1.1`, 2.058 ГБ), в ней `bin\TKMesh.dll`
заменён сборкой `build/occt-bo` с патчем `patches/0001-EXPERIMENT-BRepMesh-env-overrides.patch`
(md5 `B8281762…`, сток рядом — `TKMesh.dll.stock`, md5 `C23ECD1A…`). Патч только читает переменные
окружения после `initParameters()`; без них поведение стоковое. Исходник OCCT после сборки возвращён
`git checkout`.

| прогон (`results/`) | открытие в GUI | сетки всех тел (повтор) | `Part__Feature014` |
|---|---|---|---|
| `fcperf_vr6_stored_csd_unset` — DLL без переменной | 59.10 с | 57.48 с | 52.99 с |
| `fcperf_vr6_stored_csd0` — `OCCT_MESH_CSD=0`, углы 6.4° как в файле | **8.29 с** | 7.19 с | 4.08 с |
| `fcperf_cube_csd0`, `fcperf_hicmos_csd0` | 0.62 с, 0.95 с | — | — |

## 5. Предложение для FreeCAD (не собрано)

`src/Mod/Part/Gui/ViewProviderExt.cpp`, функция `ViewProviderPartExt::setupCoinGeometry(...)` (стр. 1047;
`angularDeflection` — её параметр, группы настроек в ней нет), после
`meshParams.AllowQualityDecrease = Standard_True;` (стр. 1101):

```cpp
// Surface-deflection control re-inserts nodes until every triangle is within Deflection of the surface.
// On long B-spline faces with a small angular deflection it costs 10-70x the time for an error already
// below Deflection (freecad-kernel-fixes issue 010). Default: on only from the stock angle up.
ParameterGrp::handle hPart = App::GetApplication().GetParameterGroupByPath(
    "User parameter:BaseApp/Preferences/Mod/Part");
meshParams.ControlSurfaceDeflection =
    hPart->GetBool("MeshControlSurfaceDeflection", angularDeflection >= 28.5);
```

Ожидаемый выигрыш на файле владельца — замер раздела 4: 59.1 → 8.3 с при сохранённых 6.4°.

Upstream: PR FreeCAD #32397 «Limit global tessellation» (открыт, запрошены правки из-за артефактов)
описывает ту же картину — «STEP-станок с шариковыми винтами», минуты на кадр — и вводит предел треугольников
2 000 000 по умолчанию (по описанию PR, код не проверялся). В этом теле 1 008 762 треугольника, так что
такой предел по умолчанию его бы не затронул.

## 6. Что не сделано

- FreeCAD не пересобран, изменение раздела 5 не скомпилировано; проверен эквивалент на уровне `TKMesh.dll`.
- Отрисовка через OpenGL не измерена: Qt offscreen не создаёт 3D-вид, первое рисование 1 млн треугольников
  в замеры не входит.
- Визуально сетка с `ControlSurfaceDeflection=false` не осмотрена; есть только числовая ошибка хорды.
- В отчёт OCCT не отправлено.

## Воспроизведение

```
powershell -File build-scripts/build-mesh-params.ps1
powershell -File build-scripts/run-mesh-params.ps1 -Quality -Only "freecad_6.4_stored,freecad_28.5_default,6.4_csd_off"
"C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe" repro/python/faces_mesh.py   (env PERF_FILE, PERF_OUT, PERF_OBJ=Part__Feature014)
```

Фикстура `fixtures/sfu1605_ball_screw.brep` — `Part__Feature014.Shape.brp` из файла владельца, байт в байт.
