# Измерения: шов (seam) в OCCT 7.8.1 / FreeCAD 1.1.1

Это фактическая база проекта. Каждое число здесь получено вызовом, который приведён
рядом, и воспроизводится скриптами из `repro/python/`. Ни одно число не взято
«по памяти»: если утверждение нельзя было измерить, оно так и помечено.

Дата измерений: 12 сентября 2026 года.

---

## 0. Окружение и как всё это перезапустить

```
FreeCAD.Version()  = ['1', '1', '1', '20260414 (Git shallow)', 'Unknown',
                      '2026/04/14 22:09:59', '(HEAD detached at 0108fd4b4)',
                      '0108fd4b4850cc46e625b60e53cea7a7bbe69f8d']
Part.OCC_VERSION   = 7.8.1
sys.version        = 3.11.14 | packaged by conda-forge | (main, Oct 13 2025, 14:00:26)
                     [MSC v.1944 64 bit (AMD64)]
```
(вывод `repro/python/06_python_reach.py`, раздел A)

Всё запускается без окна:

```
timeout -k 5 540 "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" <script.py> 2>&1 1>/dev/null
```

Почему `2>&1 1>/dev/null`: измерения скрипты печатают в **stderr**, а FreeCAD пишет
свой баннер и индикатор `Recompute... (37 %)` с возвратами каретки в **stdout** и не
сбрасывает буфер до выхода. Если смешать потоки, строки с числами затираются. Подробности —
в `repro/README.md`.

Почему обязательно `timeout`: скругление рядом со швом может не вернуться вовсе
(раздел 5). Убитый по таймауту прогон — это тоже измерение, и оно записывается.

| Факт | Скрипт | Раздел здесь |
|---|---|---|
| что такое шов, как его найти | `01_seam_anatomy.py` | 1 |
| одно ребро — две pcurve | `02_two_pcurves.py` | 2 |
| минимальная пара и порог расстояния | `03_minimal_pair.py` | 3 |
| `isValid()` против `check(True)` | `04_isvalid_vs_bop.py` | 4 |
| шов можно не создавать | `05_removing_the_seam.py` | 6 |
| что достижимо из Python | `06_python_reach.py` | 7 |
| реальная деталь владельца, полоса зависания | `07_user_part_fillet.py` | 5 |
| `Part.makeThread` и витки | `08_thread_turns.py` | 8 |
| `PartDesign::AdditiveHelix` | `09_helix_profile.py` | 9 |

---

## 1. Что такое шов и как его обнаружить

### 1.1. Поверхность замкнута по параметру

Цилиндрическая поверхность периодична по `u` с периодом `2*pi`, и точка при `u = 0`
совпадает с точкой при `u = 2*pi`:

```
Part.makeCylinder(5.0, 10.0)
  surface        = Part::GeomCylinder  R = 5.0000  Axis = (0.0000, 0.0000, 1.0000)
  isUPeriodic()  = True        isVPeriodic() = False
  UPeriod()      = 6.283185  (== 2*pi: True)
  face.ParameterRange = u[0.0000 .. 6.2832]  v[0.0000 .. 10.0000]
  S(u=0.0000, v=0) = (5.0000, 0.0000, 0.0000)
  S(u=1.5708, v=0) = (0.0000, 5.0000, 0.0000)
  S(u=3.1416, v=0) = (-5.0000, 0.0000, 0.0000)
  S(u=6.2832, v=0) = (5.0000, -0.0000, 0.0000)
  |S(0,0) - S(2pi,0)| = 0.000000000000  -> the parameter square is glued along u
```

Параметрический квадрат склеен по `u`. Грань вынуждена иметь ребро на линии склейки —
это и есть шов.

### 1.2. Детектор: у шва ровно одна смежная грань

В замкнутом теле любое обычное ребро принадлежит двум граням. Ребро с **одной**
смежной гранью — шов; его обходит дважды контур этой единственной грани.

```
edges of the solid: 3, faces: 3
  Edge1  Part::GeomCircle     len =  31.4159  adjacent faces = 2
  Edge2  Part::GeomLine       len =  10.0000  adjacent faces = 1 <- SEAM
  Edge3  Part::GeomCircle     len =  31.4159  adjacent faces = 2
seam_edges() found 1 seam(s)
```

Реализация детектора — `seam_edges()` в `common/python/seamlib.py`:
`shape.ancestorsOfType(edge, Part.Face)` и проверка длины результата.

### 1.3. Якорь: шов лежит на изо-линии `u = 0`

```
  seam Edge2 on Face1 (Part::GeomCylinder)
    from (5.0000, -0.0000, 0.0000) to (5.0000, -0.0000, 10.0000)   len = 10.0000
    Center = (0.0000, 0.0000, 0.0000)  Rotation.Q = (0.0, 0.0, 0.0, 1.0)
    Center + R*Rot*(1,0,0) = (5.0000, 0.0000, 0.0000)
    distance(seam start, that point) = 0.000000000000
    srf.parameter(seam start) = (u = 6.283185307, v = 0.000000000)
```

Формула, по которой шов предсказывается точно:

```
anchor = Center + R * (Surface.Rotation.multVec(Vector(1, 0, 0)))
```

Она следует за системой координат поверхности, а не за телом. Повернём цилиндр —
якорь повернётся вместе с ним, и расстояние остаётся нулевым:

```
  spin about Z =    0.0 deg -> u=0 point (5.0000, 0.0000, 0.0000)  dir (1.0000, 0.0000, 0.0000)  dist(seam, u=0 point) = 0.000000000000
  spin about Z =   30.0 deg -> u=0 point (4.3301, 2.5000, 0.0000)  dir (0.8660, 0.5000, 0.0000)  dist(seam, u=0 point) = 0.000000000000
  spin about Z =   90.0 deg -> u=0 point (-0.0000, 5.0000, 0.0000)  dir (-0.0000, 1.0000, 0.0000)  dist(seam, u=0 point) = 0.000000000000
  spin about Z =  180.0 deg -> u=0 point (-5.0000, 0.0000, 0.0000)  dir (-1.0000, 0.0000, 0.0000)  dist(seam, u=0 point) = 0.000000000000
```

### 1.4. Шов появляется ровно тогда, когда грань покрывает весь период

```
  makeCylinder(5, 10, angle =  360.0 deg): solid faces = 3, u span = 6.283185 of period 6.283185
      closed in u = True   seam edges = 1
  makeCylinder(5, 10, angle =  180.0 deg): solid faces = 5, u span = 3.141593 of period 6.283185
      closed in u = False   seam edges = 0
  makeCylinder(5, 10, angle =  359.0 deg): solid faces = 5, u span = 6.265732 of period 6.283185
      closed in u = False   seam edges = 0
```

Недостающего одного градуса хватает, чтобы шва не было. Это ключ к разделу 6.

**Важная оговорка про детектор.** У *одиночной* грани (не внутри тела) все рёбра имеют
одну смежную грань, поэтому считать швы можно только внутри замкнутого тела.

---

## 2. Одно ребро — две параметрические кривые

Тот же цилиндр, то же ребро, спрошенное дважды — прямо и обращённо:

```
  as-is     Face.curveOnSurface(edge) -> Line2d   from (u = 6.2832, v = 0.0000) to (u = 6.2832, v = 10.0000)
  reversed  Face.curveOnSurface(edge) -> Line2d   from (u = 0.0000, v = 0.0000) to (u = 0.0000, v = 10.0000)
```

Две `Line2d` — при `u = 2*pi` и при `u = 0`. Обычное ребро ведёт себя иначе: оно
принадлежит двум граням и несёт по одной кривой на каждой:

```
the top/bottom circle belongs to 2 faces
  face 1 (Part::GeomCylinder  ) -> Line2d       from (0.0000, 10.0000) to (6.2832, 10.0000)
  face 2 (Part::GeomPlane     ) -> Circle2d     from (5.0000, 0.0000) to (5.0000, -0.0000)
```

Прямое доказательство двойного обхода — `OuterWire.OrderedEdges`, где шов встречается
дважды, в двух ориентациях:

```
  Face.Edges        = 3   (distinct edges of the face)
  OuterWire.Edges   = 3   (Python de-duplicates here)
  OuterWire.OrderedEdges = 4   <- the traversal, and it is one longer

    step 1: Edge1  Part::GeomCircle   orientation = Reversed length = 31.4159
    step 2: Edge2  Part::GeomLine     orientation = Reversed length = 10.0000
    step 3: Edge3  Part::GeomCircle   orientation = Forward  length = 31.4159
    step 4: Edge2  Part::GeomLine     orientation = Forward  length = 10.0000
```

`Edge2` — шов. Граница параметрического квадрата имеет четыре стороны, а у тела
только три различных ребра; четвёртая сторона — это то же ребро во второй раз.

То же правило на остальных замкнутых поверхностях:

```
  cylinder  Part.makeCylinder(5, 10)   faces = 3  edges = 3  seams = 1
  sphere    Part.makeSphere(5)         faces = 1  edges = 3  seams = 3
  torus     Part.makeTorus(10, 3)      faces = 1  edges = 2  seams = 2
  cone      Part.makeCone(5, 2, 10)    faces = 3  edges = 3  seams = 1
```

Тор периодичен по обоим параметрам (`uPer=True vPer=True`) и несёт два шва.
Это понадобится в разделе 4.

---

## 3. Минимальная пара и порог расстояния

### 3.1. Стенд

Коробка 25 x 25.7184 x 10 мм и цилиндрический карман радиусом 6.647656 мм, ось
которого наклонена на 45 градусов вокруг Y и пересекает верхнее рёберное ребро коробки.
Полное описание — `build_fixture()` в `common/python/seamlib.py`. Меняется **одно**
число: `AngleXU` — угол, на который повёрнута окружность профиля внутри своей же
плоскости эскиза. Поворот полной окружности вокруг собственной оси не сдвигает ни одной
её точки; он сдвигает только начало параметризации, то есть шов.

### 3.2. Тела доказанно одинаковы

```
  AngleXU =   0.0 deg: volume = 5849.473573868  area = 2358.396110707  faces = 8 edges = 18
      isValid() = True   check(True) = clean
  AngleXU =  90.0 deg: volume = 5849.473572935  area = 2358.396111104  faces = 8 edges = 17
      isValid() = True   check(True) = clean
  A0.cut(A90).Volume  = 0.000000000000
  A90.cut(A0).Volume  = 0.000000000000
```

Каждое режет другое в ноль — это одна и та же область пространства. Скругляемое ребро
тоже совпадает побайтово:

```
  AngleXU =   0.0 deg: Edge10 length = 6.370744000  from (25.0000, 19.3477, 10.0000) to (25.0000, 25.7184, 10.0000)
  AngleXU =  90.0 deg: Edge10 length = 6.370744000  from (25.0000, 19.3477, 10.0000) to (25.0000, 25.7184, 10.0000)
```

Шов — нет:

```
  AngleXU =   0.0 deg: seam Edge17 on Face7 (Cylinder) from (25.0000, 12.7000, 0.5988) to (24.7509, 12.7000, 0.3496)
  AngleXU =  90.0 deg: seam Edge16 on Face7 (Cylinder) from (25.0000, 19.3477, 10.0000) to (20.0503, 19.3477, 5.0503)
```

### 3.3. Одно и то же скругление на одном и том же ребре

```
  AngleXU =   0.0 deg  dist(seam, edge) = 11.514077943 mm
      makeFillet(1.00) -> isValid() = True  volume 5849.4736 -> 5848.1055
      removed =    +1.3681 mm3   analytic (1 - pi/4)*r^2*L = +1.3672 mm3
      check(True) = clean      t = 0.014 s
  AngleXU =  90.0 deg  dist(seam, edge) = 0.000000000 mm
      makeFillet(1.00) -> isValid() = False volume 5849.4736 -> 6205.9267
      removed =  -356.4531 mm3   analytic (1 - pi/4)*r^2*L = +1.3672 mm3
      check(True) = RAISED Bad orientation of sub-shape x1, No error x2      t = 0.025 s
```

Скругление обязано **снять** 1.3672 мм3. При шве на вершине объём **вырос** на
356.4531 мм3.

Контроль: фаска того же размера на том же ребре не страдает ни в одном из случаев.

```
  AngleXU =   0.0 deg  makeChamfer(1.00) -> isValid() = True  removed = +3.1885 mm3 (analytic 3.1854) check = clean
  AngleXU =  90.0 deg  makeChamfer(1.00) -> isValid() = True  removed = +3.1885 mm3 (analytic 3.1854) check = clean
```

Значит, дефект — в коде скруглений, а не в топологии как таковой.

### 3.4. Развёртка по углу: три режима, а не два

`r = 1.0`, `AngleXU` от 0 до 270 градусов, `dist` — расстояние от шва до скругляемого ребра:

```
  AngleXU   dist(mm)      valid   volume       removed      check(True)
      0.0     11.514078  True       5848.1055      +1.3681 clean
     45.0      6.926929  True       5848.1055      +1.3681 clean
     60.0      4.784231  True       5848.1055      +1.3681 clean
     75.0      2.443732  True       5848.1055      +1.3681 clean
     80.0      1.635623  True       5848.1055      +1.3681 clean
     82.0      1.309993  True       5848.1055      +1.3681 clean
     84.0      0.983368  False      6205.9267    -356.4531 RAISED Bad orientation of sub-shape x1, No error x2
     85.0      0.819759  False      6205.9267    -356.4531 RAISED ...
     86.0      0.655995  False      6205.9267    -356.4531 RAISED ...
     87.0      0.492105  False      6205.9267    -356.4531 RAISED ...
     88.0      0.328122  False      6205.9267    -356.4531 RAISED ...
     89.0      0.164077  False      6205.9267    -356.4531 RAISED ...
     90.0      0.000000  False      6205.9267    -356.4531 RAISED ...
     91.0      0.164077  False      6205.9267    -356.4531 RAISED ...
     92.0      0.328122  False      6205.9267    -356.4531 RAISED ...
     93.0      0.492105  True       5846.7258      +2.7478 RAISED Error in Edge: BOPAlgo SelfIntersect x3, Error in Edge: BOPAlgo TooSmallEdge x14, Error in Face: BOPAlgo SelfIntersect x1, Error in Vertex: BOPAlgo SelfIntersect x76
     94.0      0.655995  True       5846.7237      +2.7498 RAISED ...
     95.0      0.819759  True       5846.7228      +2.7508 RAISED ...
     96.0      0.983368  True       5846.7188      +2.7547 RAISED ...
    100.0      1.635623  True       5848.1055      +1.3681 clean
    135.0      6.926929  True       5848.1055      +1.3681 clean
    180.0     11.514078  True       5848.1055      +1.3681 clean
    270.0     13.295312  True       5848.1055      +1.3681 clean
```

Три режима:

1. **`dist >= 1.31` мм** — верно: снято 1.3681 против аналитических 1.3672, BOP чист.
2. **углы 84…92** — `isValid() = False`, объём вырос на 356.4531 мм3. Отказ громкий.
3. **углы 93…96** — `isValid() = True`, но `check(True)` ругается, и снято 2.7478 мм3,
   то есть **вдвое больше** положенного. Отказ **тихий**. Это самый опасный режим:
   такое тело выглядит исправным.

Асимметрия по углу (слева от 90 — громкий отказ, справа — тихий) воспроизводится
устойчиво; почему именно так — не измерено, это вопрос к исходникам скруглений.

### 3.5. Полоса опасности масштабируется с радиусом

Развёртка `AngleXU` от 60 до 120 градусов с шагом 1 градус, для четырёх радиусов.
`max broken` — наибольшее расстояние шов–ребро, при котором результат уже испорчен;
`min intact` — наименьшее расстояние, при котором он ещё верен.

```
  r       band lo    band hi    max broken   min intact   verdict
  0.25    89.0       91.0       0.164077     0.328122     BROKEN,SILENT
  0.50    87.0       93.0       0.492105     0.655995     BROKEN,SILENT
  1.00    84.0       96.0       0.983368     1.146790     BROKEN,SILENT
  2.00    78.0       102.0      1.960011     2.121663     BROKEN,SILENT
```

Отношение `max broken / r`: 0.656, 0.984, 0.983, 0.980. **Порог — примерно один радиус
скругления.** Правило: скругление радиуса `r` ломается, пока конец шва ближе примерно
`r` миллиметров к скругляемому ребру.

Контроль — тот же радиус при заведомо далёком шве:

```
    r = 0.25  AngleXU =   0.0  dist = 11.514078  OK      removed = +0.0855 (analytic +0.0854)
    r = 0.50  AngleXU =   0.0  dist = 11.514078  OK      removed = +0.3419 (analytic +0.3418)
    r = 1.00  AngleXU =   0.0  dist = 11.514078  OK      removed = +1.3681 (analytic +1.3672)
    r = 2.00  AngleXU =   0.0  dist = 11.514078  OK      removed = +5.4832 (analytic +5.4687)
    r = 3.00  AngleXU =   0.0  dist = 11.514078  OK      removed = +12.3782 (analytic +12.3046)
```

Большие радиусы сами по себе работают: дело не в радиусе, а в близости шва.

Карта по углам (`.` верно, `s` тихо испорчено, `X` невалидно):

```
    r = 0.25   82:. 83:. 84:. 85:. 86:. 87:. 88:. 89:X 90:s 91:s 92:. 93:. 94:. 95:. 96:. 97:. 98:. 99:. 100:.
    r = 0.50   82:. 83:. 84:. 85:. 86:. 87:s 88:s 89:s 90:X 91:s 92:X 93:X 94:. 95:. 96:. 97:. 98:. 99:. 100:.
    r = 1.00   82:. 83:. 84:X 85:X 86:X 87:X 88:X 89:X 90:X 91:X 92:X 93:s 94:s 95:s 96:s 97:. 98:. 99:. 100:.
    r = 2.00   82:X 83:X 84:X 85:X 86:X 87:X 88:X 89:X 90:X 91:X 92:X 93:X 94:X 95:X 96:X 97:s 98:s 99:s 100:s
```

---

## 4. `isValid()` врёт; правду говорит `check(True)`

`Part.Shape.isValid()` — это дешёвая структурная проверка OCCT (`BRepCheck_Analyzer`).
`Part.Shape.check(True)` — проверка булевых операций (`BOPAlgo_ArgumentAnalyzer`),
то есть ровно то, от чего зависит всё дальнейшее: булевы, сечения, экспорт.

### 4.1. Результат скругления, который «валиден» и при этом сломан

```
  AngleXU   valid   volume        removed       analytic    check(True)
      0.0   True        5848.1055       +1.3681     +1.3672 clean
     90.0   False       6205.9267     -356.4531     +1.3672 RAISED Bad orientation of sub-shape x1, No error x2
     93.0   True        5846.7258       +2.7478     +1.3672 RAISED Error in Edge: BOPAlgo SelfIntersect x3, Error in Edge: BOPAlgo TooSmallEdge x14, Error in Face: BOPAlgo SelfIntersect x1, Error in Vertex: BOPAlgo SelfIntersect x76
     95.0   True        5846.7228       +2.7508     +1.3672 RAISED ...
```

Подробности того же тела при `AngleXU = 93`:

```
    isValid()                     = True
    Shells[0].isClosed()          = True
    faces = 9  edges = 21  vertexes = 14  solids = 1
    faces failing their own isValid(): none
    check(True) -> BOP check found the following errors:
    check(True) -> Error in Vertex: BOPAlgo SelfIntersect
    ... (95 lines in total)
```

Оболочка замкнута, каждая грань проходит собственный `isValid()`, а 95 строк ошибок BOP
говорят, что тело самопересекается.

### 4.2. Тело, испорченное ещё до всякой операции

Если сначала скруглить донное ребро кармана (радиус 1.0), появляется тороидальная
грань. Тор периодичен по обоим параметрам; там, где шов кармана пересекает тор, тор
выдаётся **разрезанным**, и тело грязно по BOP сразу:

```
  AngleXU   faces     volume        valid   seams     toroids   check(True)
      0.0   14            5857.2721 True    0         [10, 14]  clean
     45.0   14            5857.2721 True    0         [8, 9, 11] RAISED Error in Edge: BOPAlgo_InvalidCurveOnSurface x2, Error in Face: BOPAlgo_InvalidCurveOnSurface x2
     88.0   14            5857.2721 True    0         [8, 9, 11] RAISED ...
     90.0   14            5857.2721 True    0         [8, 9, 13] RAISED ...
     92.0   14            5857.2721 True    0         [8, 9, 13] RAISED ...
    135.0   14            5857.2721 True    0         [8, 9, 13] RAISED ...
    180.0   14            5857.2721 True    0         [9, 10]   clean
    270.0   14            5857.2721 True    0         [8, 9, 13] RAISED ...
```

Во всех строках `isValid() = True` и одинаковый объём. Различие видно по площадям
тороидальных граней:

```
  AngleXU =   0.0  isValid() = True  check(True) = clean
      Face10  toroid area = 22.224494
      Face14  toroid area = 22.224494
  AngleXU =  90.0  isValid() = True  check(True) = RAISED Error in Edge: BOPAlgo_InvalidCurveOnSurface x2, Error in Face: BOPAlgo_InvalidCurveOnSurface x2
      Face8   toroid area = 11.112247
      Face9   toroid area = 22.224494
      Face13  toroid area = 11.112247
```

`11.112247 * 2 = 22.224494` — тор разрезан ровно пополам швом.

**Вывод для всего проекта: проверять только `check(True)`. `isValid()` в этой области
непригоден.**

---

## 5. Реальная деталь владельца и полоса зависания

Скрипт `07_user_part_fillet.py` копирует `.FCStd` во временный каталог и открывает
копию; оригинал не открывается никогда.

### 5.1. Исходная деталь чиста по обеим проверкам

```
  Body           PartDesign::Body           faces = 11  edges = 28  valid = True  vol =    5456.5806  check = clean
  Pad            PartDesign::Pad            faces = 6   edges = 12  valid = True  vol =    6429.5861  check = clean
  Pocket         PartDesign::Pocket         faces = 8   edges = 20  valid = True  vol =    5451.4879  check = clean
  Fillet         PartDesign::Fillet         faces = 10  edges = 25  valid = True  vol =    5457.8804  check = clean
  Fillet001      PartDesign::Fillet         faces = 11  edges = 28  valid = True  vol =    5456.5806  check = clean

  Body.Tip = Fillet001 (PartDesign::Fillet)
  tip shape: faces = 11 edges = 28 volume = 5456.5806 isValid = True check(True) = clean
```

Каждая фича проходит `check(True)`. Сообщение PartDesign «Base feature's TopoShape is
invalid» — ложное: измерения выше его опровергают.

### 5.2. Шов сидит ровно на конце скругляемого ребра

```
  seam Edge3   on Face1   (Cylinder  ) length =   9.0000  (24.9999, 19.3478, 10.0000) -> (18.6360, 19.3478, 3.6360)
  Edge9: Part::GeomLine     length = 6.370619  (24.9999, 19.3478, 10.0000) -> (24.9999, 25.7184, 10.0000)
  distance(Edge9, nearest seam) = 0.000000000 mm
```

Это ровно случай `AngleXU = 90` из раздела 3.

### 5.3. Развёртка по радиусу на `Edge9`

Каждый радиус — отдельный процесс со своим внешним дедлайном
(`SEAMLESS_RADIUS=<r> timeout -k 5 540 FreeCADCmd.exe 07_user_part_fillet.py`).
База — 5456.5806 мм3.

| r, мм | recompute | isValid | объём результата | дельта, мм3 | `check(True)` |
|---|---|---|---|---|---|
| 0.10 | 0.033 s | False | -142.2981 | -5598.8787 | Self-intersecting wire x2, Unorientable shape x2 |
| 0.25 | 0.028 s | **True** | 5456.5584 | -0.0222 | BOPAlgo SelfIntersect x3 + TooSmallEdge x14 + Face x1 + Vertex x244 |
| 0.45 | 0.035 s | False | 4599.7393 | -856.8413 | Self-intersecting wire x2, Unorientable shape x2 |
| 0.50 | НЕ ВЕРНУЛСЯ | — | — | — | — |
| 0.55 | НЕ ВЕРНУЛСЯ | — | — | — | — |
| 0.60 | 0.020 s | False | 6099.5286 | **+642.9480** | Self-intersecting wire x2, Unorientable shape x2 |
| 0.75 | 0.021 s | False | 6075.7317 | **+619.1511** | Self-intersecting wire x2, Unorientable shape x2 |
| 1.00 | 0.039 s | False | 6053.9129 | **+597.3323** | Self-intersecting wire x2, Unorientable shape x2 |

Строки «НЕ ВЕРНУЛСЯ» — см. раздел 5.4.

`r = 0.25` — тот самый тихий отказ: `isValid() = True`, тело выглядит целым, снято
0.0222 мм3 вместо аналитических `(1 - pi/4) * 0.25^2 * 6.370619 = 0.0854` мм3, то есть
почти вчетверо меньше, и BOP насчитывает 262 ошибки.

Начиная с `r = 0.60` объём стабильно **растёт** на 600–650 мм3 при том, что скругление
обязано снять доли кубического миллиметра. Аналитическое значение для `r = 1.0` на ребре
длиной 6.370619 мм — 1.3672 мм3.

### 5.4. Полоса зависания

Радиусы 0.5 и 0.55 не завершаются. Каждый запускался отдельным процессом с внешним
дедлайном 540 секунд:

```
SEAMLESS_RADIUS=0.5  timeout -k 5 540 "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 07_user_part_fillet.py
SEAMLESS_RADIUS=0.55 timeout -k 5 540 "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 07_user_part_fillet.py
```

Результат:

```
radius=0.5  exit=124 wall=542s
radius=0.55 exit=124 wall=541s
```

Код 124 — процесс убит по дедлайну. Последняя напечатанная строка в обоих прогонах:

```
==============================================================================
D. PartDesign::Fillet r = 0.5000 on Edge9
==============================================================================
  about to recompute -- if nothing follows this line, the kernel never returned
```

`doc.recompute()` не вернулся за 9 минут. Для сравнения, соседние радиусы возвращаются
мгновенно: 0.45 — за 0.035 с, 0.60 — за 0.020 с. Это не «медленно», это другое
поведение: между 0.45 и 0.60 лежит полоса, в которой скругление не завершается вовсе.

Границы полосы точно не измерены: каждая точка внутри неё стоит 9 минут машинного
времени, а снаружи — доли секунды, поэтому бисекция по радиусу дорога. Измерено, что
0.45 возвращается, 0.5 и 0.55 — нет.

Практический вывод для любого инструмента поверх OCCT: **вызов скругления рядом со швом
обязан иметь внешний дедлайн.** Внутри процесса его поставить нечем — ядро не
прерывается.

---

## 6. Шов можно не создавать — и это поправка к стартовому факту

Стартовая запись проекта гласила: «разбиение окружности профиля на две дуги шов не
убирает: ядро склеивает грани одной поверхности обратно». Измерение показывает, что это
верно **только при включённом Refine**.

### 6.1. Цилиндр из двух половинных граней швов не имеет

```
  reference Part.makeCylinder(5, 10) : faces = 3 edges = 3 seams = 1 vol = 785.3982 valid = True
  built from two half faces          : faces = 4 edges = 6 seams = 0 vol = 785.3982 valid = True
  shell closed = True   check(True) = clean
  |volume difference| = 0.000000000000   -> the same solid, no seam
```

### 6.2. Что сохраняет бесшовную форму, а что возвращает шов

```
  cut:       box.cut(split)    faces = 10  edges = 18  seams = 0
  common:    box.common(split) faces = 4   edges = 6   seams = 0
  fuse:      split.fuse(small) faces = 9   edges = 18  seams = 0
  copy:      split.copy()      faces = 4   edges = 6   seams = 0
  transform: split.rotated(...) faces = 4   edges = 6   seams = 0
  removeSplitter()             faces = 3   edges = 5   seams = 1 <- the seam is back
  UnifySameDomain              faces = 3   edges = 3   seams = 1 <- the seam is back
  STEP export + read back      faces = 4   edges = 6   seams = 0  vol = 785.3982
```

Булевы, копии, преобразования и круговой обмен через STEP бесшовную форму сохраняют.
Возвращают шов ровно `removeSplitter` и `UnifySameDomain` — то есть то, что запускает
флаг `Refine` в PartDesign. Ослабить это настройками нельзя:

```
  before: faces = 4 seams = 0
  UnifySameDomain(linear = 1e-07, angular = 1e-07) -> faces = 3 seams = 1
  UnifySameDomain(linear = 0.001, angular = 0.001) -> faces = 3 seams = 1
```

### 6.3. На реальном стенде: разбитый профиль плюс `Refine = False`

Тот же стенд, `AngleXU = 90` — угол, на котором раздел 3 намерил -356.4531 мм3.
Профиль кармана разбивается на `arcs` дуг вместо одной окружности:

```
  arcs    Refine   faces   seams   valid   pocket vol    removed       check(True)
  1       True     8       1       True        5849.4736     -356.4531 False RAISED Bad orientation of sub-shape x1, No error x2
  2       True     8       1       True        5849.4736       +1.3681 True clean
  3       True     8       1       True        5849.4736       +1.3681 True clean
  4       True     8       1       True        5849.4736       +1.3681 True clean
  1       False    8       1       True        5849.4736     -356.4531 False RAISED Bad orientation of sub-shape x1, No error x2
  2       False    9       0       True        5849.4736       +1.3681 True clean
  3       False    10      0       True        5849.4736       +1.3681 True clean
  4       False    11      0       True        5849.4736       +1.3681 True clean
```

Аналитическое значение — `+1.3672` мм3.

- одна дуга (полная окружность) — один шов, скругление уничтожено;
- две дуги при `Refine = True` — PartDesign склеивает половинки обратно, шов есть
  снова, но его `u = 0` попадает в другое место, и **это конкретное** скругление
  выживает; общей гарантии это не даёт;
- две дуги при `Refine = False` — швов нет вовсе, и скругление точное.

Цена:

```
  Refine = True  : faces = 8, edges = 18, vertexes = 12, area = 2358.396112
  Refine = False : faces = 9, edges = 19, vertexes = 12, area = 2358.396112
```

Одна лишняя грань и одно лишнее ребро на каждое разбиение; площадь и объём не меняются.

**Это обходной путь, а не лечение.** Он ничего не говорит о том, почему скругление
ломается; он лишь показывает, что причина — именно шов, а не близость геометрии.

---

## 7. Что достижимо из Python, а что нет

### 7.1. Ни один модуль OCCT не импортируется напрямую

```
  import ShapeUpgrade     -> ModuleNotFoundError: No module named 'ShapeUpgrade'
  import ShapeFix         -> ModuleNotFoundError: No module named 'ShapeFix'
  import ShapeAnalysis    -> ModuleNotFoundError: No module named 'ShapeAnalysis'
  import ShapeBuild       -> ModuleNotFoundError: No module named 'ShapeBuild'
  import ShapeCustom      -> ModuleNotFoundError: No module named 'ShapeCustom'
  import BRepBuilderAPI   -> ModuleNotFoundError: No module named 'BRepBuilderAPI'
  import BRepTools        -> ModuleNotFoundError: No module named 'BRepTools'
  import BRepAlgoAPI      -> ModuleNotFoundError: No module named 'BRepAlgoAPI'
  import BRepFilletAPI    -> ModuleNotFoundError: No module named 'BRepFilletAPI'
  import TopoDS           -> ModuleNotFoundError: No module named 'TopoDS'
```

### 7.2. Что переэкспортирует `Part`

```
  Part.BRepFeat           (module) -> ['MakePrism']
  Part.BRepOffsetAPI      (module) -> ['MakeFilling', 'MakePipeShell']
  Part.ChFi2d             (module) -> ['AnaFilletAlgo', 'ChamferAPI', 'FilletAPI', 'FilletAlgo']
  Part.Geom2d             (module) -> [... 17 классов кривых ...]
  Part.GeomPlate          (module) -> ['BuildPlateSurface', 'CurveConstraint', 'PointConstraint']
  Part.HLRBRep            (module) -> ['Algo', 'HLRToShape', 'PolyAlgo', 'PolyHLRToShape']
  Part.ShapeFix           (module) -> ['Edge', 'EdgeConnect', 'Face', 'FaceConnect', 'FixSmallFace',
                                       'FixSmallSolid', 'FreeBounds', 'Root', 'Shape', 'ShapeTolerance',
                                       'Shell', 'Solid', 'SplitCommonVertex', 'SplitTool', 'Wire',
                                       'WireVertex', 'Wireframe', ...]
  Part.ShapeUpgrade       (module) -> ['UnifySameDomain']
```

**Поправка к стартовому факту.** В стартовой записи проекта было сказано, что `ShapeFix`
недоступен. Это верно только для верхнеуровневого `import ShapeFix`. На самом деле
`Part.ShapeFix` существует и содержит 17 классов.

### 7.3. Класса, который убирает шов, нет

```
  Part.ShapeUpgrade contents: ['UnifySameDomain']
  Part.ShapeUpgrade.ShapeDivideClosed      present = False
  Part.ShapeUpgrade.ShapeDivide            present = False
  Part.ShapeUpgrade.ShapeDivideContinuity  present = False
  Part.ShapeUpgrade.ShapeDivideArea        present = False
  Part.ShapeUpgrade.ShapeConvertToBezier   present = False
  Part.ShapeUpgrade.RemoveLocations        present = False
  Part.ShapeUpgrade.UnifySameDomain        present = True
```

`ShapeUpgrade_ShapeDivideClosed` — это и есть класс OCCT, который режет замкнутую грань
надвое и тем самым убирает шов. Он не привязан. Привязан ровно один класс —
`UnifySameDomain`, делающий противоположное (раздел 6.2).

Из `Part.ShapeFix` доступно всё, что касается шва, кроме удаления:

```
  Part.ShapeFix.Wire   methods mentioning 'seam': ['FixSeamMode', 'fixSeam']
  Part.ShapeFix.Face   methods mentioning 'seam': ['FixMissingSeamMode', 'fixMissingSeam']
```

`fixSeam` и `fixMissingSeam` **добавляют** или чинят шов у грани, которой его не хватает.
Метода `removeSeam` не существует. Попытка снять вторую pcurve вручную ничего не даёт:

```
  seam edge before: adjacent faces = 1
  Part.ShapeFix.Edge().fixRemovePCurve(seam, face) -> False
  solid after the call: faces = 3 seams = 1 valid = True check = clean
```

### 7.4. Итог по доступности

Из Python можно: **увидеть** шов (раздел 1), **переставить** его через параметризацию
профиля (раздел 3), **не создавать** его вовсе (раздел 6) и **починить** отсутствующий.
Нельзя: попросить OCCT разрезать замкнутую грань. Любое настоящее исправление требует
C++ и, скорее всего, пересборки OCCT.

---

## 8–9. Резьбы — вынесены в отдельные дефекты

Замеры резьб были сделаны по дороге, пока разбирался шов, и со швом не связаны: у тела
`Part.makeThread` швов нет вовсе (`seams = 0`), а у `AdditiveHelix` шов подложки есть и при
чистом, и при сломанном результате. Теперь это самостоятельные дефекты со своими замерами:

- `issues/002-freecad-makethread-turns` — `Part.makeThread` выдаёт 0.2690 витка из 32;
- `issues/003-partdesign-additivehelix` — открытый инструмент при `2h == pitch`, потеря
  сердцевины выше отношения 1.20;
- `issues/004-makehelix-length` — `Shape.Length` у `makeHelix` врёт начиная примерно с 50 витков;
- `issues/005-thread-fuse` — приваривание 32-витковой резьбы: 41 с и тело с отрицательным объёмом.

---

## 10. Что измерено и что осталось неизвестным

Измерено:

- шов — изо-линия `u = 0` системы координат поверхности, предсказывается формулой
  `Center + R * Rotation * (1,0,0)` с расстоянием 0.000000000000;
- шов — единственное ребро с одной смежной гранью; его контур обходит дважды, в двух
  ориентациях; он несёт две pcurve на одной грани;
- скругление радиуса `r` ломается, пока шов ближе примерно `r` мм к скругляемому ребру;
  порог измерен для `r` = 0.25, 0.5, 1.0, 2.0; отношение «наибольшее сломанное
  расстояние / r» равно 0.656, 0.984, 0.983, 0.980 — то есть для `r >= 0.5` порог
  держится на `0.98 * r`, а при `r = 0.25` он относительно уже;
- отказ бывает трёх видов: верно, громко невалидно (объём растёт на 356.4531 мм3),
  и тихо испорчено (`isValid() = True`, снято вдвое больше нужного);
- `isValid()` в этой области непригоден; пригоден только `check(True)`;
- фаска того же размера на том же ребре не страдает;
- из Python шов нельзя удалить: `ShapeUpgrade_ShapeDivideClosed` не привязан;
- шов можно **не создавать**: разбитый профиль плюс `Refine = False`;
- `Part.makeThread` — одновитковый примитив, 0.2690 витка из 32 запрошенных;
- `PartDesign::AdditiveHelix` ломается при `2h == pitch` и молча съедает сердцевину
  выше `2h/pitch = 1.20`.

Не измерено (и потому нигде не утверждается):

- почему полоса отказа асимметрична по углу (слева громко, справа тихо);
- где именно в подсистеме скруглений OCCT происходит отказ — для этого нужны исходники
  и отладочная сборка;
- является ли дефект следствием модели данных (шов как обязательная сущность) или
  ошибкой конкретной реализации; это и есть главный вопрос разведки;
- почему `rod.fuse(thread)` на 32 витка занимает 41 с и даёт отрицательный объём;
- поведение на сфере и торе: швы посчитаны (3 и 2), но скругления рядом с ними не
  измерялись.

---

## 11. Поправки к стартовым фактам проекта

Измерения этого файла расходятся со стартовой запиской в двух местах. Записано
здесь, чтобы расхождение не потерялось.

1. **«`ShapeFix` из Python недоступен»** — неверно. Недоступен верхнеуровневый
   `import ShapeFix`, но `Part.ShapeFix` существует и содержит 17 классов, включая
   `Wire.fixSeam` и `Face.fixMissingSeam` (раздел 7.2). Содержательный вывод не
   меняется: удалить шов всё равно нечем, потому что нет `ShapeDivideClosed`.

2. **«Разбиение окружности профиля на две дуги шов не убирает»** — верно только при
   `Refine = True`. При `Refine = False` шов не появляется вовсе, и скругление,
   которое раньше давало -356.4531 мм3, даёт точные +1.3681 (раздел 6.3).
