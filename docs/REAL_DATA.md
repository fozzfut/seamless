# Настоящие данные: набор OCCT прогнан на реальных телах, а не на кубиках

Дата: 12 сентября 2026. Ядро: OCCT 7.8.1, тег `V7_8_1`.
Патч: `patches/0002-chfi3d-recale-on-closed-face.patch` — одно условие
`if (onsame || Bs.IsUClosed() || Bs.IsVClosed())` в `ChFi3d_Builder_C1.cxx:807`.

---

## 0. Ответ

**Данные нашлись.** Публичный набор данных OCCT лежит на GitHub —
`a-betenev/opencascade-dataset`, 3718 файлов, 910 МБ. Это репозиторий
сопровождающего OCCT Андрея Бетенева, и в его `Readme.md` прямо сказано, что
файлы взяты из официальных наборов, публикуемых с релизами OCCT.

После подключения этого набора **исполняется 2122 случая вместо 849**
(прибавка 1273 случая). Результат сравнения стокового и патченого ядра:

| | значение |
|---|---|
| случаев исполнено на обоих ядрах | **2122** |
| **изменений статуса случая (OK/BAD/FAILED/SKIPPED)** | **0** |
| журналов случаев разошлось (из 3065 сравнённых) | 21 |
| из них доказано воспроизведённым шумом набора | **21 из 21** |
| ухудшений | **0** |
| улучшений в наборе | 0 |

Вывод предыдущего прогона («475 из 475 журналов `blend` байт в байт») **устоял
на впятеро большем объёме реальной геометрии**. Самая большая дыра раздела
«что не измерено» закрыта — и закрыта в пользу патча.

Остаточная дыра: 943 случая по-прежнему пропускаются, потому что 445 файлов
данных отсутствуют и в публичном наборе. Что именно с ними — раздел 5.

---

## 1. Где искали и что ответил каждый источник

Предыдущий агент проверил один адрес и остановился. Вот полный список
проверенного, с ответами.

| Источник | Команда / URL | Ответ |
|---|---|---|
| исторический git OCCT | `Resolve-DnsName git.dev.opencascade.org` | `DNS name does not exist` — подтверждено, хоста больше нет |
| багтрекер OCCT | `Resolve-DnsName tracker.dev.opencascade.org` | `The remote name could not be resolved` — тоже нет |
| портал загрузок | `https://dev.opencascade.org/release` | 301 → `occt3d.com/open-cascade-technology/index.html` |
| портал загрузок (новый) | `https://occt3d.com/open-cascade-technology/index.html` | **архивов датасета нет**, все ссылки ведут на GitHub Releases |
| историч. URL архива | `.../private/occt/OCC_7.9.0_release/opencascade-dataset-7.9.0.tar.xz` | HTTP 200, но `Content-Length=43629` — это тот же редирект на главную, не архив |
| GitHub Releases OCCT | `api.github.com/repos/Open-Cascade-SAS/OCCT/releases` | 27 релизов, ассеты только бинарные (`opencascade-*.zip`, `3rdparty`, доки). **Датасета нет ни в одном** |
| организация Open-Cascade-SAS | `api.github.com/orgs/Open-Cascade-SAS/repos` | 24 репозитория, репозитория с тестовыми данными **нет** |
| поиск репозиториев | `search/repositories?q=occt-test-data` | 1 результат, нерелевантный |
| поиск репозиториев | `search/repositories?q=opencascade+test+data` | **1 результат: `a-betenev/opencascade-dataset`, 272 МБ** ← нашлось здесь |
| форки найденного | `repos/a-betenev/opencascade-dataset/forks` | 1 форк: `gkv311/opencascade-dataset`, 294 МБ (Кирилл Гаврилов, тоже разработчик OCCT) |
| поиск по коду GitHub | `search/code?q=CFI_pro5203` | HTTP 401 — поиск по коду требует авторизации, недоступен |
| Ubuntu/Debian | `archive.ubuntu.com/ubuntu/pool/universe/o/opencascade/` | только `*+dfsg*.deb`; суффикс `dfsg` означает, что несвободные файлы **вырезаны** из исходников — данных там нет по построению |
| Gentoo ebuild | `opencascade-7.8.1.ebuild` | HTTP 404 на зеркале |
| SourceForge | `sourceforge.net/projects/opencascade/files/` | три папки: `Open CASCADE fixes`, `OldFiles`, `Miscellaneous` — тестового набора нет |
| Wayback Machine | `web.archive.org/cdx/search/cdx?...dataset...` | HTTP 429 Too Many Requests при четырёх попытках с паузами до 45 с — **проверить не удалось** |
| архив тикетов | `occt3d.com/dev/tickets/` | страница есть, но `/dev/tickets/0025926/` → HTTP 404; вложений не отдаёт |
| веб-поиск по именам файлов | `"CFI_pro5203.rle" OR "CCH_001_ahev.rle"` | ноль совпадений во всём вебе |

Сравнение двух найденных репозиториев (форк на 14 файлов больше):

```
# диф деревьев через GitHub API git/trees?recursive=1
a-betenev=3718 gkv311=3732
only in gkv311 (15): шрифты (.ttf), кубмапы (.png), два glTF, один .stp, один .brep
only in a-betenev (1): others/bug24386_DejaVuSerif.ttf
blend: 0 of 27 missing covered by gkv311 extras
chamfer: 0 of 4 ; feat: 0 of 15 ; offset: 0 of 548
total newly covered: 0
```

Форк добавляет только ресурсы визуализации и **ни одного** нужного нам файла.
Поэтому взят `a-betenev/opencascade-dataset` — это максимум публично доступного.

---

## 2. Что именно взято

```
$ git clone --depth 1 --single-branch https://github.com/a-betenev/opencascade-dataset.git C:/dev/occt-dataset
$ cd /c/dev/occt-dataset && git rev-parse HEAD
d78a7a9e6de57699261fa03641ec1b5bafac39a1
$ find . -path ./.git -prune -o -type f -print | wc -l
3718
$ find . -path ./.git -prune -o -type f -printf '%s\n' | awk '{s+=$1} END {print s}'
909871002
$ git status --short          # пусто: рабочее дерево чистое
```

Состав: `brep` 2879, `step` 404, `geom` 179, `others` 140, `iges` 87,
`ocaf` 10, `xbf` 10, `msv` 5, `script` 2.

Из `Readme.md` репозитория:

> The data files come from two primary sources:
> * Official datasets published with OCCT releases
> * Additional data extracted from attachments to publicly accessible issues in
>   OCCT bug tracker

Подключается одной переменной — `locate_data_file` в
`src/DrawResources/TestCommands.tcl:1182` разбирает `CSF_TestDataPath` через
`_split_path`, то есть принимает список через `;` и обходит подкаталоги
рекурсивно:

```
export CSF_TestDataPath="C:/dev/occt-cond/data;C:/dev/occt-dataset"
```

Проверка, что путь действительно находит файлы:

```
$ DRAWEXE -b -f smoke.tcl
FOUND: C:/dev/occt-dataset/brep/CFI_indusfjm.rle
FOUND2: C:/dev/occt-dataset/brep/CCH_001_ahdb.rle
```

---

## 3. Прогон: что исполнилось и что разошлось

Запуск — `tests-fillet/run_group_data.sh <группа> <каталог> <ядро>`.
Единственная переменная между прогонами — `TKFillet.dll`:

```
bin-stock/TKFillet.dll  8acb66f3cd79bdbb94f7b3db1d45df26
bin-cond/TKFillet.dll   4e89e519f8a7ec7f7ed7f2b198d60275
```

Остальные 22 DLL в обоих каталогах — одни и те же файлы из одной сборки
`C:/dev/seamless/build/occt-cond`. Пакет `Thread` в этом DRAWEXE отсутствует
(`package require Thread` → `can't find package Thread`), поэтому `testgrid`
в любом случае идёт последовательно — как и в прошлых прогонах; восемь прогонов
шли параллельно как отдельные процессы ОС.

### 3.1. Сколько случаев ожило

| группа | всего | исполнялось БЕЗ данных | исполняется СЕЙЧАС | **ожило** | пропущено сейчас |
|---|---|---|---|---|---|
| `blend` | 475 | 183 | **446** | +263 | 29 |
| `chamfer` | 279 | **0** | **261** | +261 | 18 |
| `feat` | 304 | 130 | **285** | +155 | 19 |
| `offset` | 2007 | 536 | **1130** | +594 | 877 |
| **итого** | **3065** | **849** | **2122** | **+1273** | **943** |

Цифры «БЕЗ данных» — из `docs/PATCH_V2.md`, раздел 4.

### 3.2. Статусы: сток против патча

`tests-fillet/case_status.py` берёт последнюю строку `CASE <группа> <сетка>
<случай>: <статус>` из журнала каждого случая и сличает два прогона.

| группа | сток | патч | различий статуса |
|---|---|---|---|
| `blend` | OK 433, BAD 13, SKIPPED 29 | то же | **0** |
| `chamfer` | OK 232, BAD 21, IMPROVEMENT 7, FAILED 1, SKIPPED 18 | то же | **0** |
| `feat` | OK 283, BAD 2, SKIPPED 19 | то же | **0** |
| `offset` | OK 702, BAD 112, FAILED 316, SKIPPED 877 | то же | **0** |

**Ни одного случая, у которого статус изменился.** Ни в худшую сторону, ни в
лучшую.

Две оговорки, чтобы цифры не читались лучше, чем они есть:

* `chamfer dist_angle_sequence A5` — `FAILED (bad shape)` **на обоих** ядрах.
  Это дефект, который набор ловит и на стоке; патч его не вносит и не чинит.
* все 316 `FAILED` в `offset` — это `pload VISUALIZATION` → `Could not open:
  TKViewerTest.dll`. В этой сборке нет модуля Visualization, поэтому сетки
  `simple`, `with_intersect_20`, `with_intersect_80` падают, не дойдя до ядра.
  Они одинаковы на обоих ядрах, но **ядро в них не проверяется**. Честный счёт
  реально проверенных случаев `offset` — 814 (702 OK + 112 BAD), а не 1130.

Тогда честный итог по реально проверенным случаям: **1806** (446 + 261 + 285 +
814) против 849 раньше.

### 3.3. Журналы: сток против патча, байт в байт

`tests-fillet/compare_logs.py` вычищает изменчивые строки (время, память,
адреса исключений) и сличает остальное дословно.

| группа | сравнено | байт в байт | разошлось |
|---|---|---|---|
| `blend` | 475 | **475** | **0** |
| `chamfer` | 279 | **279** | **0** |
| `feat` | 304 | 302 | 2 |
| `offset` | 2007 | 1988 | 19 |

`blend` и `chamfer` — полное совпадение. Все 446 случаев `blend`, включая 263
только что оживших на реальных деталях, дают идентичный журнал. Все 261
исполнившихся `chamfer` — тоже; напомню, что раньше эта группа не исполнялась
вообще (0 из 279).

---

## 4. 21 разошедшийся журнал: все воспроизведены на одном стоке

Расхождение журналов само по себе ничего не доказывает, пока не проверено, что
то же ядро дважды подряд даёт одно и то же. Проверено.

### 4.1. `feat` — два случая

`feat featdprism B4` и `feat featdprism E1`. Каждый запущен по три раза на
каждом ядре (`tests-fillet/run_one_case.sh`):

```
=== B4: Relative error of mass computation ===
stock 1  3.30332e-16     cond 1  3.30332e-16
stock 2  3.79182e-16     cond 2  3.79182e-16
stock 3  3.30332e-16     cond 3  3.79182e-16

=== E1: Matrix of Inertia, строка 1 ===
stock 1  3.6437e+10  1.14441e-05  -1.3999e+08
stock 2  3.6437e+10  1.14441e-05  -1.3999e+08
stock 3  3.6437e+10  7.62939e-06  -1.3999e+08
cond  1  3.6437e+10  7.62939e-06  -1.3999e+08
cond  2  3.6437e+10  7.62939e-06  -1.3999e+08
cond  3  3.6437e+10  1.14441e-05  -1.3999e+08
```

**Сток выдаёт оба значения.** Это не эффект патча, а шум самого набора:
величины — оценка относительной погрешности интегрирования (3e-16, то есть
машинный эпсилон) и внедиагональные члены тензора инерции, равные нулю с
точностью 2e-16 от диагонали (7.62939e-06 = 2⁻¹⁷, 1.14441e-05 = 1.5·2⁻¹⁷ —
квантование float). Масса и центр тяжести во всех шести прогонах совпадают.

### 4.2. `offset` — девятнадцать случаев

Все 19 — в сетках `compshape`, `faces_type_a`, `shape_type_a`. Каждый запущен
дважды подряд на **одном и том же стоковом** ядре:

```
=== stock-прогон 1 против stock-прогона 2 на тех же 19 случаях ===
DIFF compshape/A2   DIFF compshape/A3   DIFF compshape/A5
DIFF compshape/A6   DIFF compshape/A7   SAME faces_type_a/A5
DIFF faces_type_a/A8
DIFF shape_type_a/A1  A2  A3  A6  A7  A8  A9  B1  B2  B4  B5  B6
same=1 differ=18
```

**18 из 19 разошлись на стоке сам с собой.** Оставшийся — `faces_type_a A5` —
проверен отдельно: 18 прогонов на стоке (шесть из них под искусственной
загрузкой шести ядер, чтобы повторить конкуренцию за CPU из группового
прогона) и 6 на патче:

```
distinct sub-shape orderings: 2
  ordering 1: n=8   {'cond': 3, 'stock': 5}
  ordering 2: n=16  {'cond': 3, 'stock': 13}
```

**Сток выдаёт оба порядка.** Разница — перестановка `result_14` и `result_15`
в разложенном компаунде: массы `0.325619` и `0.4` те же самые, центры тяжести и
тензоры инерции те же самые, просто поменялись индексами. Статус всех 24
прогонов — `OK`.

Итого: **21 из 21 разошедшегося журнала воспроизведены на стоковом ядре без
всякого патча.** Ни одно расхождение не относится к патчу.

---

## 5. Что всё-таки не досталось: 445 файлов, 943 случая

Список взят не из догадок, а из самих журналов пропущенных случаев (строка
`file <имя> could not be found`):

| группа | пропущено случаев | различных файлов | из них вложения багтрекера |
|---|---|---|---|
| `blend` | 29 | 27 | 0 |
| `chamfer` | 18 | 4 | 0 |
| `feat` | 19 | 15 | 0 |
| `offset` | 877 | 399 | 378 |

Две разные причины.

**Первая — конфиденциальные модели заказчиков.** 46 файлов для
`blend`/`chamfer`/`feat` — 44 из них `.rle`, два `.brep`: `CFI_pro5203.rle`, `CFI_jap50078.rle`,
`CCH_001_ahev.rle`, `CFE900_cts20gdx.rle`, `CTO904_hkg60206.rle` и подобные.
Имена — коды старых обращений заказчиков (`pro`, `jap`, `ger`, `fra`, `hkg`).
Документация OCCT про набор тестов говорит прямо: *«Many tests are based on
data files that are confidential and thus available only at OPEN CASCADE»*.
Публичный набор содержит 118 файлов `CFI_*` и 37 `CCH_*` — то есть выложено
далеко не всё. Поиск по этим именам во всём вебе даёт ноль. Их **нельзя
получить**, это не вопрос настойчивости.

**Вторая — вложения багтрекера.** 378 из 399 файлов `offset` названы
`bug<номер>_*.brep` / `OCC<номер>-*.brep`. Сам сопровождающий набора решает эту
задачу скриптом `script/getocctdata.tcl`, и в его шапке написано:

> For downloading the files, a user account in OCCT bug tracker is needed.
> set environment variable MANTIS_STRING_COOKIE equal to value of same-named
> cookie in your browser, created when you log in to OCCT bug tracker

Требуется учётная запись в трекере. Хост трекера (`tracker.dev.opencascade.org`)
сейчас не резолвится вовсе, а архив тикетов на `occt3d.com/dev/tickets/`
вложений не отдаёт (`/dev/tickets/0025926/` → HTTP 404). Заводить учётную
запись от имени владельца я не стал.

Из 877 пропущенных `offset` 773 приходятся на одну сетку `shape_type_i_c`.
Ни один из этих файлов не относится к скруглениям: это набор для `BRepOffset`.

Непроверенным остался один источник — Wayback Machine: четыре запроса к её CDX
API ответили HTTP 429 (Too Many Requests) даже с паузами до 45 с. Если старые
архивы `opencascade-dataset-7.9.0.tar.xz` там сохранились, они могли бы
добавить часть первой категории; проверить это в рамках сессии не удалось.

**Подстраховочный корпус не понадобился.** Задание допускало: если данные не
достать — сгенерировать не меньше 500 собственных случаев. Данные достались, и
оживших случаев на настоящих телах вышло 1273 — вдвое больше, чем требовал
запасной план, и это реальная геометрия заказчиков, а не синтетика.

---

## 6. Как повторить

```bash
git clone --depth 1 https://github.com/a-betenev/opencascade-dataset.git C:/dev/occt-dataset
cd /c/dev/seamless
for g in blend chamfer feat offset; do
  for k in stock cond; do
    tests-fillet/run_group_data.sh "$g" "out/$g-$k" "build/bin-$k"
  done
done
for g in blend chamfer feat offset; do
  python tests-fillet/compare_logs.py "out/$g-stock" "out/$g-cond"
  python tests-fillet/case_status.py  "out/$g-stock" "out/$g-cond"
done
# проверка расхождения на шум -- то же ядро дважды:
tests-fillet/run_one_case.sh offset faces_type_a A5 build/bin-stock /tmp/a.log
tests-fillet/run_one_case.sh offset faces_type_a A5 build/bin-stock /tmp/b.log
```

Скрипты, добавленные этой работой:

* `tests-fillet/run_group_data.sh` + `run_group_data.tcl` — прогон группы с
  подключённым набором данных;
* `tests-fillet/run_one_case.sh` + `run_one_case.tcl` — один случай, для
  проверки воспроизводимости;
* `tests-fillet/case_status.py` — таблица статусов и их различий;
* `tests-fillet/diff_list.py` — список разошедшихся журналов;
* `tests-fillet/launch_group.sh` — запуск группы в отдельном рабочем каталоге.

---

## 7. Что это меняет в общем выводе

`docs/PATCH_V2.md`, раздел «что не измерено», пункт про отсутствующие данные —
закрыт. Было: 849 исполненных случаев, из них `chamfer` ноль. Стало: 2122
исполненных (1806 реально доходящих до ядра), `chamfer` 261 из 279.

Ни одного изменения статуса. Ни одного расхождения журнала, которое не
воспроизводилось бы на стоковом ядре. Утверждение «сужённое условие не трогает
ветку `OnSame` и потому ничего не ломает» проверено теперь на реальных телах
заказчиков, а не только на коробках и торах.

Что по-прежнему **не** доказано: патч не проверен на 445 недоступных моделях,
включая 46 конфиденциальных моделей из групп скруглений и фасок. Это остаточный
риск, и снять его без доступа Open Cascade нельзя.
